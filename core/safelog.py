import logging
import os
import re

_PATTERNS = [
    r"(?i)bearer\s+[A-Za-z0-9._-]+",
    os.getenv("NOTION_TOKEN") or "",
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "",
]


def _redact(s: str) -> str:
    t = s
    for pat in _PATTERNS:
        if pat:
            t = re.sub(pat, "***", t)
    return t


class SafeLogger(logging.Logger):
    def _log(self, level, msg, args, **kw):
        super()._log(level, _redact(str(msg)), tuple(_redact(str(a)) for a in args), **kw)


logging.setLoggerClass(SafeLogger)
logger = logging.getLogger("tgc")
