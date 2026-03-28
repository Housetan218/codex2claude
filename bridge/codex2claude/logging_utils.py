from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .paths import logs_dir


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_bridge_log(event: dict[str, object]) -> None:
    log_path = logs_dir() / "bridge.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": utc_now(), **event}
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
