"""Base live collector — retries, checksums, snapshot fallback (never silent fixtures)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any

from live_data import store
from live_data.schema import DEFAULT_RETRY, LIDI_VERSION


class LiveCollectorError(Exception):
    pass


def http_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    opener: urllib.request.OpenerDirector | None = None,
) -> bytes:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": (
                "Mozilla/5.0 (compatible; AGIB-LIDI/1.0; +https://github.com/shivamagw06-dev/AGIB)"
            ),
            "Accept": "*/*",
        },
    )
    open_fn = opener.open if opener else urllib.request.urlopen
    with open_fn(req, timeout=timeout) as resp:
        return resp.read()


def nse_session_opener() -> urllib.request.OpenerDirector:
    """Bootstrap NSE cookie jar via homepage — required for many JSON APIs."""
    import http.cookiejar

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    try:
        http_get(
            "https://www.nseindia.com/",
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)",
                "Accept": "text/html,*/*",
            },
            timeout=15,
            opener=opener,
        )
    except Exception:
        pass
    return opener


def run_with_retry(fn, *, retry_policy: dict[str, Any] | None = None) -> Any:
    policy = {**DEFAULT_RETRY, **(retry_policy or {})}
    attempts = int(policy.get("max_attempts") or 1)
    backoff = list(policy.get("backoff_seconds") or [1])
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — collector boundary
            last_exc = exc
            if i < attempts - 1:
                time.sleep(float(backoff[min(i, len(backoff) - 1)]))
    raise LiveCollectorError(str(last_exc) if last_exc else "retry_exhausted")


def collector_envelope(
    *,
    collector_id: str,
    source_id: str,
    official_source: str,
    payload: dict[str, Any],
    effective_date: str | None,
    checksum: str | None,
    mode: str,
    downloaded_files: list[dict[str, Any]] | None = None,
    confidence: float = 0.9,
) -> dict[str, Any]:
    now = store.utc_now()
    return {
        "ok": True,
        "lidi_version": LIDI_VERSION,
        "collector_id": collector_id,
        "source_id": source_id,
        "official_source": official_source,
        "mode": mode,  # live | snapshot | injected
        "retrieved_at": now,
        "available_from": now,
        "effective_date": effective_date,
        "source_version": LIDI_VERSION,
        "checksum": checksum,
        "downloaded_files": downloaded_files or [],
        "payload": payload,
        "provenance": {
            "official_source": official_source,
            "collector": collector_id,
            "retrieved_at": now,
            "validated_at": None,
            "derived_from": None,
            "confidence": confidence,
            "version": LIDI_VERSION,
            "fabricated": False,
        },
        "fabricated": False,
        "fixture": False,
    }


def fallback_to_snapshot(
    *,
    collector_id: str,
    source_id: str,
    entity: str,
    reason: str,
) -> dict[str, Any] | None:
    snap = store.get_latest_snapshot(source_id, entity)
    if not snap:
        store.log_fallback(
            {
                "collector_id": collector_id,
                "source_id": source_id,
                "entity": entity,
                "reason": reason,
                "outcome": "no_snapshot",
                "used_fixture": False,
            }
        )
        return None
    store.log_fallback(
        {
            "collector_id": collector_id,
            "source_id": source_id,
            "entity": entity,
            "reason": reason,
            "outcome": "latest_validated_snapshot",
            "used_fixture": False,
            "snapshot_age_hint": snap.get("retrieved_at") or snap.get("available_from"),
        }
    )
    out = dict(snap)
    out["mode"] = "snapshot"
    out["ok"] = True
    out["fallback"] = True
    out["fallback_reason"] = reason
    out["freshness"] = "stale_or_snapshot"
    out["transparent_insufficiency"] = True
    out["fixture"] = False
    prov = dict(out.get("provenance") or {})
    prov["confidence"] = min(float(prov.get("confidence") or 0.5), 0.5)
    prov["fallback"] = "latest_validated_snapshot"
    out["provenance"] = prov
    return out
