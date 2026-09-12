"""NSE Bhavcopy live collector — prices/volumes primitives only (no derived PE)."""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from live_data import store
from live_data.collectors.base import (
    collector_envelope,
    fallback_to_snapshot,
    http_get,
    run_with_retry,
)
from live_data.schema import DEFAULT_RETRY

COLLECTOR_ID = "lidi_nse_bhavcopy_v1"
SOURCE_ID = "nse_bhavcopy"
OFFICIAL = "NSE India"
SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _candidate_dates(as_of: datetime | None = None, lookback: int = 10) -> list[datetime]:
    d0 = as_of or datetime.utcnow()
    out = []
    for i in range(lookback):
        d = d0 - timedelta(days=i)
        if d.weekday() < 5:
            out.append(d)
    return out


def bhavcopy_urls(d: datetime) -> list[str]:
    """Authoritative NSE archive URL patterns (attempted in order)."""
    dd = d.strftime("%d")
    mmm = d.strftime("%b").upper()
    yyyy = d.strftime("%Y")
    mon = d.strftime("%m")
    return [
        f"https://archives.nseindia.com/content/historical/EQUITIES/{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip",
        f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip",
        # Newer CDN-style path variants occasionally used by NSE
        f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{dd}{mon}{yyyy}.csv",
    ]


def parse_bhavcopy_csv(text: str) -> tuple[str | None, list[dict[str, Any]]]:
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, Any]] = []
    effective = None
    for raw in reader:
        # normalize keys
        row = {(k or "").strip().upper(): (v or "").strip() for k, v in raw.items()}
        sym = row.get("SYMBOL") or row.get("SYMBOL ")
        series = row.get("SERIES") or row.get(" SERIES") or "EQ"
        if not sym:
            continue
        if series and series not in {"EQ", "BE", "SM", "ST"}:
            # keep EQ-primary; still allow common equity series
            if series not in {"EQ", "BE"}:
                continue
        def _f(key: str) -> float | None:
            v = row.get(key)
            if v in (None, ""):
                return None
            try:
                return float(str(v).replace(",", ""))
            except Exception:
                return None

        ts = row.get("TIMESTAMP") or row.get("DATE1") or row.get("DATE")
        if ts and not effective:
            effective = _parse_nse_date(ts)
        item = {
            "symbol": sym.upper(),
            "series": series,
            "open": _f("OPEN"),
            "high": _f("HIGH"),
            "low": _f("LOW"),
            "close": _f("CLOSE") or _f("CLOSE_PRICE"),
            "last": _f("LAST") or _f("LAST_PRICE"),
            "prev_close": _f("PREVCLOSE") or _f("PREV_CLOSE") or _f("PREV_CL"),
            "volume": _f("TOTTRDQTY") or _f("TTL_TRD_QNTY") or _f("VOLUME"),
            "value": _f("TOTTRDVAL") or _f("TURNOVER_LACS") or _f("TURNOVER"),
            "trades": _f("TOTALTRADES") or _f("NO_OF_TRADES"),
            "isin": row.get("ISIN") or None,
            "date": effective,
        }
        if item["close"] is None:
            continue
        # primitive return from prev_close when present (not a stored PE)
        if item["prev_close"] and item["prev_close"] > 0 and item["close"] is not None:
            item["return_1d"] = round((item["close"] / item["prev_close"]) - 1.0, 6)
        else:
            item["return_1d"] = None
        rows.append(item)
    return effective, rows


def _parse_nse_date(ts: str) -> str | None:
    ts = str(ts).strip()
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(ts, fmt).date().isoformat()
        except Exception:
            continue
    return ts[:10] if len(ts) >= 10 else None


def _extract_csv_bytes(data: bytes) -> bytes:
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError("zip_without_csv")
            return zf.read(names[0])
    return data


def collect_nse_bhavcopy(
    *,
    as_of: str | None = None,
    injected_csv: str | bytes | None = None,
    allow_recorded_sample: bool = False,
) -> dict[str, Any]:
    """Collect NSE bhavcopy.

    Modes:
      - injected_csv: explicit test/offline injection (not a silent fixture fallback)
      - live HTTP attempts
      - latest validated snapshot fallback
      - allow_recorded_sample: only when explicitly True (CI/dev), never silent
    """
    downloaded: list[dict[str, Any]] = []
    mode = "live"
    data: bytes | None = None
    used_url = None
    as_of_dt = datetime.fromisoformat(as_of) if as_of else None

    try:
        if injected_csv is not None:
            mode = "injected"
            data = injected_csv.encode("utf-8") if isinstance(injected_csv, str) else injected_csv
        else:
            def _fetch() -> bytes:
                nonlocal used_url
                last_err: Exception | None = None
                for d in _candidate_dates(as_of_dt):
                    for url in bhavcopy_urls(d):
                        try:
                            raw = http_get(
                                url,
                                headers={
                                    "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)",
                                    "Accept": "*/*",
                                    "Referer": "https://www.nseindia.com/",
                                },
                                timeout=25,
                            )
                            used_url = url
                            return raw
                        except Exception as exc:  # noqa: BLE001
                            last_err = exc
                            continue
                raise RuntimeError(f"nse_bhavcopy_fetch_failed:{last_err}")

            try:
                # CI/dev recorded-sample path: one live attempt then explicit sample (never silent).
                policy = {"max_attempts": 1, "backoff_seconds": [0]} if allow_recorded_sample else DEFAULT_RETRY
                data = run_with_retry(_fetch, retry_policy=policy)
            except Exception as live_exc:
                # explicit recorded sample only if requested
                if allow_recorded_sample:
                    sample = SAMPLES / "nse_bhavcopy_cm26JUL2024bhav.csv"
                    if sample.exists():
                        mode = "recorded_sample"
                        data = sample.read_bytes()
                        used_url = str(sample)
                    else:
                        raise live_exc
                else:
                    fb = fallback_to_snapshot(
                        collector_id=COLLECTOR_ID,
                        source_id=SOURCE_ID,
                        entity="LATEST",
                        reason=str(live_exc)[:200],
                    )
                    if fb:
                        store.update_collector_health(
                            COLLECTOR_ID,
                            source=SOURCE_ID,
                            last_failure=store.utc_now(),
                            failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
                            last_error=str(live_exc)[:200],
                            version=COLLECTOR_ID,
                            frequency="daily",
                            retry_policy=DEFAULT_RETRY,
                        )
                        return fb
                    store.update_collector_health(
                        COLLECTOR_ID,
                        source=SOURCE_ID,
                        last_failure=store.utc_now(),
                        failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
                        last_error=str(live_exc)[:200],
                    )
                    return {
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

        assert data is not None
        csv_bytes = _extract_csv_bytes(data)
        digest = hashlib.sha256(csv_bytes).hexdigest()

        # The archive publishes one file per trading day, but this collector runs
        # every cycle. Storing an identical payload again buys nothing and cost
        # 147 MB of duplicates on the worker before this check existed: the same
        # 30 July file was written 248 times. Reuse the stored file instead.
        prior = store.get_collector_health(COLLECTOR_ID) or {}
        if prior.get("last_checksum") == digest:
            existing_paths = [p for p in (prior.get("downloaded_files") or []) if p]
            file_rec = {
                "checksum": digest,
                "path": existing_paths[0] if existing_paths else None,
                "reused": True,
            }
        else:
            file_rec = store.put_raw_file(
                SOURCE_ID,
                Path(used_url or "bhavcopy.csv").name,
                csv_bytes,
                meta={"mode": mode, "url": used_url},
            )
        downloaded.append(file_rec)
        text = csv_bytes.decode("utf-8", errors="replace")
        effective, rows = parse_bhavcopy_csv(text)
        env = collector_envelope(
            collector_id=COLLECTOR_ID,
            source_id=SOURCE_ID,
            official_source=OFFICIAL,
            payload={
                "effective_date": effective,
                "row_count": len(rows),
                "rows": rows,
                "url": used_url,
            },
            effective_date=effective,
            checksum=file_rec["checksum"],
            mode=mode,
            downloaded_files=downloaded,
            confidence=0.95 if mode == "live" else (0.85 if mode == "injected" else 0.7),
        )
        store.put_raw(SOURCE_ID, "LATEST", env)
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            version=COLLECTOR_ID,
            frequency="daily",
            retry_policy=DEFAULT_RETRY,
            authentication=None,
            last_success=store.utc_now(),
            last_checksum=file_rec["checksum"],
            success_count=(store.get_collector_health(COLLECTOR_ID).get("success_count") or 0) + 1,
            downloaded_files=[file_rec.get("path")],
            metadata={"row_count": len(rows), "mode": mode, "url": used_url},
        )
        return env
    except Exception as exc:  # noqa: BLE001
        fb = fallback_to_snapshot(
            collector_id=COLLECTOR_ID,
            source_id=SOURCE_ID,
            entity="LATEST",
            reason=str(exc)[:200],
        )
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            last_failure=store.utc_now(),
            failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
            last_error=str(exc)[:200],
        )
        if fb:
            return fb
        return {
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
