"""KUL production facade — single gateway for Ask and diagnostics."""

from __future__ import annotations

import re
from typing import Any, Optional

from knowledge_unification.fusion import fuse
from knowledge_unification.knowledge_planner import build_knowledge_plan
from knowledge_unification.query_planner import plan_query
from knowledge_unification.ranking import rank_and_filter
from knowledge_unification.registry import get_registry
from knowledge_unification.schema import FusedEvidence, ProviderResult

KUL_VERSION = "1.2.0"
PROGRAMME = "Phase X — Knowledge Unification Layer (+ II Integration 3.1.5)"
_COMPARISON_RE = re.compile(r"\b(compare|versus|\bvs\.?\b|difference between|relative to)\b", re.I)
_EXACT_CONSENSUS_RE = re.compile(
    r"\b(consensus target|target price|price target|high target|low target|"
    r"analysts? cover|rating split|broker (?:estimate|consensus|recommendation))\b",
    re.I,
)


def health() -> dict[str, Any]:
    reg = get_registry()
    dash = reg.dashboard()
    ok_n = sum(1 for p in dash["providers"] if p.get("health") == "ok")
    return {
        "ok": True,
        "programme": PROGRAMME,
        "version": KUL_VERSION,
        "providers_ok": ok_n,
        "providers_total": dash["provider_count"],
        "dashboard": dash,
        "fabricated": False,
    }


def plan_and_gather(
    question: str,
    *,
    ticker: Optional[str] = None,
    max_providers: int = 12,
) -> dict[str, Any]:
    """Full KUL path: query plan → knowledge plan → consult → rank → fuse.

    Entity Intelligence is authoritative: if the contract blocks the planner
    (clarification / unsupported / private insufficient coverage), KUL must
    not run Investment/Business/Industry engines on a substituted entity.
    """
    ei_contract: dict[str, Any] = {}
    try:
        from entity_intelligence.production import analyse as ei_analyse
        from entity_intelligence.production import should_short_circuit

        ei_contract = ei_analyse(question) or {}
        if should_short_circuit(ei_contract) and not _COMPARISON_RE.search(question or ""):
            summary = str(ei_contract.get("summary") or "").strip()
            why = list(ei_contract.get("why") or [])
            return {
                "ok": True,
                "version": KUL_VERSION,
                "programme": PROGRAMME,
                "engine": "entity_intelligence_gate",
                "answerable": bool(summary),
                "fabricated": False,
                "summary": summary,
                "why": why,
                "evidence": [],
                "coverage": {"knowledge_sources_used": ["entity_intelligence"]},
                "company_intelligence": {
                    "identity": {
                        "ticker": None,
                        "name": ei_contract.get("canonical_name"),
                    }
                },
                "diagnostics": {
                    "entity_intelligence": {
                        "state": ei_contract.get("state"),
                        "confidence": ei_contract.get("confidence"),
                        "allow_planner": False,
                        "ticker": ei_contract.get("ticker"),
                    },
                    "providers_consulted": [],
                    "plan": {"provider_ids": []},
                },
                "entity_intelligence": ei_contract,
            }
    except Exception:
        ei_contract = {}

    query = plan_query(question)
    if ticker and not query.ticker_hint:
        # Never accept a caller ticker that Entity Intelligence forbids.
        try:
            from entity_intelligence.production import validate_bound_ticker

            if ei_contract and not validate_bound_ticker(ei_contract, ticker):
                ticker = None
        except Exception:
            pass
    if ticker and not query.ticker_hint:
        query.ticker_hint = str(ticker).upper()
        if "company" not in query.question_types:
            query.question_types = ["company", *query.question_types]

    reg = get_registry()
    kplan = build_knowledge_plan(query, registry=reg)

    results: list[ProviderResult] = []
    for pid in kplan.provider_ids[:max_providers]:
        provider = reg.get(pid)
        if not provider:
            continue
        try:
            results.append(provider.consult(query))
        except Exception as exc:  # pragma: no cover — provider wrappers already catch
            from knowledge_unification.providers.base import error_result
            import time

            results.append(error_result(pid, time.perf_counter(), exc))

    ranked = rank_and_filter(results)
    fused: FusedEvidence = fuse(kplan, ranked, results)
    payload = fused.to_dict()
    payload.update(
        {
            "ok": bool(ranked),
            "version": KUL_VERSION,
            "programme": PROGRAMME,
            "engine": "knowledge_unification",
            "answerable": bool(ranked) and bool(fused.summary),
            "fabricated": False,
        }
    )
    return payload


def soft_slice_for_ask_agi(
    question: str = "",
    *_args: Any,
    ticker: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Ask-facing soft slice — runs KUL and returns fusion + coverage."""
    return plan_and_gather(question, ticker=ticker)


_HARD_PROVIDERS = frozenset(
    {
        "research_intelligence",
        "research_intelligence_engine",
        "forecast_intelligence_engine",
        "macro_intelligence_engine",
        "unified_valuation_engine",
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "valuation_policy_engine",
        "market_intelligence_engine",
        "historical_intelligence",
        "institutional_warehouse",
        "portfolio_intelligence",
        "investment_intelligence",
        "industry_intelligence",
        "business_intelligence",
        "valuation_consensus",
        "valuation_terminal",
        "hedge_fund_screens",
        "financial_statement_warehouse",
        "capiq_ikt",
        "company_memory",
        "ikl",
        "knowledge_factory",
        "cgl",
        "financial_concepts",
        "financial_foundations",
        "financial_statement_intelligence",
    }
)


def answer_for_ask(question: str, *, ticker: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Compact Ask short-circuit payload via Universal Knowledge Orchestration.

    Phase 6.0 — every short-circuit uses the same gather as the full desk path.
    Soft-only academy/legacy hits still must not short-circuit Ask.
    """
    # Exact market-consensus questions are database lookups, not synthesis
    # prompts.  UKO deliberately blends useful company context, but that can
    # displace the requested numeric fact with a general business summary.
    # Preserve the KUL consensus provider as the authoritative answer here.
    if _EXACT_CONSENSUS_RE.search(question or ""):
        gathered = plan_and_gather(question, ticker=ticker)
        coverage = gathered.get("coverage") if isinstance(gathered.get("coverage"), dict) else {}
        sources = list(coverage.get("knowledge_sources_used") or [])
        company = gathered.get("company_intelligence")
        company = company if isinstance(company, dict) else {}
        identity = company.get("identity") if isinstance(company.get("identity"), dict) else {}
        gathered_summary = str(gathered.get("summary") or "")
        summary_is_company_consensus = bool(
            re.search(
                r"\b(capital iq market consensus|capital iq consensus (?:high|low) target|"
                r"analysts contribute to the capital iq consensus)\b",
                gathered_summary,
                re.I,
            )
        )
        if (
            gathered.get("answerable")
            and "valuation_consensus" in sources
            and summary_is_company_consensus
        ):
            return {
                "summary": gathered.get("summary") or "",
                "why": list(gathered.get("why") or []),
                "evidence": list(gathered.get("evidence") or []),
                "engine": "knowledge_unification",
                "key": identity.get("ticker") or ticker,
                "company_name": identity.get("name"),
                "coverage": coverage,
                "company_intelligence": company,
                "concept_intelligence": gathered.get("concept_intelligence") or {},
                "diagnostics": gathered.get("diagnostics") or {},
                "providers_used": sources,
                "exact_fact": True,
            }
        name = ticker
        if ticker:
            try:
                from company_identity.service import identity_for

                identity = identity_for(ticker)
                name = identity.company_name if identity.resolved else ticker
            except Exception:
                name = ticker
        unavailable = (
            f"No Capital IQ market-consensus record is available for {name or 'this company'} "
            "in the current database export. AGI will not substitute a company profile or "
            "invent a target price."
        )
        return {
            "summary": unavailable,
            "why": [
                "The valuation-consensus provider returned no usable row for the verified entity.",
                "Refresh or import the latest consensus dataset before using this field.",
            ],
            "evidence": [],
            "engine": "knowledge_unification",
            "key": ticker,
            "company_name": name,
            "coverage": {
                "knowledge_sources_used": ["valuation_consensus"],
                "missing_information": ["market_consensus_record"],
                "confidence": 100.0,
            },
            "company_intelligence": {
                "identity": {"ticker": ticker, "name": name},
            },
            "concept_intelligence": {},
            "diagnostics": gathered.get("diagnostics") or {},
            "providers_used": ["valuation_consensus"],
            "exact_fact": True,
            "insufficient_evidence": True,
        }

    try:
        from universal_knowledge.production import for_ask as uko_for_ask

        out = uko_for_ask(question, ticker=ticker)
    except Exception:
        out = None
        # Fall back to legacy KUL gather if UKO is unavailable.
        gathered = plan_and_gather(question, ticker=ticker)
        if gathered.get("answerable"):
            coverage = gathered.get("coverage") if isinstance(gathered.get("coverage"), dict) else {}
            sources = list(coverage.get("knowledge_sources_used") or [])
            company = gathered.get("company_intelligence")
            company = company if isinstance(company, dict) else {}
            identity = company.get("identity") if isinstance(company.get("identity"), dict) else {}
            concept = gathered.get("concept_intelligence")
            concept = concept if isinstance(concept, dict) else {}
            if sources and any(s in _HARD_PROVIDERS for s in sources):
                out = {
                    "summary": gathered.get("summary") or "",
                    "why": list(gathered.get("why") or []),
                    "evidence": list(gathered.get("evidence") or []),
                    "engine": "knowledge_unification",
                    "key": identity.get("ticker"),
                    "company_name": identity.get("name"),
                    "coverage": coverage,
                    "company_intelligence": company,
                    "concept_intelligence": concept,
                    "diagnostics": gathered.get("diagnostics") if isinstance(gathered.get("diagnostics"), dict) else {},
                    "providers_used": sources,
                }
    if not out:
        return None
    sources = list(out.get("providers_used") or (out.get("coverage") or {}).get("knowledge_sources_used") or [])
    if not sources:
        return None
    if not any(s in _HARD_PROVIDERS for s in sources):
        return None
    # Preserve KUL engine label for downstream short-circuit gates that key on it,
    # while recording that UKO produced the gather.
    out = dict(out)
    out.setdefault("engine", "knowledge_unification")
    out["uko"] = True
    out["providers_used"] = sources
    try:
        from ask_product_quality.production import enrich_answer

        out = enrich_answer(out, question=question)
    except Exception:
        pass
    return out
