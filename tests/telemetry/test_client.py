from __future__ import annotations

import inspect
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from core.telemetry.client import ALLOWED_EVENT_NAMES, MAX_ATTEMPTS, TelemetryClient
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
        sender = overrides.pop("sender", lambda payload: sent.append(payload) or 202)
        client = TelemetryClient(
            state_path=overrides.pop("state_path", self.root / "state.json"),
            queue_path=overrides.pop("queue_path", self.root / "queue.json"),
            sender=sender,
            enabled_getter=overrides.pop("enabled_getter", lambda: True),
            channel_getter=overrides.pop("channel_getter", lambda: "stable"),
            start_background=False,
            **overrides,
        )
        return client, sent

    def test_disabled_telemetry_sends_and_writes_nothing(self):
        client, sent = self.make_client(enabled_getter=lambda: False)
        self.assertFalse(client.emit("inventory_opened"))
        self.assertEqual(client.flush(), 0)
        self.assertEqual(sent, [])
        self.assertFalse(client.state_path.exists())
        self.assertFalse(client.queue_path.exists())

    def test_default_waits_for_disclosure_before_delivery(self):
        config = Config()
        self.assertTrue(config.telemetry.enabled)
        self.assertFalse(config.telemetry.disclosure_acknowledged)

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

    def test_installation_identifier_is_random_uuid4_and_persistent(self):
        first, _ = self.make_client()
        identifier = first.installation_id()
        self.assertEqual(uuid.UUID(identifier).version, 4)
        second, _ = self.make_client()
        self.assertEqual(second.installation_id(), identifier)
        other_root = self.root / "other"
        other, _ = self.make_client(
            state_path=other_root / "state.json",
            queue_path=other_root / "queue.json",
        )
        self.assertNotEqual(other.installation_id(), identifier)

    def test_payload_is_exact_and_cannot_accept_business_content(self):
        client, _ = self.make_client()
        payload = client.build_payload("inventory_opened")
        self.assertEqual(set(payload), {
            "schema_version", "event_id", "event_name", "installation_id", "client_ts", "context",
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
        payload = client.build_payload("settings_opened")
        self.assertEqual(payload["context"]["app_version"], VERSION)
        self.assertEqual(payload["context"]["release_channel"], "partner-3dque")
        self.assertIn(payload["event_name"], ALLOWED_EVENT_NAMES)

    def test_milestones_deduplicate_but_module_events_do_not(self):
        client, _ = self.make_client()
        self.assertTrue(client.emit("first_inventory_item_created"))
        self.assertFalse(client.emit("first_inventory_item_created"))
        self.assertTrue(client.emit("inventory_opened"))
        self.assertTrue(client.emit("inventory_opened"))
        queue = json.loads(client.queue_path.read_text(encoding="utf-8"))
        self.assertEqual([item["payload"]["event_name"] for item in queue], [
            "first_inventory_item_created", "inventory_opened", "inventory_opened",
        ])

    def test_lighthouse_outage_is_fail_open_and_retries_are_bounded(self):
        def offline(_payload):
            raise OSError("offline")

        client, _ = self.make_client(sender=offline)
        self.assertTrue(client.emit("inventory_opened"))
        for _ in range(MAX_ATTEMPTS):
            queue = json.loads(client.queue_path.read_text(encoding="utf-8"))
            if queue:
                queue[0]["next_attempt_at"] = 0
                client.queue_path.write_text(json.dumps(queue), encoding="utf-8")
            client.flush(max_events=1)
        self.assertEqual(json.loads(client.queue_path.read_text(encoding="utf-8")), [])

    def test_older_server_response_drops_safely(self):
        client, _ = self.make_client(sender=lambda _payload: 404)
        self.assertTrue(client.emit("inventory_opened"))
        self.assertEqual(client.flush(), 1)
        self.assertEqual(json.loads(client.queue_path.read_text(encoding="utf-8")), [])

    def test_opt_out_queue_clear_removes_unsent_events(self):
        client, _ = self.make_client()
        self.assertTrue(client.emit("inventory_opened"))
        client.clear_queue()
        self.assertEqual(json.loads(client.queue_path.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
