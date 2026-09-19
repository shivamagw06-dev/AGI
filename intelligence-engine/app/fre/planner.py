"""Step 2 — Query planner — never issue only one search."""

from __future__ import annotations

from app.fre.models import QueryPlan, QueryUnderstanding, RetrievalTask
from app.fre.understanding import understand_query


_BASE_TASKS = [
    ("Latest annual report", ["annual_report"], [1], 1),
    ("Latest quarterly report", ["quarterly_report"], [1], 1),
    ("Investor presentation", ["investor_presentation"], [1], 2),
    ("Conference call transcript", ["transcript", "conference_call"], [1], 2),
    ("Exchange filings", ["exchange_filing", "nse_bse_filing"], [1, 2], 2),
    ("Recent management guidance", ["transcript", "quarterly_report"], [1], 3),
    ("Recent acquisitions / corporate actions", ["exchange_filing", "news"], [1, 2, 4], 4),
    ("Industry outlook", ["industry_report", "research_publication"], [5, 3], 4),
    ("Latest news", ["news"], [4], 3),
    ("Peer comparison", ["research_publication", "annual_report"], [1, 5], 4),
    ("Analyst estimates", ["research_publication", "news"], [4, 5], 5),
    ("Government / policy context", ["government", "rbi", "sebi"], [2, 3], 4),
]


def plan_retrieval(query: str, *, aoi=None, understanding: QueryUnderstanding | None = None) -> QueryPlan:
    ud = understanding or understand_query(query, aoi=aoi)
    company = ud.companies[0] if ud.companies else None
    symbol = ud.symbols[0] if ud.symbols else ud.primary_entity

    tasks: list[RetrievalTask] = []
    for desc, doc_types, tiers, priority in _BASE_TASKS:
        # Intent-aware pruning: keep high priority always; filter lower ones by needs
        if priority >= 4 and ud.needs:
            keywords = desc.lower()
            if not any(n.split()[0].lower() in keywords or n.lower() in keywords for n in ud.needs):
                # still keep news/filings for investment analysis
                if ud.intent == "investment_analysis" and "news" not in keywords and "filing" not in keywords:
                    if "peer" not in keywords and "policy" not in keywords and "industry" not in keywords:
                        continue
        tasks.append(
            RetrievalTask(
                description=desc,
                document_types=list(doc_types),
                preferred_tiers=list(tiers),
                company=company,
                symbol=symbol,
                priority=priority,
            )
        )

    # Macro-specific extra tasks
    if "macro" in ud.intents or "policy" in ud.intents:
        tasks.append(
            RetrievalTask(
                description="Macro / rates / inflation prints",
                document_types=["fred", "rbi", "imf", "world_bank"],
                preferred_tiers=[2, 3],
                company=company,
                symbol=symbol,
                priority=2,
            )
        )

    tasks.sort(key=lambda t: t.priority)
    return QueryPlan(query=query, understanding=ud, tasks=tasks)
