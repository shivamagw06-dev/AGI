"""RBI DBIE / key-rates macro collector — structured series with incremental history."""

from __future__ import annotations

import json
import re
import ssl
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.request import HTTPSHandler, Request, build_opener

from live_data import store
from live_data.collectors.base import collector_envelope, fallback_to_snapshot, run_with_retry
from live_data.qa import qa_macro_series
from live_data.schema import DEFAULT_RETRY

COLLECTOR_ID = "lidi_rbi_dbie_v1"
SOURCE_ID = "rbi_dbie"
OFFICIAL = "Reserve Bank of India DBIE"
SAMPLES = Path(__file__).resolve().parents[1] / "samples"

# Prefer pages that publish numeric policy / macro figures.
DBIE_URLS = (
    "https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx?param=4",
    "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx",
    "https://www.rbi.org.in/",
    "https://dbie.rbi.org.in/DBIE/#/dbie/home",
    # Open data / SDMX-ish probes (may 404; skipped gracefully)
    "https://data.rbi.org.in/DBIE/#/dbie/home",
)

# Metric aliases found in RBI HTML copy.
METRIC_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("repo_rate", re.compile(r"Repo\s*Rate[:\s]+([0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("reverse_repo_rate", re.compile(r"Reverse\s*Repo\s*Rate[:\s]+([0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("crr", re.compile(r"\bCRR\b[:\s]+([0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("slr", re.compile(r"\bSLR\b[:\s]+([0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("cpi", re.compile(r"\bCPI\b[^0-9]{0,40}?([0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("wpi", re.compile(r"\bWPI\b[^0-9]{0,40}?([0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("iip", re.compile(r"\bIIP\b[^0-9]{0,40}?([-+]?[0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("gdp", re.compile(r"\bGDP\b[^0-9]{0,40}?([-+]?[0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("fx_reserves_usd_bn", re.compile(r"(?:Forex|Foreign\s*Exchange)\s*Reserves[^0-9]{0,40}?([0-9]+(?:\.[0-9]+)?)", re.I), "usd_bn"),
    ("gsec_10y_yield", re.compile(r"(?:10[- ]Year|10Y).*?(?:G[- ]?Sec|Government).*?([0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("bank_credit_growth_yoy", re.compile(r"(?:Bank\s*)?Credit\s*Growth[^0-9]{0,30}?([-+]?[0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
    ("aggregate_deposits_growth_yoy", re.compile(r"Deposit(?:s)?\s*Growth[^0-9]{0,30}?([-+]?[0-9]+(?:\.[0-9]+)?)\s*%?", re.I), "percent"),
]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data and data.strip():
            self.parts.append(data.strip())


def collect_rbi_dbie(
    *,
    injected_json: dict[str, Any] | str | None = None,
    allow_recorded_sample: bool = False,
) -> dict[str, Any]:
    mode = "live"
    payload_obj = None
    raw = None
    url_used = None
    parse_path = "json"
    try:
        if injected_json is not None:
            mode = "injected"
            if isinstance(injected_json, str):
                payload_obj = json.loads(injected_json)
                raw = injected_json.encode("utf-8")
            else:
                payload_obj = injected_json
                raw = json.dumps(injected_json).encode("utf-8")
        else:

            def _fetch() -> tuple[bytes, str]:
                nonlocal url_used
                last = None
                ctx_default = ssl.create_default_context()
                for url in DBIE_URLS:
                    for ctx in (ctx_default, ssl._create_unverified_context()):  # noqa: S323
                        try:
                            opener = build_opener(HTTPSHandler(context=ctx))
                            req = Request(
                                url,
                                headers={
                                    "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)",
                                    "Accept": "text/html,application/json,*/*",
                                },
                            )
                            with opener.open(req, timeout=30) as resp:
                                data = resp.read()
                            if not data:
                                raise RuntimeError("empty_body")
                            url_used = url
                            return data, url
                        except Exception as exc:  # noqa: BLE001
                            last = exc
                raise RuntimeError(f"rbi_dbie_fetch_failed:{last}")

            try:
                policy = {"max_attempts": 1, "backoff_seconds": [0]} if allow_recorded_sample else DEFAULT_RETRY
                raw, url_used = run_with_retry(_fetch, retry_policy=policy)
                payload_obj, parse_path = _parse_rbi_payload(raw)
                if not (payload_obj.get("series") or []):
                    raise RuntimeError("rbi_dbie_no_structured_series_export")
            except Exception as live_exc:
                if allow_recorded_sample:
                    sample = SAMPLES / "rbi_dbie_key_rates.json"
                    mode = "recorded_sample"
                    raw = sample.read_bytes()
                    payload_obj = json.loads(raw.decode("utf-8"))
                    url_used = str(sample)
                    parse_path = "recorded_sample"
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
                        frequency="daily_to_weekly",
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

        assert payload_obj is not None and raw is not None
        series = list(payload_obj.get("series") or [])
        for s in series:
            if s.get("value") is None and s.get("metric") == "liquidity_stance":
                s["value"] = "UNKNOWN"
        # Ensure liquidity placeholder exists
        if not any(s.get("metric") == "liquidity_stance" for s in series):
            series.append(
                {
                    "metric": "liquidity_stance",
                    "value": "UNKNOWN",
                    "unit": "qualitative",
                    "as_of": payload_obj.get("effective_date") or store.utc_now()[:10],
                    "note": "UNKNOWN if not published",
                }
            )
        effective = payload_obj.get("effective_date") or _infer_effective(series)
        history = _merge_series_history(series, effective=effective)
        qa = qa_macro_series(series)

        out_payload = {
            "effective_date": effective,
            "series": series,
            "history": history,
            "history_points": len(history),
            "url": url_used,
            "parse_path": parse_path,
            "qa": qa,
        }
        raw_out = json.dumps(out_payload, default=str).encode("utf-8")
        file_rec = store.put_raw_file(SOURCE_ID, "rbi_dbie.json", raw_out, meta={"mode": mode, "url": url_used})
        env = collector_envelope(
            collector_id=COLLECTOR_ID,
            source_id=SOURCE_ID,
            official_source=OFFICIAL,
            payload=out_payload,
            effective_date=effective,
            checksum=file_rec["checksum"],
            mode=mode,
            downloaded_files=[file_rec],
            confidence=0.9 if mode == "live" else 0.75,
        )
        store.put_raw(SOURCE_ID, "LATEST", env)
        store.put_object(SOURCE_ID, "HISTORY", {"series_history": history, "updated_at": store.utc_now(), "qa": qa})
        # Bridge into KF HD macro store when available
        _bridge_hd_macro(history)
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            version=COLLECTOR_ID,
            frequency="daily_to_weekly",
            retry_policy=DEFAULT_RETRY,
            last_success=store.utc_now(),
            last_checksum=file_rec["checksum"],
            success_count=(store.get_collector_health(COLLECTOR_ID).get("success_count") or 0) + 1,
            downloaded_files=[file_rec.get("path")],
            metadata={"series_count": len(series), "history_points": len(history), "mode": mode, "parse_path": parse_path},
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


def _parse_rbi_payload(raw: bytes) -> tuple[dict[str, Any], str]:
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict) and obj.get("series"):
                return obj, "json"
            if isinstance(obj, list):
                series = []
                for row in obj:
                    if isinstance(row, dict) and row.get("metric"):
                        series.append(row)
                if series:
                    return {"effective_date": _infer_effective(series), "series": series}, "json_list"
        except Exception:
            pass
    series = _extract_series_from_html(text)
    return {
        "effective_date": store.utc_now()[:10],
        "series": series,
    }, "html_extract"


def _extract_series_from_html(html: str) -> list[dict[str, Any]]:
    # Collapse tags to text
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
        blob = " ".join(extractor.parts)
    except Exception:
        blob = re.sub(r"<[^>]+>", " ", html)
    blob = re.sub(r"\s+", " ", blob)
    as_of = store.utc_now()[:10]
    # Try to find a date near "as on"
    m_date = re.search(r"as\s+on\s+([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})", blob, re.I)
    if m_date:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                as_of = datetime.strptime(m_date.group(1), fmt).date().isoformat()
                break
            except Exception:
                continue
    series: list[dict[str, Any]] = []
    seen: set[str] = set()
    for metric, pat, unit in METRIC_PATTERNS:
        m = pat.search(blob)
        if not m:
            continue
        try:
            val: Any = float(m.group(1))
        except Exception:
            continue
        if metric in seen:
            continue
        seen.add(metric)
        series.append({"metric": metric, "value": val, "unit": unit, "as_of": as_of, "source": "rbi_html"})
    return series


def _infer_effective(series: list[dict[str, Any]]) -> str | None:
    dates = [str(s.get("as_of")) for s in series if s.get("as_of")]
    return max(dates) if dates else store.utc_now()[:10]


def _merge_series_history(series: list[dict[str, Any]], *, effective: str | None) -> list[dict[str, Any]]:
    prev = store.get_object(SOURCE_ID, "HISTORY") or {}
    hist = list(prev.get("series_history") or [])
    by_key: dict[str, dict[str, Any]] = {}
    for row in hist:
        key = f"{row.get('metric')}|{row.get('as_of')}"
        by_key[key] = row
    for s in series:
        as_of = s.get("as_of") or effective
        key = f"{s.get('metric')}|{as_of}"
        by_key.setdefault(
            key,
            {
                "metric": s.get("metric"),
                "value": s.get("value"),
                "unit": s.get("unit"),
                "as_of": as_of,
                "source": s.get("source") or SOURCE_ID,
            },
        )
    return sorted(by_key.values(), key=lambda x: (str(x.get("metric") or ""), str(x.get("as_of") or "")))


def _bridge_hd_macro(history: list[dict[str, Any]]) -> None:
    """Best-effort: append RBI points into KF Historical Depth macro store."""
    try:
        from knowledge_factory.historical_depth import store as hd_store

        # Collapse to period buckets by as_of month
        by_period: dict[str, dict[str, Any]] = {}
        for row in history:
            as_of = str(row.get("as_of") or "")[:10]
            if len(as_of) < 7:
                continue
            period = as_of[:7]  # YYYY-MM
            bucket = by_period.setdefault(period, {"period": period, "payload": {}, "source": "rbi_dbie"})
            metric = str(row.get("metric") or "")
            if metric and row.get("value") is not None:
                bucket["payload"][metric] = row.get("value")
        records = []
        for period, bucket in sorted(by_period.items()):
            records.append(
                {
                    "period": period,
                    "period_end": f"{period}-28",
                    "available_from": f"{period}-28",
                    "payload": bucket["payload"],
                    "source": "rbi_dbie",
                }
            )
        if records:
            hd_store.put_macro_history(records)
    except Exception:
        return
