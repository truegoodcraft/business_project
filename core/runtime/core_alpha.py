from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.auth.google_sa import validate_google_service_account
from core.capabilities import registry
from core.capabilities.registry import MANIFEST_PATH
from core.broker.runtime import Broker
from core.contracts.plugin_v2 import PluginV2
from core.runtime.crypto import decrypt, encrypt
from core.runtime.journal import JournalManager
from core.runtime.policy import PolicyEngine
from core.runtime.sandbox import SandboxError, run_transform
from core.runtime import set_broker
from core.secrets import Secrets
from core.settings.reader import load_reader_settings
from core.version import VERSION
from tgc.bootstrap_fs import DATA, LOGS, ensure_first_run


@dataclass
class PluginRecord:
    id: str
    name: str
    version: str
    services: List[str]
    scopes: List[str]
    manifest: Dict[str, Any]
    configured: bool
    instance: PluginV2 = field(repr=False)


class CoreAlpha:
    def __init__(self, *, policy_path: Path) -> None:
        self.run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self.bootstrap = ensure_first_run()
        self.policy = PolicyEngine(policy_path)
        self.journal = JournalManager(DATA)
        self.broker = Broker(
            Secrets,
            lambda name: logging.getLogger(f"core.{name}" if name else "core"),
            registry,
            load_reader_settings,
        )
        set_broker(self.broker)
        self._lock = threading.Lock()
        self._plugins: List[PluginRecord] = []
        self.session_token: Optional[str] = None
        self._load_plugins()
        self._register_core_capabilities()

    @property
    def plugins(self) -> List[PluginRecord]:
        return list(self._plugins)

    def _load_plugins(self) -> None:
        from core.plugins_alpha import discover_alpha_plugins

        plugins: List[PluginRecord] = []
        for plugin in discover_alpha_plugins():
            manifest = plugin.manifest()
            try:
                desc = plugin.describe() or {}
            except Exception:
                desc = {}
            services = [str(s) for s in desc.get("services", []) if isinstance(s, str)]
            scopes = [str(s) for s in desc.get("scopes", []) if isinstance(s, str)]
            configured = bool(services)
            record = PluginRecord(
                id=str(getattr(plugin, "id", plugin.__class__.__name__)),
                name=str(getattr(plugin, "name", plugin.__class__.__name__)),
                version=str(getattr(plugin, "version", "0")),
                services=services,
                scopes=scopes,
                manifest=manifest,
                configured=configured,
                instance=plugin,
            )
            plugins.append(record)
            self._register_capabilities(record)
            if configured and hasattr(plugin, "register_broker"):
                try:
                    plugin.register_broker(self.broker)
                except Exception:
                    pass
        self._plugins = plugins
        try:
            from core.plugins.loader import all_plugins

            for module in all_plugins().values():
                register_fn = getattr(module, "register_broker", None)
                if callable(register_fn):
                    try:
                        register_fn(self.broker)
                    except Exception:
                        continue
        except Exception:
            pass
        registry.emit_manifest_async()

    def _register_capabilities(self, record: PluginRecord) -> None:
        provides = record.manifest.get("provides", [])
        requires = record.manifest.get("requires", [])
        if not isinstance(provides, list):
            provides = []
        status = "pending" if record.configured else "blocked"
        reason = None if record.configured else "plugin_not_configured"
        for cap in provides:
            policy_block = {"allowed": record.configured, "reason": reason}
            if requires:
                policy_block["requires"] = requires
            registry.upsert(cap, provider=record.id, status=status, policy=policy_block)

    def _register_core_capabilities(self) -> None:
        ok, meta = validate_google_service_account()
        registry.upsert(
            "auth.google.service_account",
            provider="core",
            status="ready" if ok else "blocked",
            policy={"allowed": ok, "reason": None if ok else meta.get("detail", "missing")},
            meta={k: v for k, v in meta.items() if k in {"project_id", "client_email", "path_exists"}},
        )

    def configure_session_token(self, token: str) -> None:
        self.session_token = token

    # ---- primitives ----
    def read(self, source: str, selector: Dict[str, Any], limits: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        decision = self.policy.evaluate("read", {"source": source, **(selector or {})})
        return {
            "source": source,
            "selector": selector or {},
            "limits": limits or {},
            "allowed": decision.allowed,
            "reasons": list(decision.reasons),
        }

    def transform(
        self,
        *,
        plugin_id: str,
        fn: str,
        input_payload: Dict[str, Any],
        limits: Optional[Dict[str, Any]],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        metadata = {"plugin": plugin_id, "fn": fn}
        policy_decision = self.policy.evaluate("transform", metadata)
        if not policy_decision.allowed:
            return {"proposal": None, "policy": policy_decision}
        payload = {"input": input_payload, "limits": limits or {}}
        try:
            result = run_transform(plugin_id, fn, payload)
        except SandboxError as exc:
            return {"proposal": {"error": str(exc)}, "policy": policy_decision}
        proposal = result.get("proposal") or {}
        inputs_hash = hashlib.sha256(json.dumps(input_payload, sort_keys=True).encode("utf-8")).hexdigest()
        proposal_hash = hashlib.sha256(json.dumps(proposal, sort_keys=True).encode("utf-8")).hexdigest()
        try:
            self.journal.prepare(
                run_id=self.run_id,
                actor=plugin_id,
                intent="transform",
                idempotency_key=idempotency_key,
                inputs_hash=inputs_hash,
                proposal_hash=proposal_hash,
                policy_version=self.policy.version,
            )
        except ValueError as exc:
            return {"proposal": {"error": str(exc)}, "policy": policy_decision}
        for record in self._plugins:
            if record.id == plugin_id:
                for cap in record.manifest.get("provides", []):
                    registry.upsert(
                        cap,
                        provider=plugin_id,
                        status="ready",
                        policy={"allowed": True},
                    )
        registry.emit_manifest_async()
        return {"proposal": proposal, "policy": policy_decision}

    def write(self, target: str, proposal: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        metadata = {"target": target}
        decision = self.policy.evaluate("write", metadata)
        if not decision.allowed:
            return {"status": "denied", "policy": decision}
        inputs_hash = hashlib.sha256(json.dumps({"target": target}, sort_keys=True).encode("utf-8")).hexdigest()
        proposal_hash = hashlib.sha256(json.dumps(proposal, sort_keys=True).encode("utf-8")).hexdigest()
        try:
            journal_entry = self.journal.prepare(
                run_id=self.run_id,
                actor="core",
                intent="write",
                idempotency_key=idempotency_key,
                inputs_hash=inputs_hash,
                proposal_hash=proposal_hash,
                policy_version=self.policy.version,
            )
        except ValueError as exc:
            return {"status": "error", "policy": decision, "error": str(exc)}
        self.journal.commit(journal_entry["journal_id"], result="commit")
        return {"status": "committed", "policy": decision, "journal_id": journal_entry["journal_id"]}

    def encrypt(self, dek_id: str, chunks: List[Any]) -> List[str]:
        return encrypt(dek_id, chunks)

    def decrypt(self, dek_id: str, chunks: List[str]) -> List[str]:
        return decrypt(dek_id, chunks)

    # ---- transparency ----
    def transparency_report(self) -> Dict[str, Any]:
        enabled = [p.id for p in self._plugins if p.configured]
        caps = [
            {
                "cap": cap.cap,
                "provider": cap.provider,
                "status": cap.status,
                "policy": cap.policy,
            }
            for cap in registry.list()
        ]
        return {
            "version": VERSION,
            "policy_mode": self.policy.mode,
            "telemetry": "off",
            "enabled_plugins": enabled,
            "capability_summary": caps,
            "journal_path": str(self.journal.journal_path),
            "audit_path": str(self.journal.audit_path),
            "manifest_path": str(MANIFEST_PATH),
            "data_paths": [str(DATA), str(LOGS)],
            "retention_policy": {"journal": "manual", "logs": "manual"},
        }

    def plugin_list(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for record in self._plugins:
            if not record.configured:
                continue
            out.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "services": record.services,
                    "scopes": record.scopes,
                    "version": record.version,
                }
            )
        return out

    def update_capabilities_after_probe(self, results: Dict[str, Dict[str, Any]]) -> None:
        for record in self._plugins:
            if not record.configured:
                continue
            service_ok = any(results.get(svc, {}).get("ok") for svc in record.services)
            status = "ready" if service_ok else "blocked"
            policy = {"allowed": service_ok}
            if not service_ok:
                policy["reason"] = "probe_failed"
            for cap in record.manifest.get("provides", []):
                registry.upsert(cap, provider=record.id, status=status, policy=policy)
        registry.emit_manifest_async()

    def probe_services(self, services: List[str]) -> Dict[str, Any]:
        from core.runtime.probe import probe_services

        results = probe_services(self.broker, services)
        self.update_capabilities_after_probe(results)
        return results


__all__ = ["CoreAlpha", "PluginRecord"]
