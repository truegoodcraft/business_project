import logging
import os
import re

_PATTERNS = [
    r"(?i)bearer\s+[A-Za-z0-9._-]+",
    os.getenv("NOTION_TOKEN") or "",
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "",
]


def _compile_pattern(pat: str):
    if not pat:
        return None
    if pat.startswith("(?i)"):
        return re.compile(pat, re.IGNORECASE)
    return re.compile(re.escape(pat), re.IGNORECASE)


try:
    _REDACT_COMPILED = [rx for rx in (_compile_pattern(p) for p in _PATTERNS) if rx]
except NameError:
    _REDACT_COMPILED = None  # will be initialised lazily


def _ensure_compiled():
    global _REDACT_COMPILED
    if _REDACT_COMPILED is None:
        from core import safelog as _safelog

        _REDACT_COMPILED = [
            rx for rx in (_compile_pattern(p) for p in _safelog._PATTERNS) if rx
        ]


def _redact(s: str):
    if not isinstance(s, str):
        return s
    _ensure_compiled()
    t = s
    for rx in _REDACT_COMPILED:
        t = rx.sub("***", t)
    return t


class SafeLogger(logging.Logger):
    def _log(self, level, msg, args, **kw):
        super()._log(level, _redact(str(msg)), tuple(_redact(str(a)) for a in args), **kw)


logging.setLoggerClass(SafeLogger)
logger = logging.getLogger("tgc")
