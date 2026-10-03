"""Durable, read-only snapshot for the Global Markets client surface.

The Global Markets HTTP request must never compose the macro pack, fetch a
vendor, calculate history, or invoke an LLM.  Those jobs run in the macro
runtime; this module only atomically writes their completed output and reads it
back for the web API.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    raw = (os.getenv("KIP_DATA_DIR") or os.getenv("INSTITUTIONAL_WAREHOUSE_ROOT") or "").strip()
    root = Path(raw) if raw else Path(__file__).resolve().parents[1] / "data"
    path = root / "global_market_snapshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _key(country: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in (country or "India")).strip("_") or "india"


def _path(country: str) -> Path:
    return _root() / f"{_key(country)}.json"


def _publish_to_web_engine(payload: dict[str, Any]) -> dict[str, Any]:
    """Publish a worker result to the web engine's persistent storage.

    Render services have independent local disks. The worker must therefore
    hand its completed snapshot to the HTTP service that reads it for visitors.
    """
    if str(os.getenv("AGI_ROLE") or "").strip().lower() != "gather_worker":
        return {"attempted": False, "reason": "not_gather_worker"}
    url = (os.getenv("MIE_SNAPSHOT_PUBLISH_URL") or
           "https://agib-intelligence-engine.onrender.com/v1/mie/snapshot").strip()
    if not url:
        return {"attempted": False, "reason": "publish_url_missing"}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    token = (os.getenv("MIE_SNAPSHOT_PUBLISH_TOKEN") or "").strip()
    if token:
        request.add_header("X-AGI-Snapshot-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return {"attempted": True, "ok": 200 <= response.status < 300, "status_code": response.status}
    except Exception as exc:
        return {"attempted": True, "ok": False, "error": str(exc)[:180]}


def save(pack: dict[str, Any], *, country: str) -> dict[str, Any]:
    """Persist a completed runtime pack.  A failed pack is never published."""
    if not isinstance(pack, dict) or not pack.get("ok"):
        return {"ok": False, "reason": "pack_not_publishable"}
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "ok": True,
        "snapshot_type": "global_macro_snapshot",
        "country": country,
        "generated_at": pack.get("generated_at") or now,
        "published_at": now,
        "data_status": "CACHED",
        "source": "macro_intelligence_runtime",
        "pack": pack,
    }
    # A dedicated Render worker has its own filesystem and must not attempt to
    # create the web engine's mounted disk path. Publish directly to the
    # authenticated web tier, which owns the visitor-facing snapshot storage.
    if str(os.getenv("AGI_ROLE") or "").strip().lower() == "gather_worker":
        remote = _publish_to_web_engine(payload)
        return {
            "ok": bool(remote.get("ok")),
            "published_at": now,
            "web_engine_publish": remote,
        }
    target = _path(country)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temp.replace(target)
    return {
        "ok": True,
        "path": str(target),
        "published_at": now,
        "web_engine_publish": _publish_to_web_engine(payload),
    }


def read(country: str = "Global") -> dict[str, Any]:
    """Return the latest saved snapshot only; this function performs no calculation."""
    requested = (country or "Global").strip() or "Global"
    candidates = [requested]
    # Global data is introduced independently. Until its feed is connected, the
    # India macro snapshot gives the page an honest India-first read-through.
    if requested.lower() == "global":
        candidates.append("India")
    for candidate in candidates:
        try:
            payload = json.loads(_path(candidate).read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("pack"), dict):
                payload["requested_scope"] = requested
                payload["served_scope"] = candidate
                payload["fallback"] = candidate.lower() != requested.lower()
                return payload
        except FileNotFoundError:
            continue
        except Exception as exc:
            return {
                "ok": False,
                "snapshot_type": "global_macro_snapshot",
                "requested_scope": requested,
                "status": "DATA_QUALITY_WARNING",
                "error": f"snapshot_unreadable:{str(exc)[:120]}",
            }
    return {
        "ok": False,
        "snapshot_type": "global_macro_snapshot",
        "requested_scope": requested,
        "status": "AWAITING_SNAPSHOT",
        "message": "The global snapshot has not been published by the background macro runtime yet.",
    }
