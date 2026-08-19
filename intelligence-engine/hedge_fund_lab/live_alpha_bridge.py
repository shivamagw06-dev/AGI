"""Bridge Hedge Fund Lab to the Live Alpha research store.

Reads Leadership, Activity, Breakout, Dislocation and Positioning engines,
filters stale / illiquid / low-quality signals, and aggregates per symbol for
the ninth Hedge Fund scanner and confluence labelling.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, time, timezone
from typing import Any, Optional
from urllib import error, parse, request
from zoneinfo import ZoneInfo

ENGINE_LABELS: dict[str, str] = {
    "cross_sectional_momentum_v1": "Leadership",
    "volume_liquidity_anomaly_v1": "Activity",
    "opening_range_expansion_v1": "Breakout",
    "intraday_mean_reversion_v1": "Dislocation",
    "derivatives_positioning_v1": "Positioning",
}

_ENGINE_ORDER = list(ENGINE_LABELS.keys())
IST = ZoneInfo("Asia/Kolkata")

_MIN_QUALITY = float(os.getenv("HFL_LIVE_ALPHA_MIN_QUALITY", "50"))
_FRESHNESS_MODE = (os.getenv("HFL_LIVE_ALPHA_FRESHNESS_MODE") or "session").strip().lower()
_MAX_AGE_MINUTES_RAW = (os.getenv("HFL_LIVE_ALPHA_MAX_AGE_MINUTES") or "").strip()
_MAX_AGE_MINUTES = float(_MAX_AGE_MINUTES_RAW) if _MAX_AGE_MINUTES_RAW else None
_WEAK_LABELS = frozenset({"ignore", "weak"})


def _credentials() -> Optional[tuple[str, str]]:
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    return url, key


def _rest(path: str, *, timeout_seconds: float = 10.0) -> Any:
    creds = _credentials()
    if not creds:
        return None
    url, key = creds
    req = request.Request(
        f"{url}/rest/v1/{path}",
        method="GET",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except error.HTTPError:
        return None
    except Exception:
        return None


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _age_minutes(ts: Optional[datetime]) -> Optional[float]:
    if ts is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 60.0)


def _next_nse_session_open(after: datetime) -> datetime:
    """Next NSE cash session open (Mon–Fri 09:15 IST) strictly after `after`."""
    local = after.astimezone(IST)
    day = local.date()
    while True:
        if day.weekday() < 5:
            candidate = datetime.combine(day, time(9, 15), tzinfo=IST)
            if candidate > local:
                return candidate.astimezone(timezone.utc)
        day += timedelta(days=1)


def _signal_is_fresh(signal: dict[str, Any], *, as_of: Optional[datetime]) -> bool:
    """Session-aware freshness: closing signals stay until the next NSE open."""
    created = _parse_ts(signal.get("created_at") or signal.get("as_of"))
    ref = created or as_of
    if ref is None:
        return False
    now = datetime.now(timezone.utc)
    if _FRESHNESS_MODE == "minutes":
        cap = _MAX_AGE_MINUTES if _MAX_AGE_MINUTES is not None else 720.0
        age = _age_minutes(ref)
        return age is not None and age <= cap
    if _FRESHNESS_MODE == "hours":
        cap_hours = (_MAX_AGE_MINUTES / 60.0) if _MAX_AGE_MINUTES is not None else 12.0
        return (now - ref).total_seconds() <= cap_hours * 3600
    return now < _next_nse_session_open(ref)


def signed_score(signal: dict[str, Any]) -> float:
    direction = signal.get("direction")
    if not direction:
        return 0.0
    alpha_z = float(signal.get("alpha_z") or 0.0)
    quality = float(signal.get("signal_quality_score") or 0.0)
    magnitude = min(99.0, round(abs(alpha_z) * 28.0 + quality * 0.35))
    return -magnitude if direction == "negative" else magnitude


def _signal_passes_filters(signal: dict[str, Any], *, as_of: Optional[datetime]) -> bool:
    if not signal.get("liquidity_ok"):
        return False
    if signal.get("direction") not in ("positive", "negative"):
        return False
    label = str(signal.get("signal_quality_label") or "").lower()
    if label in _WEAK_LABELS:
        return False
    quality = float(signal.get("signal_quality_score") or 0.0)
    if quality < _MIN_QUALITY:
        return False
    classification = str(signal.get("classification") or "").lower()
    if classification in {"filtered", "neutral"}:
        return False
    if not _signal_is_fresh(signal, as_of=as_of):
        return False
    return True


def engine_agreement(active: list[dict[str, Any]]) -> str:
    """Classify Live Alpha engine agreement as positive, negative or mixed."""
    if len(active) < 2:
        return "single"
    positives = sum(1 for s in active if s.get("direction") == "positive")
    negatives = len(active) - positives
    if positives > 0 and negatives > 0:
        return "mixed"
    direction = "positive" if positives >= negatives else "negative"
    scores = [signed_score(s) for s in active]
    same_sign = all(s > 0 for s in scores) or all(s < 0 for s in scores)
    if not same_sign:
        return "mixed"
    return direction


def composite_score(active: list[dict[str, Any]]) -> float:
    scores = [signed_score(s) for s in active if s.get("direction")]
    if not scores:
        return 0.0
    composite = round(sum(scores) / math.sqrt(len(scores)))
    return float(max(-99, min(99, composite)))


def fetch_live_alpha_rows(*, limit: int = 200) -> dict[str, Any]:
    """Load qualifying Live Alpha symbols from Supabase."""
    runs = _rest(
        "live_alpha_runs"
        "?select=id,engine,as_of"
        "&order=as_of.desc"
        "&limit=25"
    )
    if not isinstance(runs, list) or not runs:
        return {"ok": False, "error": "live_alpha_unavailable", "rows": [], "meta": {}}

    run_ids = [r["id"] for r in runs if r.get("id")]
    if not run_ids:
        return {"ok": False, "error": "live_alpha_unavailable", "rows": [], "meta": {}}

    in_clause = ",".join(parse.quote(str(rid)) for rid in run_ids)
    signals = _rest(
        "live_alpha_signals"
        f"?select=symbol,sector,run_id,direction,alpha_z,signal_quality_score,"
        f"signal_quality_label,liquidity_ok,classification,factor_values,created_at"
        f"&run_id=in.({in_clause})"
        f"&order=created_at.desc"
        f"&limit=500"
    )
    if signals is None:
        return {"ok": False, "error": "live_alpha_unavailable", "rows": [], "meta": {}}

    run_by_id = {r["id"]: r for r in runs}
    seen_keys: set[str] = set()
    latest_by_key: dict[str, dict[str, Any]] = {}
    for sig in signals or []:
        if not isinstance(sig, dict):
            continue
        run = run_by_id.get(sig.get("run_id")) or {}
        engine = run.get("engine")
        if engine not in ENGINE_LABELS:
            continue
        symbol = str(sig.get("symbol") or "").upper()
        if not symbol:
            continue
        key = f"{symbol}|{engine}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        sig = {**sig, "engine": engine, "as_of": run.get("as_of")}
        if not _signal_passes_filters(sig, as_of=_parse_ts(run.get("as_of"))):
            continue
        latest_by_key[key] = sig

    by_symbol: dict[str, dict[str, Any]] = {}
    for sig in latest_by_key.values():
        symbol = str(sig.get("symbol") or "").upper()
        row = by_symbol.setdefault(
            symbol,
            {
                "ticker": symbol,
                "symbol": symbol,
                "sector": sig.get("sector"),
                "engines": {},
                "newest": sig.get("as_of") or sig.get("created_at"),
            },
        )
        row["engines"][sig["engine"]] = sig
        ts = _parse_ts(sig.get("as_of") or sig.get("created_at"))
        newest = _parse_ts(row.get("newest"))
        if ts and (newest is None or ts > newest):
            row["newest"] = sig.get("as_of") or sig.get("created_at")

    rows: list[dict[str, Any]] = []
    for symbol, row in by_symbol.items():
        active = [s for s in row["engines"].values() if s.get("direction")]
        if not active:
            continue
        comp = composite_score(active)
        agreement = engine_agreement(active)
        age_min = _age_minutes(_parse_ts(row.get("newest")))
        contributing = [ENGINE_LABELS[e] for e in _ENGINE_ORDER if e in row["engines"]]
        direction = "positive" if comp >= 0 else "negative"
        rows.append(
            {
                "ticker": symbol,
                "company_name": symbol,
                "sector": row.get("sector"),
                "direction": direction,
                "live_alpha_score": abs(comp),
                "live_alpha_signed": comp,
                "engine_agreement": agreement,
                "contributing_engines": contributing,
                "engine_count": len(active),
                # Raw per-engine signals, keyed by engine id. The aggregate
                # fields above collapse these into one confluence flag, which
                # is all the confluence scanner needs; per-engine strategies
                # need the underlying signal (alpha_z, quality, factor_values).
                "engines": dict(row["engines"]),
                "signal_age_minutes": round(age_min) if age_min is not None else None,
                "newest_signal_at": row.get("newest"),
                "why": (
                    f"{len(active)} Live Alpha engine{'s' if len(active) != 1 else ''} "
                    f"({', '.join(contributing)}) show {direction} intraday evidence"
                    + (f" with {agreement} agreement" if agreement not in {"single", direction} else "")
                    + ". Tactical research only — validate against fundamentals before acting."
                ),
            }
        )

    rows.sort(key=lambda r: (-(r.get("live_alpha_score") or 0), r.get("ticker") or ""))
    capped = rows[: max(1, min(int(limit or 200), 500))]
    return {
        "ok": True,
        "rows": capped,
        "meta": {
            "source": "live_alpha_signals",
            "engines": ENGINE_LABELS,
            "qualifying_symbols": len(rows),
            "freshness_mode": _FRESHNESS_MODE,
            "max_age_minutes": _MAX_AGE_MINUTES,
            "min_quality": _MIN_QUALITY,
        },
    }


def fundamental_bias(fund_avg: Optional[float]) -> Optional[str]:
    if fund_avg is None:
        return None
    if fund_avg >= 55:
        return "positive"
    if fund_avg <= 45:
        return "negative"
    return None


def live_alpha_confirms(*, hfl_bias: Optional[str], live_direction: Optional[str]) -> bool:
    return bool(hfl_bias and live_direction and hfl_bias == live_direction)


def live_alpha_conflicts(*, hfl_bias: Optional[str], live_direction: Optional[str]) -> bool:
    return bool(hfl_bias and live_direction and hfl_bias != live_direction)


def effective_agreement(*, fundamental_count: int, live_alpha_confirms: bool) -> int:
    """Only positive Live Alpha confirmation adds to scanner agreement."""
    return int(fundamental_count) + (1 if live_alpha_confirms else 0)


def confluence_label(
    *,
    hfl_scanner_count: int,
    live_alpha_present: bool,
    live_direction: Optional[str],
    hfl_bias: Optional[str],
) -> str:
    """Label cross-desk agreement for the Hedge Fund interface."""
    has_fundamental = hfl_scanner_count > 0
    has_tactical = live_alpha_present

    if has_fundamental and has_tactical:
        if live_direction and hfl_bias and live_direction != hfl_bias:
            return "Timing conflict"
        if live_direction and hfl_bias and live_direction == hfl_bias:
            return "Confirmed"
        return "Live unconfirmed"
    if has_fundamental:
        return "Fundamental only"
    if has_tactical:
        return "Tactical only"
    return "Unclassified"


def unified_score(
    *,
    hfl_score: float,
    live_alpha_score: float,
    live_direction: Optional[str],
    hfl_bias: Optional[str],
) -> float:
    """70% Hedge Fund evidence, 30% Live Alpha; penalize directional conflicts."""
    hfl = max(0.0, min(100.0, float(hfl_score or 0.0)))
    la = max(0.0, min(99.0, abs(float(live_alpha_score or 0.0))))
    base = 0.7 * hfl + 0.3 * la
    if live_direction and hfl_bias and live_direction != hfl_bias:
        penalty = min(35.0, 0.25 * la + 10.0)
        return round(max(0.0, base - penalty), 1)
    return round(base, 1)
