"""NSE Corporate Announcements collector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from live_data import store
from live_data.collectors.base import (
    collector_envelope,
    fallback_to_snapshot,
    http_get,
    nse_session_opener,
    run_with_retry,
)
from live_data.schema import DEFAULT_RETRY

COLLECTOR_ID = "lidi_nse_announcements_v1"
SOURCE_ID = "nse_announcements"
OFFICIAL = "NSE India"
SAMPLES = Path(__file__).resolve().parents[1] / "samples"

# Public corporate announcement endpoints (attempted; may require session cookies).
ANNOUNCEMENT_URLS = (
    "https://www.nseindia.com/api/corporate-announcements?index=equities",
    "https://www.nseindia.com/api/corp-info?corpType=announcements",
)


def collect_nse_announcements(
    *,
    injected_json: dict[str, Any] | str | None = None,
    allow_recorded_sample: bool = False,
) -> dict[str, Any]:
    mode = "live"
    payload_obj: dict[str, Any] | None = None
    raw_bytes: bytes | None = None
    url_used = None
    try:
        if injected_json is not None:
            mode = "injected"
            if isinstance(injected_json, str):
                payload_obj = json.loads(injected_json)
                raw_bytes = injected_json.encode("utf-8")
            else:
                payload_obj = injected_json
                raw_bytes = json.dumps(injected_json).encode("utf-8")
        else:
            def _fetch() -> bytes:
                nonlocal url_used
                last = None
                opener = nse_session_opener()
                for url in ANNOUNCEMENT_URLS:
                    try:
                        data = http_get(
                            url,
                            headers={
                                "User-Agent": (
                                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                                ),
                                "Accept": "application/json,text/plain,*/*",
                                "Accept-Language": "en-US,en;q=0.9",
                                "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
                            },
                            timeout=25,
                            opener=opener,
                        )
                        url_used = url
                        return data
                    except Exception as exc:  # noqa: BLE001
                        last = exc
                raise RuntimeError(f"nse_announcements_fetch_failed:{last}")

            try:
                policy = {"max_attempts": 1, "backoff_seconds": [0]} if allow_recorded_sample else DEFAULT_RETRY
                raw_bytes = run_with_retry(_fetch, retry_policy=policy)
                payload_obj = json.loads(raw_bytes.decode("utf-8", errors="replace"))
            except Exception as live_exc:
                if allow_recorded_sample:
                    sample = SAMPLES / "nse_announcements.json"
                    mode = "recorded_sample"
                    raw_bytes = sample.read_bytes()
                    payload_obj = json.loads(raw_bytes.decode("utf-8"))
                    url_used = str(sample)
                else:
                    fb = fallback_to_snapshot(
                        collector_id=COLLECTOR_ID,
                        source_id=SOURCE_ID,
                        entity="LATEST",
                        reason=str(live_exc)[:200],
                    )
                    store.update_collector_health(
                        COLLECTOR_ID,
                        source=SOURCE_ID,
                        last_failure=store.utc_now(),
                        failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
                        last_error=str(live_exc)[:200],
                        version=COLLECTOR_ID,
                        frequency="intraday_poll",
                        retry_policy=DEFAULT_RETRY,
                    )
                    return fb or {
                        "ok": False,
                        "collector_id": COLLECTOR_ID,
                        "source_id": SOURCE_ID,
                        "official_source": OFFICIAL,
                        "reason": "live_unavailable_no_snapshot",
                        "error": str(live_exc)[:240],
                        "fixture": False,
                        "fabricated": False,
                        "transparent_insufficiency": True,
                    }

        assert payload_obj is not None and raw_bytes is not None
        events = _normalize_events(payload_obj)
        if isinstance(payload_obj, dict):
            effective = payload_obj.get("effective_date") or (events[0].get("effective_date") if events else None)
        else:
            effective = events[0].get("effective_date") if events else store.utc_now()[:10]
        if not events and mode == "live":
            raise RuntimeError("nse_announcements_empty_or_unparseable_payload")
        file_rec = store.put_raw_file(SOURCE_ID, "announcements.json", raw_bytes, meta={"mode": mode, "url": url_used})
        env = collector_envelope(
            collector_id=COLLECTOR_ID,
            source_id=SOURCE_ID,
            official_source=OFFICIAL,
            payload={"effective_date": effective, "events": events, "event_count": len(events), "url": url_used},
            effective_date=effective,
            checksum=file_rec["checksum"],
            mode=mode,
            downloaded_files=[file_rec],
            confidence=0.9 if mode == "live" else 0.75,
        )
        store.put_raw(SOURCE_ID, "LATEST", env)
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            version=COLLECTOR_ID,
            frequency="intraday_poll",
            retry_policy=DEFAULT_RETRY,
            last_success=store.utc_now(),
            last_checksum=file_rec["checksum"],
            success_count=(store.get_collector_health(COLLECTOR_ID).get("success_count") or 0) + 1,
            downloaded_files=[file_rec.get("path")],
            metadata={"event_count": len(events), "mode": mode},
        )
        return env
    except Exception as exc:  # noqa: BLE001
        fb = fallback_to_snapshot(
            collector_id=COLLECTOR_ID, source_id=SOURCE_ID, entity="LATEST", reason=str(exc)[:200]
        )
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            last_failure=store.utc_now(),
            failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
            last_error=str(exc)[:200],
        )
        return fb or {
            "ok": False,
            "collector_id": COLLECTOR_ID,
            "source_id": SOURCE_ID,
            "official_source": OFFICIAL,
            "reason": "collect_failed",
            "error": str(exc)[:240],
            "fixture": False,
            "fabricated": False,
            "transparent_insufficiency": True,
        }


def _normalize_events(obj: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        raw_events = obj
        default_eff = None
    elif isinstance(obj, dict):
        raw_events = obj.get("events") or obj.get("data") or obj.get("Table") or obj.get("announcements") or []
        default_eff = obj.get("effective_date")
    else:
        return []
    out = []
    for e in raw_events if isinstance(raw_events, list) else []:
        if not isinstance(e, dict):
            continue
        sym = (e.get("symbol") or e.get("SYMBOL") or e.get("sm_name") or "").upper()
        if not sym:
            continue
        raw_dt = e.get("an_dt") or e.get("datetime") or e.get("sort_date") or e.get("date") or ""
        eff = _coerce_date(raw_dt) or default_eff
        out.append(
            {
                "symbol": sym,
                "headline": e.get("headline") or e.get("desc") or e.get("subject") or e.get("TITLE"),
                "category": e.get("category") or e.get("desc") or e.get("an_tt"),
                "subcategory": e.get("subcategory") or e.get("an_sub"),
                "effective_date": eff,
                "description": e.get("desc") or e.get("description"),
                "attachment": e.get("attchmntFile") or e.get("attchmntText"),
            }
        )
    return out


def _coerce_date(value: Any) -> str | None:
    from datetime import datetime

    s = str(value or "").strip()
    if not s:
        return None
    # ISO / NSE styles
    for cand in (s[:10], s.split("T")[0], s.split(" ")[0]):
        try:
            return datetime.fromisoformat(cand).date().isoformat()
        except Exception:
            pass
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:11].strip(), fmt).date().isoformat()
        except Exception:
            continue
    return None
