"""File cache helpers for AI outputs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .settings import CACHE_DIR


def _cache_path(subdir: str, key: str) -> Path:
    safe_key = key.replace("/", "_").replace(" ", "-")
    d = CACHE_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe_key}.json"


def _read_cache(subdir: str, key: str, max_age_hours: float = 0) -> dict[str, Any] | None:
    path = _cache_path(subdir, key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if max_age_hours > 0:
            ts = float(data.get("_timestamp", 0) or 0)
            if time.time() - ts > max_age_hours * 3600:
                return None
        return data
    except Exception:
        return None


def _write_cache(subdir: str, key: str, data: dict[str, Any]) -> None:
    payload = dict(data)
    payload["_timestamp"] = time.time()
    _cache_path(subdir, key).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

