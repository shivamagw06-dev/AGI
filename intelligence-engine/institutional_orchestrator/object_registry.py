"""UAG-01 Object Registry — engines register capabilities; router discovers them."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class ObjectRegistration:
    object_type: str
    routes: tuple[str, ...]
    provider: str
    planner: str  # company | portfolio | market | governance
    description: str = ""
    retrieve: Optional[Callable[..., dict[str, Any]]] = field(default=None, compare=False, hash=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "routes": list(self.routes),
            "provider": self.provider,
            "planner": self.planner,
            "description": self.description,
            "has_provider": self.retrieve is not None,
        }


_REGISTRY: dict[str, ObjectRegistration] = {}


def _period_parts(row: dict[str, Any]) -> tuple[int, int]:
    period = str(row.get("fiscal_period") or row.get("fiscal_year") or "")
    # Warehouse vendors use both "FY27Q1" and "Q1 FY27".  Extract the
    # labelled components instead of assuming that the first number is a year.
    fiscal_year = re.search(r"\bFY\s*(\d{2,4})\b", period, flags=re.IGNORECASE)
    fiscal_quarter = re.search(r"\bQ\s*([1-4])\b", period, flags=re.IGNORECASE)
    if fiscal_year:
        year = int(fiscal_year.group(1))
        if year < 100:
            year += 2000
        return year, int(fiscal_quarter.group(1)) if fiscal_quarter else 0
    numbers = [int(n) for n in re.findall(r"\d+", period)]
    year = numbers[0] if numbers else 0
    if year and year < 100:
        year += 2000
    return year, numbers[1] if len(numbers) > 1 else 0


def _statement_rank(row: dict[str, Any]) -> tuple[int, int, int, str]:
    """Choose a like-for-like current statement without mixing providers.

    The warehouse may retain historical imports from several vendors.  Ask
    should prefer a consolidated Upstox statement, then the newest fiscal
    period and source update, rather than whichever row happens to sort first.
    """
    source = str(row.get("source") or "").lower()
    # CapIQ is the canonical 2016–2026 annual history. Quarterly rows are
    # unchanged because they are live Upstox reported statements.
    is_capiq = (
        str(row.get("statement_version") or "").lower().startswith("capiq_workbook_")
        or source == "capital_iq_workbook"
    )
    source_rank = 0 if is_capiq else 1 if "upstox" in source else 2
    statement_rank = 0 if str(row.get("statement_type") or "").upper() == "CONSOLIDATED" else 1
    year, quarter = _period_parts(row)
    return (source_rank, statement_rank, -(year * 10 + quarter), str(row.get("last_updated") or ""))


def _preferred_statement(rows: list[dict[str, Any]], fallback: dict[str, Any]) -> dict[str, Any]:
    usable = [row for row in rows if any(row.get(key) is not None for key in ("pat", "eps", "revenue"))]
    return min(usable, key=_statement_rank) if usable else fallback


def _annual_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One annual record per fiscal year, with CapIQ as the history of record."""
    from institutional_warehouse.financials import canonical_statement_series

    return canonical_statement_series(rows, period_key="fiscal_year", annual=True)


def _pat_growth(current: dict[str, Any], prior: dict[str, Any], *, basis: str) -> dict[str, Any] | None:
    """Return a labelled PAT growth observation without concealing its basis."""
    try:
        growth = (float(current["pat"]) / float(prior["pat"]) - 1.0) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return {
        "metric": "pat_yoy_pct",
        "value": round(growth, 2),
        "prior_period": prior.get("fiscal_period") or prior.get("fiscal_year"),
        "source": current.get("source"),
        "statement_type": current.get("statement_type"),
        "basis": basis,
    }


def _pat_yoy(current: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Calculate PAT growth, preferring strict lineage then a disclosed same-provider pair.

    Some providers expose a newly reported consolidated quarter before they
    publish the matching quarter from the prior year.  In that case we can
    still show the warehouse's same-provider trend, but must mark it as a
    separate, unclassified-statement series instead of passing it off as the
    consolidated headline's YoY growth.
    """
    year, quarter = _period_parts(current)
    if not year or not quarter or current.get("pat") is None:
        return None
    source = str(current.get("source") or "").lower()
    statement_type = str(current.get("statement_type") or "").upper()
    matches = [
        row for row in rows
        if _period_parts(row) == (year - 1, quarter)
        and str(row.get("source") or "").lower() == source
        and str(row.get("statement_type") or "").upper() == statement_type
        and row.get("pat") not in (None, 0)
    ]
    if matches:
        return _pat_growth(current, min(matches, key=_statement_rank), basis="same_source_statement")

    # Do not mix a current row from one source with a prior row from another.
    # Instead find a complete current/prior pair in one provider's own series.
    # This preserves a meaningful percentage while making the different basis
    # explicit to the response layer.
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for candidate in rows:
        candidate_year, candidate_quarter = _period_parts(candidate)
        if (candidate_year, candidate_quarter) != (year, quarter) or candidate.get("pat") is None:
            continue
        candidate_source = str(candidate.get("source") or "").lower()
        candidate_type = str(candidate.get("statement_type") or "").upper()
        prior_rows = [
            row for row in rows
            if _period_parts(row) == (year - 1, quarter)
            and str(row.get("source") or "").lower() == candidate_source
            and str(row.get("statement_type") or "").upper() == candidate_type
            and row.get("pat") not in (None, 0)
        ]
        if prior_rows:
            candidates.append((candidate, min(prior_rows, key=_statement_rank)))
    if not candidates:
        return None
    fallback_current, fallback_prior = min(candidates, key=lambda pair: _statement_rank(pair[0]))
    return _pat_growth(fallback_current, fallback_prior, basis="same_provider_unclassified")


def reset_registry_for_tests() -> None:
    _REGISTRY.clear()
    bootstrap_default_registry()


def register(
    object_type: str,
    *,
    routes: list[str] | tuple[str, ...],
    provider: str,
    planner: str = "company",
    description: str = "",
    retrieve: Optional[Callable[..., dict[str, Any]]] = None,
) -> None:
    key = str(object_type).strip()
    _REGISTRY[key] = ObjectRegistration(
        object_type=key,
        routes=tuple(str(r).lower() for r in routes),
        provider=provider,
        planner=planner,
        description=description,
        retrieve=retrieve,
    )


def get(object_type: str) -> Optional[ObjectRegistration]:
    return _REGISTRY.get(str(object_type))


def all_registrations() -> list[ObjectRegistration]:
    return list(_REGISTRY.values())


def catalog() -> list[dict[str, Any]]:
    return [r.to_dict() for r in sorted(_REGISTRY.values(), key=lambda x: x.object_type)]


def match_routes(question: str) -> list[ObjectRegistration]:
    q = (question or "").lower()
    hits: list[tuple[int, ObjectRegistration]] = []
    for reg in _REGISTRY.values():
        score = 0
        for route in reg.routes:
            if route and route in q:
                score += max(1, len(route.split()))
        if score:
            hits.append((score, reg))
    hits.sort(key=lambda x: (-x[0], x[1].object_type))
    return [r for _, r in hits]


# --- Default provider retrieve functions (stateless calls into domain engines) ---


def _retrieve_company_decision(ctx: dict[str, Any]) -> dict[str, Any]:
    ticker = str((ctx.get("entities") or ["AXISBANK"])[0] or "AXISBANK").upper()
    # Soft: institutional decision / IDS if available
    try:
        from institutional_decision.production import get_decision  # type: ignore

        out = get_decision(ticker)
        if isinstance(out, dict) and out.get("ok") is not False:
            return {"ok": True, "object_type": "CompanyDecision", "ticker": ticker, "payload": out}
    except Exception:
        pass
    try:
        from decision_engine.production import get_latest  # type: ignore

        out = get_latest(ticker)
        if out:
            return {"ok": True, "object_type": "CompanyDecision", "ticker": ticker, "payload": out}
    except Exception:
        pass
    # Deterministic placeholder from ticker context — orchestration must not invent BUY/SELL
    return {
        "ok": True,
        "object_type": "CompanyDecision",
        "ticker": ticker,
        "payload": {
            "ticker": ticker,
            "available": False,
            "note": "Company decision provider soft-unavailable; no recommendation invented",
        },
        "soft_missing": True,
    }


def _retrieve_portfolio_graph(ctx: dict[str, Any]) -> dict[str, Any]:
    pid = str(ctx.get("portfolio_id") or "agi-core-equity")
    try:
        from institutional_portfolio.production import get_portfolio_graph

        out = get_portfolio_graph(pid, rebuild=True, include_company_graphs=False)
        return {"ok": bool(out.get("ok")), "object_type": "PortfolioGraph", "payload": out}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "object_type": "PortfolioGraph", "error": str(exc)}


def _retrieve_portfolio_risk(ctx: dict[str, Any]) -> dict[str, Any]:
    pid = str(ctx.get("portfolio_id") or "agi-core-equity")
    try:
        from institutional_portfolio_risk.production import evaluate_portfolio_risk

        out = evaluate_portfolio_risk({"portfolio_id": pid})
        return {"ok": bool(out.get("ok")), "object_type": "PortfolioRisk", "payload": out}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "object_type": "PortfolioRisk", "error": str(exc)}


def _retrieve_policy(ctx: dict[str, Any]) -> dict[str, Any]:
    pid = str(ctx.get("portfolio_id") or "agi-core-equity")
    profile = str(ctx.get("policy") or "family_office")
    try:
        from institutional_policy.production import check_policy

        out = check_policy({"portfolio_id": pid, "policy": profile})
        return {"ok": bool(out.get("ok")), "object_type": "PolicyAssessment", "payload": out}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "object_type": "PolicyAssessment", "error": str(exc)}


def _retrieve_portfolio_decision(ctx: dict[str, Any]) -> dict[str, Any]:
    pid = str(ctx.get("portfolio_id") or "agi-core-equity")
    try:
        from institutional_portfolio_decision.production import decide_portfolio

        out = decide_portfolio({"portfolio_id": pid, "policy": ctx.get("policy") or "family_office"})
        return {"ok": bool(out.get("ok")), "object_type": "PortfolioDecision", "payload": out}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "object_type": "PortfolioDecision", "error": str(exc)}


def _retrieve_committee(ctx: dict[str, Any]) -> dict[str, Any]:
    pid = str(ctx.get("portfolio_id") or "agi-core-equity")
    try:
        from institutional_committee.production import review_committee

        out = review_committee({"portfolio_id": pid, "policy": ctx.get("policy") or "family_office"})
        return {"ok": bool(out.get("ok")), "object_type": "CommitteeResolution", "payload": out}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "object_type": "CommitteeResolution", "error": str(exc)}


def _retrieve_observation(ctx: dict[str, Any]) -> dict[str, Any]:
    ticker = str((ctx.get("entities") or [""])[0] or "").upper()
    try:
        from institutional_observation.production import get_observations  # type: ignore

        out = get_observations(ticker) if ticker else {"ok": False}
        return {"ok": bool(out.get("ok", True)), "object_type": "Observation", "payload": out}
    except Exception:
        return {
            "ok": True,
            "object_type": "Observation",
            "payload": {"available": False, "ticker": ticker},
            "soft_missing": True,
        }


def _retrieve_forecast(ctx: dict[str, Any]) -> dict[str, Any]:
    ticker = str((ctx.get("entities") or [""])[0] or "").upper()
    try:
        from institutional_forecasting.production import get_company_scenarios  # type: ignore

        out = get_company_scenarios(ticker) if ticker else {"ok": False}
        return {"ok": bool(out.get("ok", True)), "object_type": "Forecast", "payload": out}
    except Exception:
        return {
            "ok": True,
            "object_type": "Forecast",
            "payload": {"available": False, "ticker": ticker},
            "soft_missing": True,
        }


def _retrieve_research(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "object_type": "Research",
        "payload": {
            "note": "Research objects consulted via registry; detailed IRP soft-unavailable",
            "question": ctx.get("question"),
        },
        "soft_missing": True,
    }


def _retrieve_comparison_evidence(ctx: dict[str, Any]) -> dict[str, Any]:
    """Read company facts from the warehouse for a side-by-side research question.

    This is intentionally a fact provider, not a decision engine: it must never
    turn two records into a buy/sell recommendation.  The resulting source and
    as-of fields let the response layer make the provenance visible.
    """
    symbols = list(dict.fromkeys(str(x).upper() for x in (ctx.get("entities") or []) if x))[:5]
    if len(symbols) < 2:
        return {
            "ok": True,
            "object_type": "ComparisonEvidence",
            "payload": {"available": False, "reason": "two_companies_required", "symbols": symbols},
            "soft_missing": True,
        }
    try:
        from institutional_warehouse import db

        def _statement_rows(tab_id: str, symbol: str, limit: int) -> list[dict[str, Any]]:
            """Indexed comparison read: avoid store.fetch's COUNT + full shaping."""
            table = db.physical_table(tab_id)
            rows = db.query(
                f"SELECT * FROM {table} WHERE sys_entity = ? "
                "AND COALESCE(sys_published, 1) = 1 "
                "ORDER BY sys_updated_at DESC LIMIT ?",
                (symbol, limit),
            )
            for row in rows:
                row["_meta"] = {
                    "unit_method": row.get("sys_unit_method"),
                    "reported_unit": row.get("sys_reported_unit"),
                }
            return rows

        companies: list[dict[str, Any]] = []
        for symbol in symbols:
            # Do not call ``read_company`` here: it opens every warehouse sheet
            # (news, prices, ownership, research, etc.) for each symbol.  A
            # financial comparison only needs the three bounded source tables.
            # The question can explicitly ask for a decade. Read the bounded
            # company series (not the whole warehouse) so CapIQ FY2016–FY2026
            # is actually available to the answer formatter.
            annual_rows = _statement_rows("financials_annual", symbol, 80)
            quarter_rows = _statement_rows("financials_quarterly", symbol, 12)
            valuation_rows = _statement_rows("historical_valuation", symbol, 1)
            ratio_rows = _statement_rows("sector_ratio_history", symbol, 180)
            if not annual_rows and not quarter_rows and not valuation_rows and not ratio_rows:
                continue
            annual_history = _annual_history(annual_rows)
            annual = annual_history[-1] if annual_history else {}
            quarter = _preferred_statement(
                quarter_rows,
                {},
            )
            valuation = valuation_rows[0] if valuation_rows else {}
            source_rows = [row for row in (quarter, annual, valuation) if row]
            sources = {
                "Capital IQ workbook" if str(row.get("statement_version") or "").startswith("capiq_workbook_")
                else str(row.get("source"))
                for row in source_rows if row.get("source") or row.get("statement_version")
            }
            if ratio_rows:
                sources.add("Capital IQ sector-ratio workbook")
            companies.append(
                {
                    "symbol": symbol,
                    "annual": annual,
                    "annual_history": annual_history,
                    "quarter": quarter,
                    "valuation": valuation,
                    "ratio_history": sorted(ratio_rows, key=lambda row: str(row.get("fiscal_year") or "")),
                    "provider_ratios": {},
                    "earnings_trend": _pat_yoy(quarter, quarter_rows),
                    "sources": sorted(source for source in sources if source),
                    "as_of": next(
                        (
                            row.get("effective_date") or row.get("filing_date") or row.get("last_updated")
                            for row in source_rows
                            if row.get("effective_date") or row.get("filing_date") or row.get("last_updated")
                        ),
                        None,
                    ),
                }
            )
        if len(companies) < 2:
            return {
                "ok": True,
                "object_type": "ComparisonEvidence",
                "payload": {"available": False, "reason": "verified_warehouse_records_missing", "symbols": symbols},
                "soft_missing": True,
            }
        return {
            "ok": True,
            "object_type": "ComparisonEvidence",
            "payload": {
                "available": True,
                "companies": companies,
                "source": "institutional_warehouse",
                "question": str(ctx.get("question") or ""),
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "object_type": "ComparisonEvidence", "error": str(exc)}


def _retrieve_relationships(ctx: dict[str, Any]) -> dict[str, Any]:
    """CCI-01 soft retrieve — relationship reasoning over KG-01; no recommendations."""
    question = str(ctx.get("question") or "")
    entities = ctx.get("entities") or []
    ticker = str(entities[0]).upper() if entities else ""
    try:
        from institutional_cross_company.production import query_relationships

        out = query_relationships(
            {
                "question": question,
                "ticker": ticker,
                "portfolio_id": ctx.get("portfolio_id") or "agi-core-equity",
            }
        )
        return {
            "ok": bool(out.get("ok")),
            "object_type": "Relationship",
            "payload": out,
            "owns_graph": False,
            "graph_system_of_record": "KG-01",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": True,
            "object_type": "Relationship",
            "payload": {"available": False, "error": str(exc)},
            "soft_missing": True,
            "owns_graph": False,
        }


def bootstrap_default_registry() -> None:
    if _REGISTRY:
        return
    register(
        "ComparisonEvidence",
        routes=["compare", "comparison", "versus", " vs "],
        provider="institutional_warehouse",
        planner="company",
        description="Verified warehouse facts for multi-company comparison",
        retrieve=_retrieve_comparison_evidence,
    )
    register(
        "CompanyDecision",
        routes=["buy", "sell", "hold", "recommendation", "investment thesis", "valuation", "should i"],
        provider="institutional_decision",
        planner="company",
        description="Company InstitutionalDecision (referential)",
        retrieve=_retrieve_company_decision,
    )
    register(
        "PortfolioGraph",
        routes=["portfolio", "holdings", "allocation", "exposure", "what do we own"],
        provider="institutional_portfolio",
        planner="portfolio",
        description="PKG-01 InstitutionalPortfolio",
        retrieve=_retrieve_portfolio_graph,
    )
    register(
        "PortfolioRisk",
        routes=["portfolio risk", "risk", "drawdown", "concentration", "stress", "liquidity", "hhi"],
        provider="institutional_portfolio_risk",
        planner="portfolio",
        description="PRE-01 InstitutionalPortfolioRisk",
        retrieve=_retrieve_portfolio_risk,
    )
    register(
        "PolicyAssessment",
        routes=["policy", "mandate", "violation", "compliance", "constraint", "allowed"],
        provider="institutional_policy",
        planner="governance",
        description="PCE-01 InstitutionalPolicyAssessment",
        retrieve=_retrieve_policy,
    )
    register(
        "PortfolioDecision",
        routes=["reduce", "increase", "trim", "rebalance", "portfolio decision", "which holdings"],
        provider="institutional_portfolio_decision",
        planner="portfolio",
        description="CIO-01 InstitutionalPortfolioDecision",
        retrieve=_retrieve_portfolio_decision,
    )
    register(
        "CommitteeResolution",
        routes=["committee", "approved", "rejected", "deferred", "escalated", "why was"],
        provider="institutional_committee",
        planner="governance",
        description="ICE-01 InstitutionalCommitteeResolution",
        retrieve=_retrieve_committee,
    )
    register(
        "Observation",
        routes=["observation", "monitor", "alert", "what changed", "today"],
        provider="institutional_observation",
        planner="market",
        description="IO-01 observations",
        retrieve=_retrieve_observation,
    )
    register(
        "Forecast",
        routes=["forecast", "scenario", "outlook", "rbi"],
        provider="institutional_forecasting",
        planner="market",
        description="FG-01 forecasts/scenarios",
        retrieve=_retrieve_forecast,
    )
    register(
        "Research",
        routes=["research", "note", "briefing", "explain"],
        provider="research",
        planner="company",
        description="Research packages (soft)",
        retrieve=_retrieve_research,
    )
    register(
        "Relationship",
        routes=[
            "competitor",
            "compete",
            "similar",
            "connected to",
            "macro risk",
            "oil",
            "interest rates",
            "peer",
            "sector network",
            "relationship",
            "how does",
            "affect",
        ],
        provider="institutional_cross_company",
        planner="market",
        description="CCI-01 InstitutionalRelationship (reasons over KG-01; does not own graph)",
        retrieve=_retrieve_relationships,
    )


# Bootstrap on import
bootstrap_default_registry()
