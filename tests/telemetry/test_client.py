from __future__ import annotations

import inspect
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from core.telemetry.client import (
    ALLOWED_EVENT_NAMES,
    MAX_ATTEMPTS,
    TELEMETRY_ENDPOINT,
    DeliveryResult,
    TelemetryClient,
    _default_sender,
)
from core.config.manager import Config
from core.version import VERSION


class TelemetryClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_client(self, **overrides):
        sent = overrides.pop("sent", [])
        sender = overrides.pop(
            "sender",
            lambda payload: sent.append(payload) or DeliveryResult(
                status=202,
                acknowledged_event_ids=frozenset({payload["event_id"]}),
            ),
        )
        client = TelemetryClient(
            state_path=overrides.pop("state_path", self.root / "state.json"),
            queue_path=overrides.pop("queue_path", self.root / "queue.json"),
            dead_letter_path=overrides.pop("dead_letter_path", self.root / "dead-letter.json"),
            sender=sender,
            enabled_getter=overrides.pop("enabled_getter", lambda: True),
            channel_getter=overrides.pop("channel_getter", lambda: "stable"),
            start_background=False,
            **overrides,
        )
        return client, sent

    def test_disabled_telemetry_sends_and_writes_nothing(self):
        client, sent = self.make_client(enabled_getter=lambda: False)
        self.assertFalse(client.emit("first_stock_recorded"))
        self.assertEqual(client.flush(), 0)
        self.assertEqual(sent, [])
        self.assertFalse(client.state_path.exists())
        self.assertFalse(client.queue_path.exists())

    def test_default_waits_for_disclosure_before_delivery(self):
        config = Config()
        self.assertTrue(config.telemetry.enabled)
        self.assertFalse(config.telemetry.disclosure_acknowledged)

    def test_default_transport_destination_is_exact_audited_https_endpoint(self):
        parsed = urllib.parse.urlsplit(TELEMETRY_ENDPOINT)
        self.assertEqual(TELEMETRY_ENDPOINT, "https://lighthouse.buscore.ca/telemetry/v1/events")
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.hostname, "lighthouse.buscore.ca")
        self.assertEqual(parsed.path, "/telemetry/v1/events")
        self.assertFalse(parsed.username)
        self.assertFalse(parsed.password)
        self.assertFalse(parsed.query)
        self.assertFalse(parsed.fragment)

    def test_default_transport_identifies_bus_core_with_public_version(self):
        event_id = "00000000-0000-0000-0000-000000000001"

        class Response:
            status = 202

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return json.dumps({"acknowledged_event_ids": [event_id]}).encode("utf-8")

        with patch("core.telemetry.client.urllib.request.urlopen", return_value=Response()) as urlopen:
            result = _default_sender({"event_id": event_id})

        request = urlopen.call_args.args[0]
        headers = {name.lower(): value for name, value in request.header_items()}
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["user-agent"], f"BUS-Core/{VERSION}")
        self.assertEqual(result.acknowledged_event_ids, frozenset({event_id}))

    def test_first_run_and_settings_surfaces_are_explicit(self):
        repo = Path(__file__).resolve().parents[2]
        disclosure = (repo / "core" / "ui" / "js" / "telemetry.js").read_text(encoding="utf-8")
        settings = (repo / "core" / "ui" / "js" / "cards" / "settings.js").read_text(encoding="utf-8")
        self.assertIn("Share limited telemetry", disclosure)
        self.assertIn("Don't share", disclosure)
        self.assertIn("It does not send customers", disclosure)
        self.assertIn("setting-telemetry-enabled", settings)
        self.assertIn("Turning this off clears the unsent queue", settings)
        preference_route = (repo / "core" / "api" / "routes" / "telemetry.py").read_text(encoding="utf-8")
        self.assertIn('/telemetry/preference', preference_route)
        self.assertIn("independent of the business write gate", preference_route)
        self.assertNotIn("require_writes", preference_route)

    def test_payload_is_exact_and_cannot_accept_business_content(self):
        client, _ = self.make_client()
        payload = client.build_payload("first_stock_recorded")
        self.assertEqual(set(payload), {
            "schema_version", "event_id", "event_name", "client_ts", "context",
        })
        self.assertEqual(set(payload["context"]), {"app_version", "release_channel", "os_category"})
        serialized = json.dumps(payload).lower()
        for prohibited in (
            "customer_name", "supplier_name", "employee_name", "item_name", "recipe_name",
            "invoice_contents", "email", "file_path", "financial_value", "quantity",
            "database", "username", "machine_fingerprint",
        ):
            self.assertNotIn(prohibited, serialized)
        self.assertEqual(list(inspect.signature(client.emit).parameters), ["event_name", "deduplicate"])
        with self.assertRaises(ValueError):
            client.build_payload("customer_opened")

    def test_version_channel_and_event_allowlist_match_contract(self):
        client, _ = self.make_client(channel_getter=lambda: "partner-3dque")
        payload = client.build_payload("version_first_seen")
        self.assertEqual(payload["context"]["app_version"], VERSION)
        self.assertEqual(payload["context"]["release_channel"], "partner-3dque")
        self.assertIn(payload["event_name"], ALLOWED_EVENT_NAMES)

    def test_first_use_milestones_deduplicate_locally(self):
        client, _ = self.make_client()
        self.assertTrue(client.emit("first_stock_recorded"))
        self.assertFalse(client.emit("first_stock_recorded"))
        self.assertTrue(client.emit("first_backup_exported"))
        self.assertFalse(client.emit("first_backup_exported"))
        queue = json.loads(client.queue_path.read_text(encoding="utf-8"))
        self.assertEqual([item["payload"]["event_name"] for item in queue], [
            "first_stock_recorded", "first_backup_exported",
        ])

    def test_lighthouse_outage_is_fail_open_and_retries_are_bounded(self):
        def offline(_payload):
            raise OSError("offline")

        client, _ = self.make_client(sender=offline)
        self.assertTrue(client.emit("update_check_manual"))
        for _ in range(MAX_ATTEMPTS):
            queue = json.loads(client.queue_path.read_text(encoding="utf-8"))
            if queue:
                queue[0]["next_attempt_at"] = 0
                client.queue_path.write_text(json.dumps(queue), encoding="utf-8")
            client.flush(max_events=1)
        self.assertEqual(json.loads(client.queue_path.read_text(encoding="utf-8")), [])
        self.assertEqual(client.status()["dead_letter_count"], 1)
        self.assertEqual(len(json.loads(client.dead_letter_path.read_text(encoding="utf-8"))), 1)

    def test_rejected_event_is_dead_lettered_and_counted(self):
        client, _ = self.make_client(sender=lambda _payload: 404)
        self.assertTrue(client.emit("update_check_manual"))
        self.assertEqual(client.flush(), 1)
        self.assertEqual(json.loads(client.queue_path.read_text(encoding="utf-8")), [])
        self.assertEqual(client.status()["rejected_count"], 1)
        self.assertEqual(client.status()["dead_letter_count"], 1)

    def test_success_requires_matching_event_acknowledgement(self):
        client, _ = self.make_client(sender=lambda _payload: DeliveryResult(status=202))
        self.assertTrue(client.emit("first_stock_recorded"))
        for _ in range(MAX_ATTEMPTS):
            queue = json.loads(client.queue_path.read_text(encoding="utf-8"))
            if queue:
                queue[0]["next_attempt_at"] = 0
                client.queue_path.write_text(json.dumps(queue), encoding="utf-8")
            client.flush(max_events=1)
        status = client.status()
        self.assertEqual(status["acknowledged_count"], 0)
        self.assertEqual(status["dead_letter_count"], 1)
        self.assertEqual(status["last_error_category"], "missing_acknowledgement")

    def test_milestone_is_committed_only_after_acknowledgement(self):
        client, _ = self.make_client(sender=lambda _payload: DeliveryResult(status=None, error_category="offline"))
        self.assertTrue(client.emit("first_stock_recorded"))
        self.assertFalse(client.state_path.exists(), "queueing alone must not commit milestone state")

        queued = json.loads(client.queue_path.read_text(encoding="utf-8"))
        event_id = queued[0]["payload"]["event_id"]
        client.sender = lambda _payload: DeliveryResult(
            status=202,
            acknowledged_event_ids=frozenset({event_id}),
        )
        client.flush(max_events=1)
        state = json.loads(client.state_path.read_text(encoding="utf-8"))
        self.assertIn("first_stock_recorded", state["milestones"])
        self.assertEqual(client.status()["acknowledged_count"], 1)

    def test_version_dedupe_key_is_scoped_to_the_app_version(self):
        client, _ = self.make_client()
        self.assertTrue(client.emit("version_first_seen"))
        self.assertFalse(client.emit("version_first_seen"))
        self.assertNotIn("active_day", ALLOWED_EVENT_NAMES)
        self.assertFalse(client.emit("active_day"))

    def test_opt_out_queue_clear_removes_unsent_events(self):
        client, _ = self.make_client()
        self.assertTrue(client.emit("update_check_manual"))
        client.clear_queue()
        self.assertEqual(json.loads(client.queue_path.read_text(encoding="utf-8")), [])
        self.assertEqual(json.loads(client.dead_letter_path.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
