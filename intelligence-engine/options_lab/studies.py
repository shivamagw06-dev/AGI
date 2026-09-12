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


# A conditional study asks a second question of the same rows, and every extra
# question is a fresh chance to find something that is not there. With c cells
# examined, roughly 4.6% of them clear two standard errors by chance alone --
# so at twelve cells you expect one, and finding one proves nothing. The count
# travels with the result rather than living in someone's memory.
NOISE_RATE_AT_2SE = 0.0455


def _cuts(values: list[float], n: int) -> list[float]:
    """Boundaries splitting a sample into n roughly equal groups.

    Duplicates are collapsed. A variable with fewer distinct values than groups
    -- a regime flag, or a thin sample -- produces repeated boundaries, and a
    boundary equal to its neighbour creates a group nothing can land in. Fewer,
    honest groups beat three groups where one is always empty.
    """
    clean = sorted(v for v in values if v is not None and math.isfinite(v))
    if len(clean) < n * 2:
        return []
    raw = [clean[int(len(clean) * i / n)] for i in range(1, n)]
    out: list[float] = []
    for c in raw:
        if not out or c > out[-1]:
            out.append(c)
    return out


def _label(value: Optional[float], cuts: list[float], name: str) -> str:
    """Which group a value falls in.

    The lower edge is inclusive. With ties at a boundary -- common when a
    condition takes few distinct values -- a strict comparison sends every tied
    observation upward and leaves the bottom group empty.
    """
    if value is None:
        return f"{name}: unknown"
    names = (["low", "high"] if len(cuts) == 1 else
             ["low", "mid", "high"] if len(cuts) == 2 else
             [f"q{i + 1}" for i in range(len(cuts) + 1)])
    for i, c in enumerate(cuts):
        if value <= c:
            return f"{name}: {names[i]}"
    return f"{name}: {names[-1]}"


def conditional(rows: list[dict[str, Any]], *, family: str,
                outcome_field: str, condition: str,
                groups: int = 3) -> dict[str, Any]:
    """What followed a family's signals, split by a second observed variable.

    The unconditional study asks whether a signal preceded anything on average.
    This asks whether it preceded something different in different conditions --
    which is the question a strategy actually depends on, and also the question
    that makes it easy to find an edge that is not there.

    So the result reports how many cells were examined and how many of them
    would be expected to clear two standard errors by chance. A cell that beats
    that expectation is interesting; one that merely reaches it is arithmetic.
    """
    picked = [r for r in rows
              if r.get("signal_family") == family
              and r.get(outcome_field) is not None]
    cuts = _cuts([r.get(condition) for r in picked], groups)
    if not cuts:
        return {"family": family, "condition": condition,
                "error": f"too few observations to split on {condition}",
                "signals": len(picked)}

    cells: dict[str, list[float]] = {}
    for r in picked:
        key = f"{_bucket(r.get('signal_zscore'))} | {_label(r.get(condition), cuts, condition)}"
        cells.setdefault(key, []).append(float(r[outcome_field]))

    summary = {k: _stats(v) for k, v in sorted(cells.items())}
    examined = sum(1 for s in summary.values() if s.get("n", 0) >= THIN_BUCKET)
    strong = [k for k, s in summary.items()
              if s.get("n", 0) >= THIN_BUCKET
              and s.get("standard_errors") is not None
              and abs(s["standard_errors"]) >= 2]
    return {
        "family": family,
        "outcome": outcome_field,
        "condition": condition,
        "signals": len(picked),
        "cut_points": [round(c, 4) for c in cuts],
        "cells": summary,
        # The honest denominator. Reported whether or not anything was found.
        "cells_examined": examined,
        "cells_past_2se": len(strong),
        "expected_by_chance": round(examined * NOISE_RATE_AT_2SE, 2),
        "reading": _reading(len(strong), examined),
        "return_basis": (picked[0].get("return_basis") if picked else None),
        "study_version": STUDY_VERSION,
    }


def _reading(found: int, examined: int) -> str:
    if not examined:
        return "no cell had enough observations to read"
    expected = examined * NOISE_RATE_AT_2SE
    if found == 0:
        return "nothing past two standard errors"
    if found <= expected:
        return (f"{found} cell(s) past 2 se, and {expected:.1f} expected by "
                f"chance across {examined} -- indistinguishable from noise")
    return (f"{found} cell(s) past 2 se against {expected:.1f} expected by "
            f"chance -- worth a larger sample, not a conclusion")
