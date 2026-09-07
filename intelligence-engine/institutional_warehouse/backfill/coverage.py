"""Historical coverage — how much history the warehouse actually holds.

Coverage is measured against what a research desk needs, not against what a
collector returned: years of price history per company, statement periods,
valuation observations, and the gaps in between.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from institutional_warehouse import db, store
from institutional_warehouse.backfill import checkpoints, prices, statements, valuation_history
from institutional_warehouse.backfill.sources import nse_archive

# What "covered" means for a company, in years of daily price history.
DEPTH_TIERS = ((20, "20y+"), (10, "10-20y"), (5, "5-10y"), (1, "1-5y"), (0, "<1y"))


def _years(first: Optional[str], last: Optional[str]) -> float:
    if not first or not last:
        return 0.0
    try:
        delta = datetime.fromisoformat(str(last)) - datetime.fromisoformat(str(first))
        return round(delta.days / 365.25, 2)
    except Exception:
        return 0.0


def company_depth(limit: int = 5000) -> list[dict[str, Any]]:
    """Per-company history depth, straight out of the database."""
    table = db.physical_table("daily_market_history")
    rows = db.query(
        f"SELECT sys_entity AS symbol, COUNT(*) AS points, MIN(date) AS first, MAX(date) AS last"
        f" FROM {table} WHERE sys_entity IS NOT NULL GROUP BY sys_entity"
        f" ORDER BY COUNT(*) DESC LIMIT ?",
        (max(1, int(limit)),),
    )
    out = []
    for row in rows:
        years = _years(row.get("first"), row.get("last"))
        out.append(
            {
                "symbol": row.get("symbol"),
                "points": int(row.get("points") or 0),
                "first": row.get("first"),
                "last": row.get("last"),
                "years": years,
                "tier": next(label for floor, label in DEPTH_TIERS if years >= floor),
            }
        )
    return out


def _tier_counts(depths: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for _, label in DEPTH_TIERS}
    for entry in depths:
        counts[entry["tier"]] += 1
    return counts


def by_table() -> list[dict[str, Any]]:
    out = []
    for tab, period in (
        ("daily_market_history", "date"),
        ("financials_annual", "fiscal_year"),
        ("financials_quarterly", "fiscal_period"),
        ("historical_valuation", "date"),
        ("consensus", "consensus_date"),
        ("ownership", "as_of"),
        ("corporate_actions", "action_date"),
        ("research_timeline", "date"),
    ):
        table = db.physical_table(tab)
        row = db.query(
            f'SELECT COUNT(*) AS rows, COUNT(DISTINCT sys_entity) AS companies,'
            f' COUNT(DISTINCT "{period}") AS periods, MIN("{period}") AS first,'
            f' MAX("{period}") AS last FROM {table}'
        )[0]
        out.append(
            {
                "table": tab,
                "rows": int(row.get("rows") or 0),
                "companies": int(row.get("companies") or 0),
                "periods": int(row.get("periods") or 0),
                "first": row.get("first"),
                "last": row.get("last"),
            }
        )
    return out


def by_sector(limit: int = 40) -> list[dict[str, Any]]:
    sectors: dict[str, dict[str, Any]] = {}
    masters = {
        str(r.get("symbol") or "").upper(): str(r.get("sector") or "Unclassified")
        for r in store.all_rows("company_master", limit=6000)
    }
    for entry in company_depth():
        sector = masters.get(str(entry["symbol"]).upper(), "Unclassified")
        bucket = sectors.setdefault(sector, {"sector": sector, "companies": 0, "deep": 0,
                                             "total_years": 0.0})
        bucket["companies"] += 1
        bucket["total_years"] += entry["years"]
        if entry["years"] >= 10:
            bucket["deep"] += 1
    out = []
    for bucket in sectors.values():
        companies = max(bucket["companies"], 1)
        out.append(
            {
                **bucket,
                "avg_years": round(bucket["total_years"] / companies, 2),
                "deep_pct": round(100.0 * bucket["deep"] / companies, 1),
            }
        )
    return sorted(out, key=lambda b: b["companies"], reverse=True)[:limit]


def reconstruction_inputs() -> dict[str, Any]:
    """What the valuation reconstruction could and could not build, and why.

    A multiple that cannot be computed is a missing input, not a missing feature:
    without a share count there is no market cap, no book value and no EV.
    """
    table = db.physical_table("historical_valuation")
    row = db.query(
        f"SELECT COUNT(*) AS rows,"
        f" SUM(CASE WHEN pe IS NOT NULL THEN 1 ELSE 0 END) AS with_pe,"
        f" SUM(CASE WHEN pb IS NOT NULL THEN 1 ELSE 0 END) AS with_pb,"
        f" SUM(CASE WHEN market_cap IS NOT NULL THEN 1 ELSE 0 END) AS with_market_cap,"
        f" SUM(CASE WHEN ev_ebitda IS NOT NULL THEN 1 ELSE 0 END) AS with_ev_ebitda"
        f" FROM {table}"
    )[0]
    rows = int(row.get("rows") or 0) or 1

    shares = db.query(
        f"SELECT COUNT(DISTINCT sys_entity) AS n FROM {db.physical_table('financials_annual')}"
        f" WHERE shares_outstanding IS NOT NULL"
    )[0]
    statement_companies = db.query(
        f"SELECT COUNT(DISTINCT sys_entity) AS n FROM {db.physical_table('financials_annual')}"
    )[0]

    return {
        "observations": int(row.get("rows") or 0),
        "with_pe_pct": round(100.0 * int(row.get("with_pe") or 0) / rows, 1),
        "with_pb_pct": round(100.0 * int(row.get("with_pb") or 0) / rows, 1),
        "with_market_cap_pct": round(100.0 * int(row.get("with_market_cap") or 0) / rows, 1),
        "with_ev_ebitda_pct": round(100.0 * int(row.get("with_ev_ebitda") or 0) / rows, 1),
        "companies_with_share_count": int(shares.get("n") or 0),
        "companies_with_statements": int(statement_companies.get("n") or 0),
        "note": (
            "P/B, market cap and EV multiples need a share count on the statement. "
            "Where the source omits it, those columns stay empty rather than being guessed."
        ),
    }


def summary() -> dict[str, Any]:
    depths = company_depth()
    # The denominator is every company the warehouse tracks, which is the registry
    # plus anything already carrying prices. Using the registry alone produced a
    # coverage figure above 100% whenever the exchange feed ran ahead of it.
    registered = len(store.entities("company_master"))
    universe = max(registered, len(depths), 1)
    with_history = [d for d in depths if d["points"] > 1]
    deep = [d for d in depths if d["years"] >= 10]
    total_years = sum(d["years"] for d in depths)

    return {
        "ok": True,
        "universe": universe,
        "registered_companies": registered,
        "companies_with_history": len(with_history),
        "companies_deep_10y": len(deep),
        "coverage_pct": round(100.0 * len(with_history) / max(universe, 1), 1),
        "deep_coverage_pct": round(100.0 * len(deep) / max(universe, 1), 1),
        "avg_years": round(total_years / max(len(depths), 1), 2),
        "max_years": max((d["years"] for d in depths), default=0.0),
        "oldest": min((d["first"] for d in depths if d["first"]), default=None),
        "newest": max((d["last"] for d in depths if d["last"]), default=None),
        "tiers": _tier_counts(depths),
        "rows_total": sum(t["rows"] for t in by_table()),
    }


def dashboard(*, top: int = 25) -> dict[str, Any]:
    depths = company_depth()
    return {
        "ok": True,
        "summary": summary(),
        "inputs": reconstruction_inputs(),
        "tables": by_table(),
        "sectors": by_sector(),
        "deepest": depths[:top],
        "shallowest": [d for d in sorted(depths, key=lambda d: d["years"])][:top],
        "jobs": checkpoints.recent_jobs(limit=8),
        "dates": checkpoints.date_coverage(nse_archive.SOURCE),
        "entities": {
            kind: checkpoints.entity_coverage(kind)
            for kind in (prices.KIND, statements.KIND, valuation_history.KIND)
        },
        "failures": checkpoints.failures(limit=25),
    }
