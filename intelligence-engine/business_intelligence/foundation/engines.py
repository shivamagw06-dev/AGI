"""Deterministic BI engines — business model, moat, industry, growth, risks, lifecycle, unit econ, management."""

from __future__ import annotations

import re
from typing import Any

from business_intelligence.foundation.industry_drivers import template_for
from business_intelligence.foundation.named_pedagogy import lookup_named_pedagogy
from business_intelligence.foundation.schema import (
    MOAT_DIMENSIONS,
    RISK_TYPES,
    GROWTH_MODES,
    LIFECYCLE_STAGES,
    BusinessModelCard,
    MoatCard,
    IndustryCard,
    ScoredDimension,
)
from business_intelligence.foundation.taxonomy import business_type_for_industry


def _blob(*parts: Any) -> str:
    return " ".join(str(p).lower() for p in parts if p)


_DISPLAY_NAMES = {
    "ASIANPAINT": "Asian Paints",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "INFY": "Infosys",
    "RELIANCE": "Reliance Industries",
    "TATAMOTORS": "Tata Motors",
    "TCS": "TCS",
}


def _company_display_name(ev: dict[str, Any], fallback: str = "The company") -> str:
    company = ev.get("company") or {}
    ticker = str(ev.get("ticker") or company.get("ticker") or "").upper()
    company_name = str(company.get("company_name") or "").strip()
    if ticker and company_name.upper().replace(" ", "") == ticker.replace(" ", ""):
        company_name = ""
    return str(
        company.get("display_name")
        or company_name
        or _DISPLAY_NAMES.get(ticker)
        or ticker
        or fallback
    )


def _pedagogy_for_ev(ev: dict[str, Any]) -> dict[str, Any] | None:
    company = ev.get("company") or {}
    return lookup_named_pedagogy(
        name=company.get("display_name") or company.get("company_name"),
        ticker=ev.get("ticker") or company.get("ticker"),
        question=ev.get("question"),
    )


def _score_rating(score: int) -> str:
    if score >= 70:
        return "Strong"
    if score >= 40:
        return "Medium"
    if score > 0:
        return "Weak"
    return "Unknown"


def analyse_business_model(ev: dict[str, Any]) -> dict[str, Any]:
    ped = _pedagogy_for_ev(ev)
    industry = (ped or {}).get("industry_key") or ev.get("industry_key") or "unknown"
    tmpl = template_for(industry)
    company = ev.get("company") or {}
    name = (
        company.get("display_name")
        or company.get("company_name")
        or ev.get("ticker")
        or "The company"
    )
    desc = str(company.get("description") or "")
    products = company.get("products")
    segments = company.get("business_segments") or (ped or {}).get("segments")
    btype = (ped or {}).get("business_type") or business_type_for_industry(industry)
    unknown_model = (
        not ped
        and not desc
        and not products
        and not segments
        and (industry == "unknown" or btype == "unknown" or name == "The company")
    )

    revenue_streams: list[str] = []
    if products:
        revenue_streams.append(f"Products/services: {str(products)[:180]}")
    if segments:
        if isinstance(segments, list):
            revenue_streams.append("Segments: " + "; ".join(str(s) for s in segments[:6]))
        else:
            revenue_streams.append(f"Segments: {str(segments)[:180]}")
    if not revenue_streams and desc and not ped:
        # First sentence as revenue narrative, not fabrication of numbers.
        revenue_streams.append(re.split(r"(?<=[.!?])\s+", desc.strip())[0][:220])
    if not revenue_streams:
        revenue_streams = (
            ["No verified revenue streams are available."]
            if unknown_model
            else [f"Core {industry.replace('_', ' ')} franchise revenue"]
        )

    # Named pedagogy wins over thin CapIQ blurbs for conglomerates / globals.
    if ped and ped.get("how_it_makes_money"):
        how = str(ped["how_it_makes_money"])
    else:
        how = desc.strip()
        if how:
            how = " ".join(re.split(r"(?<=[.!?])\s+", how)[:2])
        elif unknown_model:
            how = (
                "No verified company identity or business-model evidence is available. "
                "Clarification is required before describing how this company makes money."
            )
        else:
            how = (
                f"{name} operates a {btype.replace('_', ' ')} economic engine in "
                f"{industry.replace('_', ' ')}, monetising its core franchise."
            )

    customers = []
    if company.get("customers"):
        customers.append(str(company["customers"])[:200])
    if not customers:
        customers = (
            ["No verified customer segments are available."]
            if unknown_model
            else ["Core franchise customers in the primary industry"]
        )

    channels = []
    blob = _blob(desc, products, segments)
    if any(k in blob for k in ("branch", "store", "retail")):
        channels.append("Physical distribution / branches / stores")
    if any(k in blob for k in ("online", "digital", "app", "platform")):
        channels.append("Digital / online channels")
    if any(k in blob for k in ("dealer", "distributor", "channel partner")):
        channels.append("Dealer / distributor network")
    if not channels:
        channels = (
            ["No verified distribution channels are available."]
            if unknown_model
            else ["Primary industry distribution channels"]
        )

    cost_structure = [
        "Cost of delivering the core product/service",
        "Operating and distribution cost base",
        "Growth / acquisition investment",
    ]
    fixed_vs_variable = {
        "fixed": "Franchise, plant, network, or platform fixed costs",
        "variable": "Volume-linked inputs, commissions, or credit/variable delivery costs",
    }
    unit_economics_summary = " -> ".join(tmpl["unit_econ_chain"])
    recurring_vs_one_time = (
        "High recurring character"
        if any(k in blob for k in ("deposit", "subscription", "recurring", "premium", "retainer"))
        or industry in {"banks", "saas", "insurance", "subscription", "utility"}
        else "Mix of recurring and transactional revenue"
    )
    capital_intensity = str(tmpl["capital_intensity"])
    working_capital_profile = str(tmpl["working_capital"])
    operating_leverage = str(tmpl["operating_leverage"])
    pricing_model = str(tmpl["pricing_model"])
    confidence = 0.88 if desc else 0.62
    if unknown_model:
        cost_structure = ["No verified cost structure is available."]
        fixed_vs_variable = {"fixed": "Unknown", "variable": "Unknown"}
        unit_economics_summary = "No verified unit economics are available."
        recurring_vs_one_time = "Unknown pending verified business-model evidence"
        capital_intensity = "Unknown"
        working_capital_profile = "Unknown"
        operating_leverage = "Unknown"
        pricing_model = "Unknown"
        confidence = 0.0

    card = BusinessModelCard(
        business_type=btype,
        how_it_makes_money=how[:600],
        revenue_streams=revenue_streams[:6],
        customer_segments=customers[:4],
        distribution_channels=channels[:4],
        cost_structure=cost_structure,
        fixed_vs_variable=fixed_vs_variable,
        unit_economics_summary=unit_economics_summary,
        recurring_vs_one_time=recurring_vs_one_time,
        capital_intensity=capital_intensity,
        working_capital_profile=working_capital_profile,
        operating_leverage=operating_leverage,
        pricing_model=pricing_model,
        confidence=confidence,
        evidence=list(ev.get("evidence") or [])[:6],
    )
    return card.to_dict()


def analyse_value_drivers(ev: dict[str, Any]) -> dict[str, Any]:
    industry = ev.get("industry_key") or "unknown"
    tmpl = template_for(industry)
    drivers = list(tmpl["value_drivers"])
    q = (ev.get("question") or "").lower()
    if "capital intensity" in q:
        summary = f"Capital intensity for {industry.replace('_', ' ')}: {tmpl['capital_intensity']}."
    elif "working capital" in q:
        summary = f"Working capital profile for {industry.replace('_', ' ')}: {tmpl['working_capital']}."
    elif "operating leverage" in q:
        summary = f"Operating leverage for {industry.replace('_', ' ')}: {tmpl['operating_leverage']}."
    else:
        summary = (
            f"For {industry.replace('_', ' ')}, enterprise value is primarily driven by "
            + ", ".join(drivers[:4])
            + "."
        )
    return {
        "industry": industry,
        "value_drivers": drivers,
        "capital_intensity": tmpl["capital_intensity"],
        "working_capital_profile": tmpl["working_capital"],
        "operating_leverage": tmpl["operating_leverage"],
        "summary": summary,
        "why": [
            f"{d} is a first-order driver of returns and cash generation in this industry."
            for d in drivers[:5]
        ],
        "confidence": 0.9 if industry != "unknown" else 0.45,
        "fabricated": False,
    }


def analyse_unit_economics(ev: dict[str, Any]) -> dict[str, Any]:
    industry = ev.get("industry_key") or "unknown"
    tmpl = template_for(industry)
    chain = list(tmpl["unit_econ_chain"])
    return {
        "industry": industry,
        "chain": [
            {"step": i + 1, "name": step}
            for i, step in enumerate(
                ["Revenue", "Gross Profit", "Contribution Margin", "Operating Profit", "Free Cash Flow"]
            )
        ],
        "industry_chain": chain,
        "summary": (
            "Unit economics follow Revenue → Gross Profit → Contribution → Operating Profit → Free Cash Flow; "
            f"in {industry.replace('_', ' ')} that maps to: " + " → ".join(chain) + "."
        ),
        "capital_intensity": tmpl["capital_intensity"],
        "operating_leverage": tmpl["operating_leverage"],
        "confidence": 0.9 if industry != "unknown" else 0.5,
        "fabricated": False,
    }


_MOAT_HINTS: dict[str, tuple[str, ...]] = {
    "brand": ("brand", "franchise", "reputation", "trust"),
    "network_effects": ("network", "ecosystem", "platform", "two-sided"),
    "scale": ("scale", "market share", "largest", "capacity"),
    "switching_costs": ("switch", "retention", "sticky", "lock-in", "casa", "multi-year"),
    "cost_leadership": ("low-cost", "cost advantage", "lowest cost", "efficiency"),
    "technology": ("technology", "patent", "software", "data", "digital"),
    "licensing": ("license", "licence", "regulatory", "spectrum", "concession"),
    "distribution": ("distribution", "branch", "dealer", "channel", "reach"),
    "customer_lock_in": ("lock-in", "embedded", "workflow", "high switching"),
}


def analyse_moat(ev: dict[str, Any]) -> dict[str, Any]:
    industry = ev.get("industry_key") or "unknown"
    tmpl = template_for(industry)
    company = ev.get("company") or {}
    blob = _blob(
        company.get("description"),
        company.get("competitive_position"),
        company.get("products"),
        ev.get("question"),
    )
    typical = set(tmpl.get("typical_moats") or [])
    dims: list[ScoredDimension] = []
    for key in MOAT_DIMENSIONS:
        hints = _MOAT_HINTS.get(key, ())
        hits = sum(1 for h in hints if h in blob)
        score = min(95, hits * 28 + (25 if key in typical else 0) + (10 if company.get("description") else 0))
        if key in typical and not hits:
            score = max(score, 45)
        evidence = []
        if hits:
            evidence.append(f"Language evidence for {key.replace('_', ' ')} in company/industry context.")
        if key in typical:
            evidence.append(f"Structural {key.replace('_', ' ')} is typical for {industry.replace('_', ' ')}.")
        dims.append(
            ScoredDimension(
                key=key,
                score=score,
                rating=_score_rating(score),
                evidence=evidence,
                why=f"{key.replace('_', ' ').title()} scored {score}/100 on structural + textual evidence.",
            )
        )
    primary = [d.key for d in sorted(dims, key=lambda x: -x.score) if d.score >= 45][:4]
    if not primary and industry not in {"unknown", ""}:
        primary = [k for k in (tmpl.get("typical_moats") or []) if k][:3]
    durability = "Strong" if sum(1 for d in dims if d.score >= 70) >= 2 else (
        "Medium" if primary else "Weak"
    )
    name = _company_display_name(ev, fallback="")
    if not name:
        # Pull a proper noun from the question (Costco/Apple/TCS) for direct answers.
        q = str(ev.get("question") or "")
        m = re.search(
            r"\b(Costco|Apple|TCS|Infosys|HDFC Bank|Asian Paints|DMart|Visa|Mastercard|Ferrari|Toyota)\b",
            q,
            re.I,
        )
        name = m.group(1) if m else "The company"
    if industry == "retail" and "membership" in str(ev.get("question") or "").lower():
        summary = (
            f"{name}'s membership/retail moat is typically grounded in "
            + (", ".join(p.replace('_', ' ') for p in primary) if primary else "scale and brand")
            + f" (durability: {durability})."
        )
    else:
        summary = (
            f"{name}'s primary moat sources are "
            + (", ".join(p.replace('_', ' ') for p in primary) if primary else "not yet clearly established")
            + f" (durability: {durability})."
        )
    card = MoatCard(
        dimensions=dims,
        primary_moats=primary,
        durability=durability,
        summary=summary,
        confidence=0.82 if company.get("description") or industry != "unknown" else 0.5,
    )
    return card.to_dict()


def analyse_industry(ev: dict[str, Any]) -> dict[str, Any]:
    industry = ev.get("industry_key") or "unknown"
    tmpl = template_for(industry)
    porter = dict(tmpl["porter"])
    dna_note = ""
    if tmpl.get("from_industry_dna"):
        dna_note = f" (Industry DNA: {tmpl.get('industry_dna_key')})"
    card = IndustryCard(
        industry=industry,
        value_drivers=list(tmpl["value_drivers"]),
        porter=porter,
        concentration=str(tmpl["concentration"]),
        summary=(
            f"{industry.replace('_', ' ').title()} structure — concentration: {tmpl['concentration']}. "
            f"Rivalry: {porter.get('rivalry')}. Entry barriers: {porter.get('entry_barriers')}.{dna_note}"
        ),
        confidence=0.9 if tmpl.get("from_industry_dna") else (0.88 if industry != "unknown" else 0.4),
    )
    out = card.to_dict()
    out["from_industry_dna"] = bool(tmpl.get("from_industry_dna"))
    out["industry_dna_key"] = tmpl.get("industry_dna_key")
    return out


def analyse_growth(ev: dict[str, Any]) -> dict[str, Any]:
    industry = ev.get("industry_key") or "unknown"
    company = ev.get("company") or {}
    blob = _blob(company.get("description"), company.get("business_segments"), ev.get("question"))
    modes: dict[str, str] = {}
    keyword_map = {
        "organic": ("organic", "same-store", "volume growth"),
        "acquisition_led": ("acquisit", "m&a", "merged"),
        "pricing_led": ("pricing", "realization", "rate hike", "arpu"),
        "volume_led": ("volume", "throughput", "passenger", "utilization"),
        "mix_improvement": ("mix", "premiumisation", "upsell"),
        "geographic_expansion": ("geographic", "international", "new market", "state expansion"),
        "cross_selling": ("cross-sell", "cross sell", "attach"),
        "upselling": ("upsell", "expansion revenue", "nrr"),
        "capacity_expansion": ("capacity", "capex", "new plant", "beds", "fleet"),
        "market_share_gains": ("market share", "share gain"),
    }
    for mode in GROWTH_MODES:
        keys = keyword_map.get(mode, ())
        modes[mode] = "Evident" if any(k in blob for k in keys) else "Possible"
    # Industry priors
    if industry in {"saas", "marketplace", "subscription"}:
        modes["organic"] = "Primary"
        modes["upselling"] = "Primary"
    if industry in {"cement", "manufacturing", "utility", "hospitals"}:
        modes["capacity_expansion"] = "Primary"
    if industry == "banks":
        modes["cross_selling"] = "Primary"
        modes["organic"] = "Primary"
    primary = [m for m, v in modes.items() if v in {"Primary", "Evident"}][:5]
    name = _company_display_name(ev)
    return {
        "industry": industry,
        "modes": modes,
        "primary_modes": primary or ["organic"],
        "summary": f"Growth at {name} is primarily "
        + ", ".join((primary or ["organic"]))
        + f" for this {industry.replace('_', ' ')} franchise.",
        "confidence": 0.75,
        "fabricated": False,
    }


def analyse_management(ev: dict[str, Any]) -> dict[str, Any]:
    """Structured management lens — evidence-light without filings; no hallucination of people facts."""
    company = ev.get("company") or {}
    has_desc = bool(company.get("description"))
    axes = {
        "capital_allocation": {"rating": "Unknown", "note": "Requires capital history and ROIC vs WACC evidence."},
        "governance": {"rating": "Unknown", "note": "Requires board/related-party / ownership evidence."},
        "execution": {"rating": "Unknown", "note": "Requires delivery vs guidance track record."},
        "communication": {"rating": "Unknown", "note": "Requires filings/transcript consistency review."},
        "strategic_consistency": {"rating": "Medium" if has_desc else "Unknown", "note": "Inferred only at industry-strategy level without deep filings."},
        "shareholder_friendliness": {"rating": "Unknown", "note": "Requires dividend/buyback/dilution history."},
        "acquisition_history": {"rating": "Unknown", "note": "Requires disclosed M&A outcomes."},
        "return_discipline": {"rating": "Unknown", "note": "Requires ROIC/reinvestment evidence."},
    }
    return {
        "axes": axes,
        "summary": (
            "Management quality is scored only where evidence exists. "
            "Without filings-backed capital and governance history, AGI marks axes Unknown rather than inventing a narrative."
        ),
        "confidence": 0.55 if has_desc else 0.35,
        "fabricated": False,
        "policy": "no_fabricated_management_claims",
    }


def analyse_risks(ev: dict[str, Any]) -> dict[str, Any]:
    industry = ev.get("industry_key") or "unknown"
    company = ev.get("company") or {}
    blob = _blob(company.get("description"), ev.get("question"))
    tmpl = template_for(industry)
    # Prefer Industry DNA typical risks when available (BI consumes, does not duplicate).
    dna_risks = [str(r).lower().replace(" ", "_") for r in (tmpl.get("typical_risks") or [])]
    industry_priors = {
        "banks": ["regulatory", "demand", "execution"],
        "nbfc": ["refinancing", "demand", "regulatory"],
        "cement": ["commodity", "demand", "execution"],
        "airlines": ["commodity", "demand", "execution"],
        "commodity": ["commodity", "political", "regulatory"],
        "saas": ["technology_disruption", "execution", "customer_concentration"],
        "it_services": ["customer_concentration", "execution", "currency"],
        "hospitals": ["regulatory", "execution", "demand"],
        "marketplace": ["regulatory", "technology_disruption", "execution"],
    }
    priors = set(industry_priors.get(industry, ["demand", "execution", "regulatory"]))
    for dr in dna_risks:
        for key in RISK_TYPES:
            if dr in key or key in dr or dr.split("_")[0] in key:
                priors.add(key)
    risks = []
    for key in RISK_TYPES:
        score = 55 if key in priors else 25
        if key.replace("_", " ") in blob or key in blob:
            score += 20
        risks.append(
            {
                "key": key,
                "score": min(95, score),
                "rating": _score_rating(score),
                "prior_for_industry": key in priors,
            }
        )
    top = [r["key"] for r in sorted(risks, key=lambda x: -x["score"])[:5]]
    name = _company_display_name(ev)
    summary = f"Primary business risks for {name}: " + ", ".join(t.replace("_", " ") for t in top) + "."
    if tmpl.get("from_industry_dna") and tmpl.get("typical_risks"):
        summary += " Industry DNA risks: " + ", ".join(tmpl["typical_risks"][:4]) + "."
    return {
        "industry": industry,
        "risks": risks,
        "primary_risks": top,
        "summary": summary,
        "from_industry_dna": bool(tmpl.get("from_industry_dna")),
        "confidence": 0.85 if tmpl.get("from_industry_dna") else (0.8 if industry != "unknown" else 0.45),
        "fabricated": False,
    }


def analyse_lifecycle(ev: dict[str, Any]) -> dict[str, Any]:
    industry = ev.get("industry_key") or "unknown"
    tmpl = template_for(industry)
    stage = tmpl.get("lifecycle_default") or "mature"
    if stage not in LIFECYCLE_STAGES:
        stage = "mature"
    q = (ev.get("question") or "").lower()
    if "turnaround" in q:
        stage = "turnaround"
    elif "decline" in q:
        stage = "decline"
    elif "hypergrowth" in q or "hyper growth" in q:
        stage = "hypergrowth"
    elif "startup" in q:
        stage = "startup"
    return {
        "stage": stage,
        "industry_default": tmpl.get("lifecycle_default"),
        "summary": f"Business lifecycle classification: {stage.replace('_', ' ')}.",
        "all_stages": list(LIFECYCLE_STAGES),
        "confidence": 0.7,
        "fabricated": False,
    }
