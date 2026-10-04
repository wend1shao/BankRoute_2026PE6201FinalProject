"""Privacy-preserving local audit logging.

Logs contain request IDs, decisions, redacted text, scores, flags and latency.
They intentionally omit API keys and the original unredacted customer message.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .config import LOG_DIR


def write_audit_event(event: Dict[str, Any], log_dir: Path = LOG_DIR) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    safe = dict(event)
    safe.pop("original_message", None)
    safe["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    with (log_dir / "audit.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(safe, ensure_ascii=False) + "\n")

