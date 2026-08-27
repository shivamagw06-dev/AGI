"""Check what the pages display against an independent source.

Every defect found on 2026-08-20 had the same shape: a correct source existed
in the warehouse and the display used something else.

    1Y return    prices were right; the page showed a year-stale upload
    upside       the target was right; the price inside it was not
    cmp          1,050 of 1,162 symbols disagreed with the traded close
    consensus    the warehouse had a date; every row rendered null
    spread_bps   624 of 1,698 values were negative, which is impossible

None were caught by tests, receipts or validation gates, and this warehouse has
more of those than most systems. They were caught because a person compared one
number on the page to a public quote.

That is the gap this closes. Everything here verifies internal consistency;
nothing until now asked whether the output matches the outside world. A
reconciliation is the only check that can fail when the arithmetic is perfect
and the answer is still wrong.

The reference is injected rather than fetched, for two reasons: the comparison
logic is then testable without a network, and the vendor token stays in the
caller's environment instead of this module's.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

# Per-field tolerance and how to read it. Price should be near exact - both
# sides are quoting the same trade - while a multiple legitimately differs on
# the earnings basis each vendor uses, so it gets more room. Returns are
# compared in percentage points, because a relative test on a number near zero
# reports enormous errors for trivial differences.
TOLERANCES: dict[str, dict[str, Any]] = {
    "price": {"mode": "relative", "warn": 0.01, "fail": 0.03},
    "market_cap": {"mode": "relative", "warn": 0.02, "fail": 0.05},
    "pe": {"mode": "relative", "warn": 0.08, "fail": 0.20},
    "pb": {"mode": "relative", "warn": 0.08, "fail": 0.20},
    "roe": {"mode": "absolute", "warn": 2.0, "fail": 5.0},
    "return_1y": {"mode": "absolute", "warn": 3.0, "fail": 8.0},
}


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def compare_field(field: str, ours: Any, theirs: Any) -> dict[str, Any]:
    """One field, one company. Missing on either side is not a divergence."""
    rule = TOLERANCES.get(field)
    mine, other = _num(ours), _num(theirs)
    if rule is None:
        return {"field": field, "status": "UNCHECKED", "reason": "no_tolerance_defined"}
    if mine is None or other is None:
        return {"field": field, "status": "SKIPPED",
                "reason": "missing_ours" if mine is None else "missing_reference",
                "ours": mine, "reference": other}

    if rule["mode"] == "relative":
        if other == 0:
            return {"field": field, "status": "SKIPPED", "reason": "reference_is_zero",
                    "ours": mine, "reference": other}
        delta = abs(mine - other) / abs(other)
    else:
        delta = abs(mine - other)

    status = "FAIL" if delta > rule["fail"] else "WARN" if delta > rule["warn"] else "OK"
    return {"field": field, "status": status, "ours": mine, "reference": other,
            "delta": round(delta, 4), "mode": rule["mode"],
            "warn_at": rule["warn"], "fail_at": rule["fail"]}


def compare_symbol(symbol: str, ours: dict[str, Any],
                   reference: dict[str, Any]) -> dict[str, Any]:
    checks = [compare_field(f, ours.get(f), reference.get(f)) for f in TOLERANCES]
    failed = [c for c in checks if c["status"] == "FAIL"]
    warned = [c for c in checks if c["status"] == "WARN"]
    return {
        "symbol": str(symbol).upper(),
        "status": "FAIL" if failed else "WARN" if warned else "OK",
        "checks": checks,
        "failed_fields": [c["field"] for c in failed],
        "warned_fields": [c["field"] for c in warned],
    }


def reconcile(
    ours_by_symbol: dict[str, dict[str, Any]],
    reference_by_symbol: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compare every symbol present on both sides and summarise.

    A symbol the reference does not cover is reported separately rather than
    counted as agreement - silence is not confirmation.
    """
    ours = {str(k).upper(): v for k, v in (ours_by_symbol or {}).items()}
    theirs = {str(k).upper(): v for k, v in (reference_by_symbol or {}).items()}
    shared = sorted(set(ours) & set(theirs))

    results = [compare_symbol(s, ours[s], theirs[s]) for s in shared]
    failed = [r for r in results if r["status"] == "FAIL"]
    warned = [r for r in results if r["status"] == "WARN"]

    by_field: dict[str, dict[str, int]] = {}
    for result in results:
        for check in result["checks"]:
            bucket = by_field.setdefault(check["field"], {"OK": 0, "WARN": 0,
                                                          "FAIL": 0, "SKIPPED": 0})
            bucket[check["status"]] = bucket.get(check["status"], 0) + 1

    return {
        "ok": not failed,
        "compared": len(shared),
        "not_in_reference": sorted(set(ours) - set(theirs)),
        "not_in_ours": sorted(set(theirs) - set(ours)),
        "failed": len(failed),
        "warned": len(warned),
        "by_field": by_field,
        # Worst first: a reader should see the largest disagreement immediately.
        "divergences": sorted(
            [r for r in results if r["status"] != "OK"],
            key=lambda r: (r["status"] != "FAIL", -len(r["failed_fields"])),
        )[:50],
        "verdict": (
            f"{len(failed)} symbols disagree beyond tolerance"
            if failed else
            f"{len(warned)} symbols drifting within tolerance"
            if warned else
            "every compared field agrees with the reference"
        ),
    }


def desk_values(limit: int = 60) -> dict[str, dict[str, Any]]:
    """What the desk would display, in the shape a reference can be compared to.

    Reads the same sources the scanner reads, so a divergence here is a
    divergence a user would have seen on the page.
    """
    try:
        from hedge_fund_lab.scanner import _universe
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in (_universe() or [])[:max(1, limit)]:
        symbol = str(row.get("ticker") or "").upper()
        if not symbol:
            continue
        consensus = row.get("consensus") or {}
        out[symbol] = {
            "price": row.get("price"),
            # The reference quotes market cap in crore.
            "market_cap": (row["market_cap"] / 1e7
                           if _num(row.get("market_cap")) else None),
            "pe": row.get("pe"),
            "pb": row.get("pb"),
            "roe": row.get("roe"),
            "return_1y": consensus.get("return_1y"),
        }
    return out


def run(
    reference_loader: Callable[[Iterable[str]], dict[str, dict[str, Any]]],
    *,
    limit: int = 60,
) -> dict[str, Any]:
    """Fetch our side, ask the caller for the reference, and compare.

    `reference_loader` receives the symbols to look up and returns the same
    field names. Keeping it injected means no vendor credential lives here.
    """
    ours = desk_values(limit=limit)
    if not ours:
        return {"ok": False, "error": "no_desk_values"}
    try:
        reference = reference_loader(sorted(ours)) or {}
    except Exception as exc:
        return {"ok": False, "error": "reference_unavailable", "detail": str(exc)[:200]}
    return {**reconcile(ours, reference), "sampled": len(ours)}
