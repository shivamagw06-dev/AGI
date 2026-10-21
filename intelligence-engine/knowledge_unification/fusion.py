"""Module 5 + 11 — Evidence Fusion and Unified Coverage Object."""

from __future__ import annotations

import re
from typing import Any

from knowledge_unification.company_object import build_company_intelligence
from knowledge_unification.schema import (
    CoverageObject,
    FusedEvidence,
    KnowledgePlan,
    ProviderResult,
)


def _concept_intelligence(
    results: list[ProviderResult],
    *,
    question_types: list[str] | None = None,
) -> dict[str, Any]:
    qtypes = set(question_types or [])
    if qtypes.intersection({"accounting", "financial_statement"}):
        order = (
            "financial_statement_intelligence",
            "financial_foundations",
            "financial_concepts",
        )
    else:
        order = (
            "financial_concepts",
            "financial_foundations",
            "financial_statement_intelligence",
        )
    by_id = {r.provider_id: r for r in results if not r.empty}
    for pid in order:
        r = by_id.get(pid)
        if not r:
            continue
        key = next(
            (f.get("value") for f in r.facts if f.get("field") in {"concept_key", "key"}),
            None,
        )
        return {
            "provider": r.provider_id,
            "summary": r.summary,
            "why": r.why,
            "key": key,
            "raw_keys": list((r.raw or {}).keys())[:20],
        }
    return {}


def _coverage(results: list[ProviderResult], used: list[ProviderResult]) -> CoverageObject:
    sources = [r.provider_id for r in used]
    conf = max((r.confidence for r in used), default=0.0)
    if len(used) >= 3 and conf >= 0.75:
        level, strength = "high", "strong"
    elif len(used) >= 1 and conf >= 0.6:
        level, strength = "medium", "moderate"
    elif used:
        level, strength = "low", "weak"
    else:
        level, strength = "none", "none"

    missing = []
    ids = set(sources)
    if "capiq_ikt" not in ids and any(r.provider_id == "capiq_ikt" and r.empty for r in results):
        missing.append("CapIQ company profile unavailable for this entity")
    if "business_intelligence" not in ids and any(
        r.provider_id == "business_intelligence" and r.empty for r in results
    ):
        missing.append("Business Intelligence foundation returned empty")
    if "industry_intelligence" not in ids and any(
        r.provider_id == "industry_intelligence" and r.empty for r in results
    ):
        missing.append("Industry Intelligence DNA returned empty")
    if "company_memory" not in ids and any(r.provider_id == "company_memory" for r in results):
        missing.append("Company memory not populated")
    if "ikl" not in ids and any(r.provider_id == "ikl" for r in results):
        missing.append("IKL memory miss")
    if "cgl" not in ids and any(r.provider_id == "cgl" for r in results):
        missing.append("No Continuous Gather extracts matched")

    return CoverageObject(
        coverage_level=level,
        knowledge_sources_used=sources,
        confidence=round(conf * 100.0, 1),
        evidence_strength=strength,
        missing_information=missing,
    )


_GENERIC_TEMPLATE_RE = re.compile(
    # "For banks, enterprise value is primarily driven by …"
    r"^\s*for [a-z0-9_ /&+-]{2,40}, enterprise value is primarily driven by|"
    r"^\s*for unknown,|"
    r"^\s*for commodity,|"
    r"^\s*unknown structure|"
    r"business type:\s*unknown|"
    r"based on retrieved evidence for the subject|"
    r"indian stock market q&a|"
    # "Banks economics: revenue from …" — an industry card, not a company answer.
    r"^\s*[a-z][a-z /&+-]{2,30} economics:\s|"
    r"^\s*industry dna:",
    re.I,
)

_RESEARCH_SHAPED_RE = re.compile(
    r"\b(annual report|earnings call|transcript|management (?:said|commentary)|"
    r"guidance|capital allocation|what changed since|research memory|investor presentation)\b",
    re.I,
)


def _is_generic_template(text: str | None) -> bool:
    """True for industry-template leads that say nothing company-specific."""
    return bool(_GENERIC_TEMPLATE_RE.search(str(text or "").strip()))


_GENERIC_NAME_WORDS = frozenset(
    {"limited", "ltd", "the", "and", "of", "india", "indian", "corporation", "company",
     "bank", "industries", "enterprise", "enterprises", "group", "holdings", "services"}
)


def _company_terms(plan: KnowledgePlan) -> list[str]:
    """Distinctive tokens of the bound company, for 'is this answer about it?'.

    Industry words are excluded: "cement" appears in both UltraTech Cement and
    in every cement industry template, so it cannot prove company specificity.
    """
    raw = " ".join(
        str(x or "")
        for x in (
            getattr(plan.query, "company_hint", None),
            getattr(plan.query, "ticker_hint", None),
        )
    )
    industry_words: set[str] = set()
    ticker = getattr(plan.query, "ticker_hint", None)
    if ticker:
        try:
            from company_identity.service import identity_for

            identity = identity_for(ticker)
            if identity.resolved:
                industry_words = {
                    w
                    for w in re.split(
                        r"[^A-Za-z]+",
                        f"{identity.primary_industry or ''} {identity.primary_sector or ''}".lower(),
                    )
                    if len(w) > 2
                }
        except Exception:
            industry_words = set()
    terms = [
        t
        for t in re.split(r"[^A-Za-z0-9]+", raw.lower())
        if len(t) > 2 and t not in _GENERIC_NAME_WORDS and t not in industry_words
    ]
    return list(dict.fromkeys(terms))


_OBJECTIVE_LEADS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    # Explicit CapIQ consensus questions only — never for valuation / IC / forecast.
    (
        re.compile(
            r"\b(consensus target|target price|price target|high target|low target|"
            r"analysts? cover|rating split|broker (?:estimate|consensus|recommendation))\b",
            re.I,
        ),
        ("valuation_consensus",),
    ),
    (
        re.compile(
            r"\b(annual report|earnings call|transcript|guidance|management (?:said|commentary)|"
            r"investment committee|institutional equity analyst|as if you were)\b",
            re.I,
        ),
        ("research_intelligence_engine", "research_intelligence", "forecast_intelligence_engine"),
    ),
    (
        re.compile(
            r"\b(expensive|cheap|overvalued|undervalued|valuation|multiple|"
            r"p/?e\b|p/?b\b|ev/?ebitda|price to (?:earnings|book|sales)|"
            r"trades? at|re-?rat(?:e|ing)|de-?rat(?:e|ing)|discount|premium|"
            r"own history|similar to today)\b",
            re.I,
        ),
        (
            "historical_valuation_intelligence",
            "unified_valuation_engine",
            "valuation_attribution_engine",
            "valuation_policy_engine",
            "valuation_terminal",
            "industry_intelligence",
        ),
    ),
    (
        re.compile(
            r"\b(screen|scanner|hedge fund|long/?short|market neutral|pair trade|"
            r"value trap|momentum|quality screen|compounders?)\b",
            re.I,
        ),
        ("hedge_fund_screens", "unified_valuation_engine", "investment_intelligence"),
    ),
    (
        re.compile(
            r"\b(forecast|outlook|bull case|bear case|base case|next 3)\b",
            re.I,
        ),
        ("forecast_intelligence_engine", "research_intelligence_engine", "macro_intelligence_engine"),
    ),
    (
        re.compile(
            r"\b(macro|rbi|rate cut|basis point|sector rotation|market breadth)\b",
            re.I,
        ),
        ("macro_intelligence_engine", "market_intelligence_engine", "forecast_intelligence_engine"),
    ),
    (
        re.compile(
            r"\b(investment thesis|why (?:would|should).{0,20}own|thesis|catalysts?|"
            r"biggest risks?|business and financial quality)\b",
            re.I,
        ),
        ("research_intelligence_engine", "investment_intelligence", "business_intelligence"),
    ),
    (
        re.compile(r"\b(business model|what does .+ do|explain|moat|competes?|unit economics)\b", re.I),
        ("business_intelligence", "research_intelligence_engine", "company_memory"),
    ),
)


def _objective_lead_order(plan: KnowledgePlan) -> tuple[str, ...]:
    """Providers that should lead, given what the question actually asks for."""
    question = getattr(plan.query, "question", None) or ""
    for pattern, providers in _OBJECTIVE_LEADS:
        if pattern.search(question):
            return providers
    return ()


def _mentions_company(text: str | None, terms: list[str]) -> bool:
    low = str(text or "").lower()
    return any(t in low for t in terms)


def _is_research_shaped(plan: KnowledgePlan) -> bool:
    question = getattr(plan.query, "question", None) or ""
    return bool(_RESEARCH_SHAPED_RE.search(question))


def fuse(
    plan: KnowledgePlan,
    ranked: list[ProviderResult],
    all_results: list[ProviderResult],
) -> FusedEvidence:
    used = ranked
    company = build_company_intelligence(plan.query, used)
    concept = _concept_intelligence(used, question_types=plan.query.question_types)
    coverage = _coverage(all_results, used)

    # Lead summary: company → FSA/foundations → concepts → soft sources.
    # Prefer statement/foundations over concepts when both contributed so
    # interpretive accounting answers aren't overwritten by a concept card.
    qtypes = set(plan.query.question_types or [])
    if "consensus" in qtypes:
        # Sell-side consensus questions must be answered from CapIQ market data,
        # not from AGI pedagogy that happens to mention valuation.
        preferred_order = (
            "valuation_consensus",
            "capiq_ikt",
            "investment_intelligence",
            "business_intelligence",
            "company_memory",
            "industry_intelligence",
            "ikl",
            "knowledge_factory",
            "cgl",
            "financial_concepts",
            "academy",
            "legacy_kip",
        )
    elif qtypes.intersection({"financial_statement", "accounting"}):
        preferred_order = (
            "financial_statement_intelligence",
            "financial_foundations",
            "financial_concepts",
            "capiq_ikt",
            "academy",
            "legacy_kip",
        )
    elif "research" in qtypes or any(
        r.provider_id == "research_intelligence" and not r.empty for r in used
    ) or any(
        k in ((getattr(plan.query, "question", None) or "").lower())
        for k in (
            "annual report",
            "earnings call",
            "transcript",
            "research memory",
            "deep research",
            "cross-document",
            "guidance history",
            "research timeline",
            "what changed since",
            "five years of",
            "from the annual report",
        )
    ):
        # Phase 3.4.5 — Research Intelligence leads research-shaped answers.
        preferred_order = (
            "research_intelligence",
            "investment_intelligence",
            "business_intelligence",
            "industry_intelligence",
            "capiq_ikt",
            "company_memory",
            "ikl",
            "knowledge_factory",
            "cgl",
            "financial_concepts",
            "academy",
            "legacy_kip",
        )
    elif "portfolio" in qtypes or any(
        r.provider_id == "portfolio_intelligence" and not r.empty for r in used
    ) or any(
        k in ((getattr(plan.query, "question", None) or "").lower())
        for k in (
            "portfolio construction",
            "portfolio quality",
            "risk budget",
            "factor exposure",
            "position sizing",
            "agib core",
            "concentrated growth",
        )
    ):
        preferred_order = (
            "portfolio_intelligence",
            "investment_intelligence",
            "business_intelligence",
            "industry_intelligence",
            "capiq_ikt",
            "company_memory",
            "ikl",
            "knowledge_factory",
            "cgl",
            "financial_concepts",
            "academy",
            "legacy_kip",
        )
    elif "investment" in qtypes or any(
        r.provider_id == "investment_intelligence" and not r.empty for r in used
    ) or any(
        k in ((getattr(plan.query, "question", None) or "").lower())
        for k in (
            "investment thesis",
            "catalyst",
            "scenario analysis",
            "bull and bear",
            "investors monitor",
            "for an investor",
            "monitoring priorit",
            "evidence strength",
            "from an investment",
            "investment quality",
            "investment committee",
            "what drives valuation",
            "valuation driver",
            "quality perspective",
            "business quality",
            "unknowns remain",
            "capital allocation",
        )
    ):
        # Phase 3.2.5 — Investment Intelligence leads investment-shaped answers.
        preferred_order = (
            "investment_intelligence",
            "business_intelligence",
            "industry_intelligence",
            "valuation_consensus",
            "capiq_ikt",
            "company_memory",
            "ikl",
            "knowledge_factory",
            "cgl",
            "financial_concepts",
            "academy",
            "legacy_kip",
        )
    elif qtypes.intersection(
        {"business_model", "moat", "unit_economics", "comparison", "business_risk", "industry"}
    ):
        # Company-less moat pedagogy ("Explain network effects") should lead with
        # financial_concepts, not a synthetic company moat card from BI.
        company_bound = bool(
            getattr(plan.query, "ticker_hint", None)
            or getattr(plan.query, "company_hint", None)
            or "comparison" in qtypes
            or "company" in qtypes
        )
        qtext = (getattr(plan.query, "question", None) or "").lower()
        concept_moat_pedagogy = (not company_bound) and any(
            k in qtext
            for k in (
                "network effect",
                "pricing power",
                "competitive moat",
                "what is a moat",
                "explain moat",
                "what creates pricing",
            )
        )
        industry_lead = (not company_bound) and (
            "industry" in qtypes
            or "unit_economics" in qtypes
            or "business_risk" in qtypes
            or any(
                k in qtext
                for k in (
                    "nim",
                    "casa",
                    "arpob",
                    "load factor",
                    "ev/sales",
                    "p/b",
                    "embedded value",
                    "porter",
                    "oligopol",
                    "spectrum",
                    "industry economics",
                )
            )
        )
        if concept_moat_pedagogy:
            preferred_order = (
                "financial_concepts",
                "business_intelligence",
                "industry_intelligence",
                "capiq_ikt",
                "academy",
                "legacy_kip",
            )
        elif industry_lead:
            # Phase 3.1.5 — Industry DNA leads pure industry pedagogy.
            preferred_order = (
                "industry_intelligence",
                "business_intelligence",
                "financial_concepts",
                "knowledge_factory",
                "capiq_ikt",
                "academy",
                "legacy_kip",
            )
        else:
            preferred_order = (
                "business_intelligence",
                "industry_intelligence",
                "investment_intelligence",
                "capiq_ikt",
                "company_memory",
                "ikl",
                "knowledge_factory",
                "cgl",
                "financial_concepts",
                "academy",
                "legacy_kip",
            )
    elif qtypes.intersection({"valuation"}) and not (
        getattr(plan.query, "ticker_hint", None) or getattr(plan.query, "company_hint", None)
    ):
        preferred_order = (
            "industry_intelligence",
            "financial_concepts",
            "business_intelligence",
            "academy",
            "legacy_kip",
        )
    elif qtypes.intersection({"company", "market"}):
        preferred_order = (
            "capiq_ikt",
            "company_memory",
            "business_intelligence",
            "industry_intelligence",
            "ikl",
            "knowledge_factory",
            "cgl",
            "financial_concepts",
            "academy",
            "legacy_kip",
        )
    else:
        preferred_order = (
            "financial_concepts",
            "financial_foundations",
            "financial_statement_intelligence",
            "industry_intelligence",
            "capiq_ikt",
            "academy",
            "knowledge_factory",
            "company_memory",
            "ikl",
            "cgl",
            "legacy_kip",
        )
    # The question's objective decides who leads: a consensus question is led
    # by consensus, a research question by research, a thesis by investment.
    lead_order = _objective_lead_order(plan) + preferred_order
    company_terms = _company_terms(plan)

    def _acceptable(result: ProviderResult) -> bool:
        if not result.summary:
            return False
        if _is_generic_template(result.summary):
            return False
        if company_terms and not _mentions_company(result.summary, company_terms):
            return False
        return True

    summary = ""
    lead_provider: str | None = None
    for preferred in lead_order:
        match = next((r for r in used if r.provider_id == preferred and _acceptable(r)), None)
        if match:
            summary = match.summary
            lead_provider = match.provider_id
            break
    if not summary:
        # Nothing company-specific — fall back to the ranked order, still
        # preferring anything over a bare industry template.
        for preferred in lead_order:
            match = next(
                (
                    r
                    for r in used
                    if r.provider_id == preferred
                    and r.summary
                    and not _is_generic_template(r.summary)
                ),
                None,
            )
            if match:
                summary = match.summary
                lead_provider = match.provider_id
                break
    if not summary and used:
        summary = used[0].summary
        lead_provider = used[0].provider_id

    # A research question with no research behind it must say so rather than
    # fall back to a generic company or industry line.
    if _is_research_shaped(plan) and not any(
        r.provider_id == "research_intelligence" and not r.empty for r in used
    ):
        company = (
            getattr(plan.query, "company_hint", None)
            or getattr(plan.query, "ticker_hint", None)
            or "this company"
        )
        summary = (
            f"No annual report, transcript or management commentary for {company} is in "
            "research memory yet, so there is nothing to quote. "
            + (summary if summary and not _is_generic_template(summary) else "")
        ).strip()

    why: list[str] = []
    evidence: list[dict[str, Any]] = []
    seen_why: set[str] = set()
    hard_ids = {
        "financial_foundations",
        "financial_statement_intelligence",
        "financial_concepts",
        "research_intelligence",
        "portfolio_intelligence",
        "investment_intelligence",
        "industry_intelligence",
        "business_intelligence",
        "capiq_ikt",
    }
    soft_ids = {"academy", "legacy_kip", "cgl", "ikl", "knowledge_factory", "company_memory"}
    has_hard = any(r.provider_id in hard_ids for r in used)

    def _append_why(line: str, *, max_len: int = 280) -> None:
        norm = " ".join((line or "").split()).strip()
        if not norm or norm in seen_why:
            return
        if len(norm) > max_len:
            norm = norm[: max_len - 1].rstrip() + "…"
        seen_why.add(norm)
        why.append(norm)

    # The provider that answered leads the reasoning too — otherwise a company
    # thesis is followed by someone else's industry notes.
    ordered_used = sorted(used, key=lambda r: 0 if r.provider_id == lead_provider else 1)

    # Prefer hard-provider why; soft academy/book lines only fill gaps and stay short.
    for r in ordered_used:
        if r.provider_id in soft_ids and has_hard:
            continue
        for line in r.why:
            _append_why(line)
            if len(why) >= 6:
                break
        if len(why) >= 6:
            break
    if len(why) < 3:
        for r in used:
            if r.provider_id not in soft_ids:
                continue
            for line in r.why[:1]:
                _append_why(line, max_len=160)
            if len(why) >= 4:
                break
    for r in used:
        for ev in r.evidence:
            if ev and ev not in evidence:
                evidence.append(ev)

    # Canonical Company Identity outranks every engine. Any line carrying
    # another industry's exclusive vocabulary is dropped rather than shown.
    identity_context: dict[str, Any] = {}
    classification_guard: dict[str, Any] = {}
    try:
        from company_identity.guard import filter_leaked_lines, validate_text
        from company_identity.service import resolve as resolve_identity

        identity = resolve_identity(plan.query.ticker_hint or plan.query.company_hint or "")
        if not identity.resolved:
            # A company named in the question still owns the classification even
            # when the planner declined to bind a ticker.
            from company_identity.service import resolve_company_mention

            mentioned, _how = resolve_company_mention(getattr(plan.query, "question", ""))
            if mentioned:
                identity = resolve_identity(mentioned)
        if identity.resolved:
            identity_context = identity.context()
            why, dropped = filter_leaked_lines(identity, why)
            summary_report = validate_text(identity, summary, where="summary")
            if not summary_report.ok:
                replacement = next((line for line in why if line), "")
                dropped.append(
                    {
                        "line": str(summary)[:220],
                        "violations": [v.rule for v in summary_report.violations],
                        "field": "summary",
                    }
                )
                summary = replacement or (
                    f"{identity.company_name} is classified by Capital IQ as "
                    f"{identity.primary_sector} / {identity.primary_industry} "
                    f"({identity.business_type})."
                )
            classification_guard = {
                "identity": identity_context,
                "source": identity.source,
                "dropped_lines": dropped,
                "clean": not dropped,
            }
    except Exception as exc:  # never block an answer on the guard
        classification_guard = {"error": f"{type(exc).__name__}:{str(exc)[:120]}"}

    # Provider names are internal plumbing — they belong in diagnostics, not in
    # an institutional answer. (Previously prepended as "Sources fused: …".)
    why = why[:7]

    diagnostics = {
        "company_identity": identity_context,
        "classification_guard": classification_guard,
        "plan": plan.to_dict(),
        "providers_consulted": [r.provider_id for r in all_results],
        "providers_used": [r.provider_id for r in used],
        "providers_rejected": [
            {"id": r.provider_id, "reason": r.rejected_reason or ("error" if not r.ok else "unused")}
            for r in all_results
            if r.empty or not r.ok or r.rejected_reason
        ],
        "provider_latency_ms": {r.provider_id: r.latency_ms for r in all_results},
        "provider_contribution": {
            r.provider_id: {
                "confidence": r.confidence,
                "fact_count": len(r.facts),
                "why_count": len(r.why),
            }
            for r in used
        },
    }

    return FusedEvidence(
        summary=summary or "Insufficient unified knowledge for this question.",
        why=why,
        evidence=evidence,
        company_intelligence=company,
        concept_intelligence=concept,
        coverage=coverage,
        provider_results=all_results,
        diagnostics=diagnostics,
    )
