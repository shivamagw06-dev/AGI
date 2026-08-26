"""Asking the warehouse whether a condition preceded anything.

A study here joins signals to their outcomes, splits them by the signal's own
z-score, and reports what followed each bucket. It does not decide whether a
result is tradeable. It reports n, the spread, and how far the difference sits
from noise, and leaves the judgement where it belongs.

Three deliberate refusals.

No p-value. With fifty-nine days and a handful of buckets, the number of
implicit comparisons is large and unrecorded, and a p-value under those
conditions is a decoration. A difference in standard errors is the same
information without the false precision.

No result is called significant. The module returns the numbers and the sample
size beside each other; "n=6" next to a large mean is a complete answer.

No study reads a price. Every return it aggregates was marked to a close by the
outcome table, and carries return_basis saying so. A study that quietly dropped
that label would be reporting alpha it never measured.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Optional

STUDY_VERSION = "studies-1"

# Below this a bucket is reported but should not be read as anything.
THIN_BUCKET = 10


def _stats(values: list[float]) -> dict[str, Any]:
    clean = [v for v in values if v is not None and math.isfinite(v)]
    if not clean:
        return {"n": 0}
    out = {
        "n": len(clean),
        "mean": round(statistics.mean(clean), 4),
        "median": round(statistics.median(clean), 4),
        "positive_share": round(sum(1 for v in clean if v > 0) / len(clean), 4),
    }
    if len(clean) > 1:
        sd = statistics.pstdev(clean)
        out["sd"] = round(sd, 4)
        # How far the mean sits from zero, in standard errors. Not a p-value:
        # with this many implicit comparisons on fifty-nine days, a p-value
        # would be decoration.
        out["standard_errors"] = (round(out["mean"] / (sd / math.sqrt(len(clean))), 2)
                                  if sd > 0 else None)
    if len(clean) < THIN_BUCKET:
        out["warning"] = f"only {len(clean)} observations"
    return out


def _bucket(z: Optional[float]) -> str:
    if z is None:
        return "no_zscore"
    if z <= -2:
        return "z <= -2"
    if z <= -1:
        return "-2 to -1"
    if z < 1:
        return "-1 to +1"
    if z < 2:
        return "+1 to +2"
    return "z >= +2"


def run(rows: list[dict[str, Any]], *, family: str,
        outcome_field: str,
        require_agreement: bool = False) -> dict[str, Any]:
    """One study: split a family by z-score, report what followed each bucket.

    `rows` are joined signal+outcome records. Filtering happens here rather
    than in the query so a study states its own conditions in its own result.
    """
    picked = [r for r in rows if r.get("signal_family") == family]
    excluded_low_agreement = 0
    if require_agreement:
        before = len(picked)
        picked = [r for r in picked
                  if (r.get("skew_agreement") is None
                      or float(r["skew_agreement"]) >= 0.7)]
        excluded_low_agreement = before - len(picked)

    buckets: dict[str, list[float]] = {}
    for r in picked:
        value = r.get(outcome_field)
        if value is None:
            continue
        buckets.setdefault(_bucket(r.get("signal_zscore")), []).append(float(value))

    order = ["z <= -2", "-2 to -1", "-1 to +1", "+1 to +2", "z >= +2", "no_zscore"]
    result = {
        "family": family,
        "outcome": outcome_field,
        "signals": len(picked),
        "buckets": {b: _stats(buckets[b]) for b in order if b in buckets},
        "return_basis": (picked[0].get("return_basis") if picked else None),
        "study_version": STUDY_VERSION,
    }
    if require_agreement:
        result["excluded_for_low_skew_agreement"] = excluded_low_agreement

    # The comparison the study exists to make: do the tails differ from the
    # middle, and by how much relative to their own spread.
    low, high = buckets.get("z <= -2"), buckets.get("z >= +2")
    middle = buckets.get("-1 to +1")
    if middle and (low or high):
        result["tails_vs_middle"] = {
            side: _difference(tail, middle)
            for side, tail in (("cheap", low), ("rich", high)) if tail
        }
    return result


def _difference(tail: list[float], middle: list[float]) -> dict[str, Any]:
    if len(tail) < 2 or len(middle) < 2:
        return {"n_tail": len(tail), "note": "too few to compare"}
    diff = statistics.mean(tail) - statistics.mean(middle)
    pooled = math.sqrt(statistics.pvariance(tail) / len(tail)
                       + statistics.pvariance(middle) / len(middle))
    return {
        "n_tail": len(tail),
        "n_middle": len(middle),
        "difference": round(diff, 4),
        "standard_errors": round(diff / pooled, 2) if pooled > 0 else None,
        "reading": ("indistinguishable from noise" if pooled <= 0
                    or abs(diff / pooled) < 2 else "worth a larger sample"),
    }


def run_all(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The three studies worth running first on this data."""
    return {
        "iv_vs_realised": run(rows, family="VRP",
                              outcome_field="variance_premium_5d"),
        "skew_mean_reversion": run(rows, family="SKEW",
                                   outcome_field="underlying_return_5d_pct",
                                   require_agreement=True),
        "positioning": run(rows, family="FLOW",
                           outcome_field="underlying_return_5d_pct"),
        "note": ("Every return is an end-of-day mark. No spread, slippage or "
                 "fee has been paid, because the source carries no bid or ask. "
                 "These are not tradeable returns."),
        "study_version": STUDY_VERSION,
    }
