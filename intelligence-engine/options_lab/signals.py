"""Claims made on a date, from what was knowable on it.

A signal here is not a recommendation. It is a measurement plus the conditions
it was taken in, stored so that what followed can be attached to it later and
the pair queried. Whether any of these carry information is the question the
warehouse exists to answer, not something this module asserts.

Three families, chosen because they are the ones this data can actually test:

  VRP     implied volatility against its own recent history
  SKEW    the risk reversal against its own recent history
  FLOW    open interest and price moving together, or not

Each is standardised against its own past rather than an absolute threshold. A
risk reversal of -1.5 means nothing on its own; -1.5 when the last sixty days
sat near -0.6 is a different statement, and only the second is comparable
across regimes.

Nothing here may read a date after the signal date. That is enforced by
construction -- the history passed in is truncated by the caller -- and
asserted in the tests, because it is the one error that turns a research
warehouse into a machine for finding edges that never existed.
"""

from __future__ import annotations

import hashlib
import math
import statistics
from typing import Any, Optional

SIGNAL_VERSION = "signals-1"

# Enough history to standardise against. Below this the z-score is null rather
# than a number computed from a handful of days, which is the same mistake the
# realised-volatility window made.
MIN_HISTORY = 20
# Long enough to span a regime, short enough to still be about now.
LOOKBACK = 60


def signal_id(family: str, day: str, underlying: str,
              detail: str = "") -> str:
    """Stable across rebuilds, so recomputing a signal updates its row.

    A random id would multiply rows every time a definition improved, and the
    outcome attached to the old row would quietly describe a different claim.
    """
    raw = f"{family}|{day}|{underlying}|{detail}|{SIGNAL_VERSION}"
    return hashlib.sha1(raw.encode()).hexdigest()[:24]


def _zscore(value: Optional[float],
            history: list[float]) -> tuple[Optional[float], int]:
    """How unusual a value is against its own past, and how much past there was."""
    clean = [h for h in history if h is not None and math.isfinite(h)]
    if value is None or len(clean) < MIN_HISTORY:
        return None, len(clean)
    window = clean[-LOOKBACK:]
    spread = statistics.pstdev(window)
    if spread <= 1e-9:
        # A constant history cannot say anything is unusual. Dividing by it
        # would report infinity as a discovery.
        return None, len(window)
    return round((value - statistics.mean(window)) / spread, 4), len(window)


def _base(family: str, name: str, state: dict[str, Any],
          value: Optional[float], history: list[float],
          detail: str = "") -> dict[str, Any]:
    day = str(state["observation_date"])
    underlying = str(state["underlying_symbol"])
    z, n = _zscore(value, history)
    flags = []
    if (state.get("skew_agreement") or 1.0) < 0.7:
        flags.append("expiries_disagree_on_skew")
    if (state.get("state_quality") or "low") != "high":
        flags.append(f"state_{state.get('state_quality')}")
    if z is None:
        flags.append("no_zscore")
    return {
        "signal_id": signal_id(family, day, underlying, detail),
        "observation_date": day,
        "underlying_symbol": underlying,
        "signal_family": family,
        "signal_name": name,
        "signal_value": round(value, 6) if value is not None else None,
        "signal_zscore": z,
        "history_days": n,
        "atm_iv_30d": state.get("atm_iv_30d"),
        "realised_vol_20d": state.get("realised_vol_20d"),
        "risk_reversal_30d": state.get("risk_reversal_30d"),
        "skew_agreement": state.get("skew_agreement"),
        "oi_pcr": state.get("oi_pcr"),
        "entry_spot": state.get("spot"),
        "quality_flags": flags,
        "signal_version": SIGNAL_VERSION,
    }


def build_for_day(state: dict[str, Any],
                  history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every signal measurable on one day.

    `history` is the state rows strictly BEFORE this day, oldest first. The
    caller truncates it; nothing here reaches forward.
    """
    if not state:
        return []
    prior = [h for h in history
             if str(h.get("observation_date")) < str(state["observation_date"])]
    out: list[dict[str, Any]] = []

    # VRP -- is implied volatility rich or cheap against its own recent past?
    # Deliberately not implied minus forward realised: that is the outcome.
    iv = state.get("atm_iv_30d")
    if iv is not None:
        out.append(_base("VRP", "atm_iv_30d_z", state, float(iv),
                         [h.get("atm_iv_30d") for h in prior]))

    # The same level measured against trailing realised, which is knowable.
    spread = state.get("iv_minus_trailing_rv")
    if spread is not None:
        out.append(_base("VRP", "iv_minus_trailing_rv_z", state, float(spread),
                         [h.get("iv_minus_trailing_rv") for h in prior],
                         detail="spread"))

    # SKEW -- is the risk reversal unusual for this market?
    rr = state.get("risk_reversal_30d")
    if rr is not None:
        out.append(_base("SKEW", "risk_reversal_30d_z", state, float(rr),
                         [h.get("risk_reversal_30d") for h in prior]))

    # FLOW -- positioning. The put-call ratio's level says less than its change,
    # so both are recorded and the study can decide which, if either, matters.
    pcr = state.get("oi_pcr")
    if pcr is not None:
        out.append(_base("FLOW", "oi_pcr_z", state, float(pcr),
                         [h.get("oi_pcr") for h in prior]))
        if prior and prior[-1].get("oi_pcr"):
            change = float(pcr) - float(prior[-1]["oi_pcr"])
            hist = [
                (float(b["oi_pcr"]) - float(a["oi_pcr"]))
                for a, b in zip(prior, prior[1:])
                if a.get("oi_pcr") and b.get("oi_pcr")
            ]
            out.append(_base("FLOW", "oi_pcr_change_z", state, change, hist,
                             detail="change"))

    # REGIME -- how far spot sits from max pain. Recorded because it is widely
    # believed rather than because it is believed here; 59 days put it 1.4
    # standard errors from a coin flip, which is what a study should confirm or
    # overturn with more.
    gap = state.get("spot_to_max_pain_pct")
    if gap is not None:
        out.append(_base("REGIME", "spot_to_max_pain_z", state, float(gap),
                         [h.get("spot_to_max_pain_pct") for h in prior]))

    return out


def build_range(start: str, end: str, *, underlying: str = "NIFTY",
                dry_run: bool = True) -> dict[str, Any]:
    """Signals and their outcomes over a range of stored days.

    Built together because they are two halves of one record, and written to
    separate tables because an outcome must never be reachable from the
    condition that selected it.

    The whole range is read once. Signals need history behind each day and
    outcomes need days ahead of it, so walking day by day would re-read the
    same rows for every day in the range.
    """
    from . import canonical_store, outcomes

    try:
        # Reach back far enough to standardise the first day in the range.
        from datetime import date as _date
        lookback_start = _date.fromordinal(
            _date.fromisoformat(start).toordinal() - LOOKBACK * 2).isoformat()
        rows = canonical_store.states_between(lookback_start, end, underlying)
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "read", "error": str(exc)[:250]}
    if not rows:
        return {"ok": False, "stage": "read", "error": "no market state stored"}

    by_date = {str(r["observation_date"]): r for r in rows}
    ordered = sorted(by_date)
    in_range = [d for d in ordered if start <= d <= end]

    built: list[dict[str, Any]] = []
    for day in in_range:
        prior = [by_date[d] for d in ordered if d < day]
        built.extend(build_for_day(by_date[day], prior))
    if not built:
        return {"ok": False, "stage": "build", "days": len(in_range),
                "error": "no signals measurable in that range"}

    resolved = outcomes.build_many(built, by_date)

    families: dict[str, int] = {}
    for s in built:
        families[s["signal_family"]] = families.get(s["signal_family"], 0) + 1
    with_z = sum(1 for s in built if s["signal_zscore"] is not None)

    try:
        # Clear the range first. Upserting alone leaves behind any signal the
        # previous definition produced and this one does not, and a study then
        # reads two definitions as though they were one.
        removed = 0
        if not dry_run:
            removed = canonical_store.delete_signals_in_range(start, end, underlying)
        wrote_signals = canonical_store.upsert_signals(built, dry_run=dry_run)
        wrote_outcomes = canonical_store.upsert_outcomes(resolved, dry_run=dry_run)
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "write", "signals": len(built),
                "error": str(exc)[:250]}
    return {"ok": True, "stage": "complete", "days": len(in_range),
            "signals": len(built), "with_zscore": with_z,
            "families": families, "outcomes": len(resolved),
            "replaced": removed,
            "write": {"signals": wrote_signals, "outcomes": wrote_outcomes}}
