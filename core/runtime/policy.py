from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    reasons: Tuple[str, ...]
    version: str

    @property
    def allowed(self) -> bool:
        return self.decision.lower() == "allow"


class PolicyEngine:
    """Simple deny-by-default policy engine."""

    def __init__(self, policy_path: Path) -> None:
        self._path = policy_path
        self._lock = threading.Lock()
        self._mode = "enforce"
        self._version = "default"
        self._rules: List[Dict[str, Any]] = []
        self._load()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def version(self) -> str:
        return self._version

    def _load(self) -> None:
        with self._lock:
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                data = {}
            except json.JSONDecodeError as exc:
                data = {"_error": str(exc)}
            self._mode = str(data.get("mode") or "enforce").lower()
            self._version = str(data.get("version") or "default")
            rules = data.get("rules")
            if isinstance(rules, list):
                self._rules = [r for r in rules if isinstance(r, dict)]
            else:
                self._rules = []

    def reload(self) -> None:
        self._load()

    def evaluate(self, intent: str, metadata: Dict[str, Any]) -> PolicyDecision:
        intent = (intent or "").lower().strip()
        reasons: List[str] = []
        decision = "deny"
        for rule in list(self._rules):
            if rule.get("intent") != intent:
                continue
            conditions = rule.get("conditions")
            if not self._conditions_match(conditions, metadata):
                continue
            decision = str(rule.get("decision") or "deny").lower()
            reason = str(rule.get("reason") or rule.get("id") or "policy_rule")
            reasons.append(reason)
            break
        if not reasons:
            reasons.append("no_matching_rule")
        return PolicyDecision(decision=decision, reasons=tuple(reasons), version=self._version)

    def simulate(self, intent: str, metadata: Dict[str, Any]) -> PolicyDecision:
        return self.evaluate(intent, metadata)

    @staticmethod
    def _conditions_match(conditions: Any, metadata: Dict[str, Any]) -> bool:
        if not conditions:
            return True
        if isinstance(conditions, dict):
            for key, expected in conditions.items():
                if isinstance(expected, Iterable) and not isinstance(expected, (str, bytes, dict)):
                    if str(metadata.get(key)) not in {str(v) for v in expected}:
                        return False
                else:
                    if str(metadata.get(key)) != str(expected):
                        return False
            return True
        return False
