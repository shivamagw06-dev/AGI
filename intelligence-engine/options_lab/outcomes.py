"""What the market did after a signal.

Separate from the signal for one reason: an outcome must never be able to reach
backwards into the condition that selected it. Kept apart, that is structural
rather than a rule someone has to remember -- a signal row has no forward
column to accidentally filter on.

Every return here is marked to a closing price. Bhavcopy carries no bid or ask,
so nothing has paid a spread, slippage or a fee. That is recorded on the row as
return_basis = 'eod_mark' rather than written in documentation, because the
distinction between a mark and a fill is exactly the one that gets lost when a
backtest is quoted in a meeting.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Optional

OUTCOME_VERSION = "outcomes-1"
TRADING_DAYS = 252
HORIZON = 5


def _pct(later: Optional[float], earlier: Optional[float]) -> Optional[float]:
    if later is None or earlier is None or not earlier:
        return None
    return round((float(later) / float(earlier) - 1.0) * 100.0, 4)


def _forward_realised(spots: list[float]) -> Optional[float]:
    """Annualised volatility of the moves that followed."""
    rets = [math.log(spots[i] / spots[i - 1])
            for i in range(1, len(spots)) if spots[i - 1] > 0]
    if len(rets) < 3:
        return None
    return round(statistics.pstdev(rets) * math.sqrt(TRADING_DAYS) * 100.0, 4)


def build(signal: dict[str, Any],
          future_states: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Attach what followed to one signal.

    `future_states` are the state rows AFTER the signal date, oldest first. A
    horizon that has not elapsed yet produces nulls and a smaller
    horizon_days_available rather than a shorter window silently relabelled --
    the same mistake the twenty-day realised volatility made.
    """
    day = str(signal["observation_date"])
    ahead = [s for s in future_states
             if str(s.get("observation_date")) > day][:HORIZON]
    if not ahead:
        return None

    entry_spot = signal.get("entry_spot")
    entry_iv = signal.get("atm_iv_30d")

    def at(n: int, field: str):
        return ahead[n - 1].get(field) if len(ahead) >= n else None

    spots = [float(entry_spot)] if entry_spot else []
    spots += [float(s["spot"]) for s in ahead if s.get("spot")]

    fwd_rv = _forward_realised(spots) if len(spots) > 3 else None
    return {
        "signal_id": signal["signal_id"],
        "observation_date": day,
        # The option leg is filled by the caller when the signal names a
        # contract. A surface-level signal has no single option to follow, and
        # inventing one would be worse than leaving it null.
        "option_return_1d_pct": None,
        "option_return_2d_pct": None,
        "option_return_5d_pct": None,
        "mfe_5d_pct": None,
        "mae_5d_pct": None,
        "underlying_return_1d_pct": _pct(at(1, "spot"), entry_spot),
        "underlying_return_5d_pct": _pct(at(HORIZON, "spot"), entry_spot),
        # `is not None`, not truthiness. A realised volatility of exactly zero
        # is a real measurement -- a market that did not move -- and treating it
        # as missing silently drops the calmest days, which are precisely the
        # ones where implied volatility looks most expensive.
        "iv_change_1d": (round(float(at(1, "atm_iv_30d")) - float(entry_iv), 4)
                         if at(1, "atm_iv_30d") is not None and entry_iv is not None
                         else None),
        "iv_change_5d": (round(float(at(HORIZON, "atm_iv_30d")) - float(entry_iv), 4)
                         if at(HORIZON, "atm_iv_30d") is not None and entry_iv is not None
                         else None),
        "forward_realised_vol_5d": fwd_rv,
        # The variance risk premium, in the only place it can honestly live:
        # implied at the signal, against what actually followed it.
        "variance_premium_5d": (round(float(entry_iv) - fwd_rv, 4)
                                if entry_iv is not None and fwd_rv is not None
                                else None),
        "horizon_days_available": len(ahead),
        "return_basis": "eod_mark",
        "outcome_version": OUTCOME_VERSION,
    }


def build_many(signals: list[dict[str, Any]],
               states_by_date: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Outcomes for every signal that has enough days after it."""
    ordered = sorted(states_by_date.items())
    out = []
    for sig in signals:
        day = str(sig["observation_date"])
        ahead = [s for d, s in ordered if d > day]
        built = build(sig, ahead)
        if built:
            out.append(built)
    return out
