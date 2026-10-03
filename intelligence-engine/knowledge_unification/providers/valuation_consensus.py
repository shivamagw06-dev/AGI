"""KUL provider — Capital IQ market consensus from valuation_consensus store.

Surfaces broker consensus / targets / coverage as Market Consensus observations
so Ask AGI can learn from the Valuation Intelligence dashboard.

Never frames CapIQ broker counts as AGI BUY/SELL recommendations.
AGI Institutional Intelligence remains a separate layer.
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_MARKET_NOTE = (
    "Capital IQ market consensus (sell-side brokers) — reported market data, "
    "not an AGI recommendation."
)

_SECTOR_HINTS = (
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
)

_LOWEST_RE = re.compile(r"\b(lowest|least|worst|smallest)\b", re.I)
_COVERAGE_RE = re.compile(r"\b(covered|coverage|analysts?|brokers?)\b", re.I)
_SCREEN_RE = re.compile(
    r"\b(highest|lowest|most|least|top|best|worst|widest|biggest|rank|list|which)\b",
    re.I,
)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _sector_hint(question: str) -> Optional[str]:
    q = (question or "").lower()
    for sector in _SECTOR_HINTS:
        if sector.lower() in q:
            return sector
    # Common shorthands mapped onto CapIQ GICS labels.
    aliases = {
        "it services": "Information Technology",
        "tech": "Information Technology",
        "banks": "Financials",
        "banking": "Financials",
        "financial": "Financials",
        "pharma": "Health Care",
        "healthcare": "Health Care",
        "fmcg": "Consumer Staples",
        "staples": "Consumer Staples",
        "auto": "Consumer Discretionary",
        "metals": "Materials",
        "chemicals": "Materials",
        "oil": "Energy",
        "power": "Utilities",
        "realty": "Real Estate",
        "telecom": "Communication Services",
    }
    for alias, sector in aliases.items():
        if re.search(rf"\b{re.escape(alias)}\b", q):
            return sector
    return None


class ValuationConsensusProvider:
    spec = ProviderSpec(
        id="valuation_consensus",
        label="Valuation Consensus (Capital IQ Market Consensus)",
        coverage="Institutional consensus dashboard — CapIQ targets, upside, broker counts, coverage",
        priority=18,
        supported_question_types=(
            "consensus",
            "company",
            "valuation",
            "market",
            "business_model",
        ),
        typical_latency_ms=10,
        confidence_ceiling=0.9,
    )

    def health_check(self) -> str:
        try:
            from valuation_consensus.store import load_live

            n = int(load_live().get("row_count") or 0)
            if n >= 1000:
                return "ok"
            if n > 0:
                return "degraded"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            from valuation_consensus.store import get_row

            ticker = plan.ticker_hint
            question = getattr(plan, "question", "") or ""
            if ticker:
                row = get_row(ticker)
                if row:
                    return self._company_result(t0, ticker, row, question=question)
                # A company-bound lookup must never fall through to the market
                # screen and present other companies' consensus as evidence.
                return empty_result(self.spec.id, t0, "no_consensus_row")

            if "consensus" in (plan.question_types or []) or _SCREEN_RE.search(question):
                return self._screen_result(t0, question)
            return empty_result(self.spec.id, t0, "no_ticker")
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

    # ------------------------------------------------------------------
    # Company-level consensus
    # ------------------------------------------------------------------
    def _company_result(
        self,
        t0: float,
        ticker: str,
        row: dict[str, Any],
        *,
        question: str = "",
    ) -> ProviderResult:
        from valuation_consensus.agi_panel import soft_consensus_facts

        facts = soft_consensus_facts(row)
        if not facts:
            return empty_result(self.spec.id, t0, "no_usable_consensus_fields")

        name = row.get("company_name") or ticker
        cmp_v, target = row.get("cmp"), row.get("target_price")
        coverage = row.get("coverage")
        upside = row.get("upside")

        why: list[str] = [_MARKET_NOTE]
        headline_bits: list[str] = []

        if target is not None:
            headline_bits.append(f"consensus target {_fmt(target)}")
            why.append(
                f"Consensus target price for {name}: {_fmt(target)} "
                f"against a last price of {_fmt(cmp_v)}"
                + (f" — implied upside {_fmt(upside)}%." if upside is not None else ".")
            )
            if row.get("target_high") is not None or row.get("target_low") is not None:
                why.append(
                    f"Target range: low {_fmt(row.get('target_low'))} to "
                    f"high {_fmt(row.get('target_high'))}"
                    + (
                        f" (std dev {_fmt(row.get('target_std_dev'))})."
                        if row.get("target_std_dev") is not None
                        else "."
                    )
                )
        elif cmp_v is not None:
            why.append(f"Last price for {name}: {_fmt(cmp_v)}. No consensus target in this export.")

        if coverage is not None:
            headline_bits.append(f"{_fmt(coverage)} analysts covering")
            why.append(f"Analyst coverage: {_fmt(coverage)} estimates contribute to the consensus.")

        reco_bits = [
            f"{label} {_fmt(row.get(key))}"
            for label, key in (
                ("Buy", "buy_count"),
                ("Outperform", "outperform_count"),
                ("Hold", "hold_count"),
                ("Sell", "sell_count"),
                ("No opinion", "no_opinion_count"),
            )
            if row.get(key) is not None
        ]
        if reco_bits:
            why.append(
                "Broker recommendation split (market consensus, not AGI advice): "
                + "; ".join(reco_bits)
                + "."
            )

        if row.get("sector") or row.get("industry"):
            why.append(
                f"Sector / Industry: {row.get('sector') or 'n/a'} / {row.get('industry') or 'n/a'}."
            )
        if row.get("return_1y") is not None:
            why.append(f"1-year price change: {_fmt(row.get('return_1y'))}%.")

        why.append(
            "AGI Institutional Intelligence is assessed separately and is not derived from "
            "these broker views."
        )

        q = question.lower()
        if "high target" in q and row.get("target_high") is not None:
            summary = f"{name} — the Capital IQ consensus high target is {_fmt(row.get('target_high'))}."
        elif "low target" in q and row.get("target_low") is not None:
            summary = f"{name} — the Capital IQ consensus low target is {_fmt(row.get('target_low'))}."
        elif ("analyst" in q and "cover" in q) and coverage is not None:
            summary = f"{name} — {_fmt(coverage)} analysts contribute to the Capital IQ consensus."
        else:
            summary = (
                f"{name} — Capital IQ market consensus: "
                + (", ".join(headline_bits) if headline_bits else "coverage details below")
                + "."
            )

        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=0.88,
            t0=t0,
            summary=summary,
            why=why,
            evidence=[
                {
                    "source": "valuation_consensus",
                    "title": f"{ticker}.market_consensus",
                    "effective_date": row.get("updated_at"),
                    "layer": "market_consensus",
                }
            ],
            facts=facts,
            raw={
                "ticker": ticker,
                "layer": "market_consensus",
                "provider_note": _MARKET_NOTE,
                "valuation": {
                    "cmp": cmp_v,
                    "target_price": target,
                    "target_high": row.get("target_high"),
                    "target_low": row.get("target_low"),
                    "target_std_dev": row.get("target_std_dev"),
                    "upside": upside,
                    "coverage": coverage,
                    "buy_count": row.get("buy_count"),
                    "outperform_count": row.get("outperform_count"),
                    "hold_count": row.get("hold_count"),
                    "sell_count": row.get("sell_count"),
                    "no_opinion_count": row.get("no_opinion_count"),
                },
                "identity": {
                    "company_name": name,
                    "sector": row.get("sector"),
                    "industry": row.get("industry"),
                },
            },
        )

    # ------------------------------------------------------------------
    # Market / sector-level consensus screens (no ticker bind)
    # ------------------------------------------------------------------
    def _screen_result(self, t0: float, question: str) -> ProviderResult:
        from valuation_consensus.production import analytics, query_rows

        stats = analytics()
        if not stats.get("total_companies"):
            return empty_result(self.spec.id, t0, "consensus_store_empty")

        sector = _sector_hint(question)
        by_coverage = bool(_COVERAGE_RE.search(question)) and not re.search(
            r"\bupside\b", question, re.I
        )
        ascending = bool(_LOWEST_RE.search(question))
        sort_key = "coverage" if by_coverage else "upside"

        filters = {"sector": sector} if sector else {}
        # Only rank names that actually carry a consensus figure.
        if sort_key == "upside":
            filters = {**filters, "coverage_min": 1}
        listing = query_rows(
            q="",
            page=1,
            page_size=10,
            sort=sort_key,
            sort_dir="asc" if ascending else "desc",
            filters=filters,
        )
        items = [r for r in (listing.get("items") or []) if r.get(sort_key) is not None]
        if not items:
            return empty_result(self.spec.id, t0, "no_consensus_matches")

        scope = f"{sector} " if sector else ""
        direction = "lowest" if ascending else "highest"
        label = "analyst coverage" if sort_key == "coverage" else "consensus upside"

        why: list[str] = [_MARKET_NOTE]
        for r in items[:8]:
            why.append(
                f"{r.get('company_name') or r.get('ticker')} ({r.get('ticker')}): "
                f"{label} {_fmt(r.get(sort_key))}"
                + ("%" if sort_key == "upside" else "")
                + f"; target {_fmt(r.get('target_price'))} vs price {_fmt(r.get('cmp'))}"
                + f"; sector {r.get('sector') or 'n/a'}."
            )
        why.append(
            f"Universe: {_fmt(stats.get('total_companies'))} companies in the Capital IQ "
            f"consensus set; average target upside {_fmt(stats.get('average_target_upside'))}%, "
            f"average coverage {_fmt(stats.get('average_coverage'))} analysts."
        )
        why.append(
            "Ranking reflects sell-side consensus only — AGI does not issue buy or sell calls."
        )

        summary = (
            f"Capital IQ consensus screen — {scope}companies with the {direction} {label}: "
            + ", ".join(
                f"{r.get('ticker')} ({_fmt(r.get(sort_key))}{'%' if sort_key == 'upside' else ''})"
                for r in items[:5]
            )
            + "."
        )

        facts = [
            {
                "field": f"{direction}_{sort_key}",
                "value": r.get(sort_key),
                "ticker": r.get("ticker"),
                "company_name": r.get("company_name"),
                "sector": r.get("sector"),
                "source": "capital_iq_market_consensus",
                "layer": "market_consensus",
            }
            for r in items
        ]

        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=0.84,
            t0=t0,
            summary=summary,
            why=why,
            evidence=[
                {
                    "source": "valuation_consensus",
                    "title": f"consensus_screen:{sort_key}:{sector or 'all_sectors'}",
                    "effective_date": stats.get("updated_at"),
                    "layer": "market_consensus",
                }
            ],
            facts=facts,
            raw={
                "layer": "market_consensus",
                "provider_note": _MARKET_NOTE,
                "screen": {
                    "sort": sort_key,
                    "direction": "asc" if ascending else "desc",
                    "sector": sector,
                    "matches": listing.get("total"),
                },
                "universe": {
                    "total_companies": stats.get("total_companies"),
                    "average_target_upside": stats.get("average_target_upside"),
                    "average_coverage": stats.get("average_coverage"),
                    "most_covered": stats.get("most_covered"),
                    "highest_upside": stats.get("highest_upside"),
                },
                "items": items,
            },
        )
