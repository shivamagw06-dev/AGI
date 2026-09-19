"""Institutional Knowledge Object (IKO) v2.0 — claim-centric schema."""

from __future__ import annotations

from typing import Any, Literal

IKO_VERSION = "iko-v2.0.0"
PROGRAMME = "AGI Institutional Knowledge Object — Claim-Centric Company DNA"
MODULE_CODE = "IKO"

ClaimState = Literal[
    "SUPPORTED",
    "ANSWERED",
    "PARTIAL",
    "CONTRADICTED",
    "STALE",
    "UNKNOWN",
    "UNDER_REVIEW",
]

ClaimType = Literal[
    "business",
    "financial",
    "management",
    "valuation",
    "growth",
    "risk",
    "investment",
    "monitoring",
    "thesis",
    "identity",
]

CLAIM_STATES: tuple[str, ...] = (
    "SUPPORTED",
    "ANSWERED",
    "PARTIAL",
    "CONTRADICTED",
    "STALE",
    "UNKNOWN",
    "UNDER_REVIEW",
)

CLAIM_TYPES: tuple[str, ...] = (
    "business",
    "financial",
    "management",
    "valuation",
    "growth",
    "risk",
    "investment",
    "monitoring",
    "thesis",
    "identity",
)

# Stronger states for completeness scoring (ordered)
STATE_STRENGTH: dict[str, int] = {
    "SUPPORTED": 5,
    "ANSWERED": 4,
    "PARTIAL": 3,
    "UNDER_REVIEW": 2,
    "CONTRADICTED": 2,
    "STALE": 1,
    "UNKNOWN": 0,
}

CLAIM_CATEGORIES: tuple[str, ...] = (
    "identity",
    "business_model",
    "economic_engine",
    "competitive_position",
    "management",
    "financial_quality",
    "growth",
    "valuation_context",
    "investment_thesis",
    "risks",
    "monitoring",
)

# Required claim templates — registry seeds (instantiated per entity)
CLAIM_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "template_id": "CLAIM_IDENTITY_BUSINESS",
        "claim_type": "identity",
        "category": "identity",
        "statement_template": "{company} generates revenue primarily through {primary_activity}.",
        "required": True,
        "evidence_required": ("annual_report", "investor_presentation"),
    },
    {
        "template_id": "CLAIM_BUSINESS_SWITCHING_COSTS",
        "claim_type": "business",
        "category": "competitive_position",
        "statement_template": "{company} possesses durable switching costs with key customers.",
        "required": False,
        "evidence_required": ("annual_report", "client_retention", "margins"),
    },
    {
        "template_id": "CLAIM_FINANCIAL_CASH_GENERATION",
        "claim_type": "financial",
        "category": "financial_quality",
        "statement_template": "{company} generates strong and stable free cash flow relative to capex.",
        "required": True,
        "evidence_required": ("financials", "cash_flow_statement"),
    },
    {
        "template_id": "CLAIM_MGMT_CAPITAL_ALLOCATION",
        "claim_type": "management",
        "category": "management",
        "statement_template": "{company} management has historically allocated capital in shareholders' interests.",
        "required": True,
        "evidence_required": ("annual_report", "capital_allocation_history"),
    },
    {
        "template_id": "CLAIM_VALUATION_HISTORICAL",
        "claim_type": "valuation",
        "category": "valuation_context",
        "statement_template": "{company} current valuation is {position} versus its historical range.",
        "required": True,
        "evidence_required": ("valuation", "historical_multiples"),
    },
    {
        "template_id": "CLAIM_RISK_MARGIN_PRESSURE",
        "claim_type": "risk",
        "category": "risks",
        "statement_template": "Margin pressure from {driver} may impair {company}'s profitability.",
        "required": False,
        "evidence_required": ("earnings", "industry_data"),
    },
    {
        "template_id": "CLAIM_INVESTMENT_THESIS_CORE",
        "claim_type": "investment",
        "category": "investment_thesis",
        "statement_template": "Institutional thesis on {company} depends primarily on {key_driver}.",
        "required": True,
        "evidence_required": ("financials", "valuation", "business_quality"),
    },
    {
        "template_id": "CLAIM_MONITORING_MARGIN",
        "claim_type": "monitoring",
        "category": "monitoring",
        "statement_template": "{company} operating margins remain resilient.",
        "required": False,
        "evidence_required": ("quarterly_results",),
        "monitoring_trigger_template": "operating_margin < {threshold}",
    },
)

FORBIDDEN_CLAIM_TOKENS: tuple[str, ...] = (
    "buy this",
    "sell this",
    "strong buy",
    "strong sell",
    "target price",
    "entry price",
    "exit price",
    "guaranteed return",
    "must buy",
    "must sell",
)


def claim_id(entity_id: str, template_id: str, *, suffix: str = "001") -> str:
    e = (entity_id or "ENTITY").upper().replace(" ", "_")
    t = template_id.replace("CLAIM_", "")
    return f"CLAIM_{e}_{t}_{suffix}"


def empty_claim(
    *,
    entity_id: str,
    template: dict[str, Any],
    company: str | None = None,
) -> dict[str, Any]:
    """Instantiate an UNKNOWN claim from a registry template."""
    label = company or entity_id
    stmt = str(template.get("statement_template") or "").format(
        company=label,
        primary_activity="[unknown]",
        position="[unknown]",
        driver="[unknown]",
        key_driver="[unknown]",
        threshold="[unknown]",
    )
    return {
        "claim_id": claim_id(entity_id, str(template["template_id"])),
        "entity_id": entity_id.upper(),
        "entity_type": "company",
        "template_id": template["template_id"],
        "statement": stmt,
        "claim_type": template["claim_type"],
        "category": template["category"],
        "state": "UNKNOWN",
        "confidence": 0,
        "evidence_refs": [],
        "contradictions": [],
        "dependencies": [],
        "monitoring": None,
        "reasoning_summary": None,
        "owner": "company_dna",
        "last_review": None,
        "version": 1,
        "fabricated": False,
        "llm_used": False,
    }


def empty_iko(entity_id: str, *, company: str | None = None) -> dict[str, Any]:
    """Empty Institutional Knowledge Object for a company."""
    claims = [empty_claim(entity_id=entity_id, template=t, company=company) for t in CLAIM_REGISTRY]
    return {
        "iko_version": IKO_VERSION,
        "module_code": MODULE_CODE,
        "entity_id": entity_id.upper(),
        "entity_type": "company",
        "identity": {
            "company_name": company or entity_id,
            "ticker": entity_id.upper(),
        },
        "claims": claims,
        "evidence_refs": [],
        "unknowns": [c["claim_id"] for c in claims if c["state"] == "UNKNOWN"],
        "monitoring": [],
        "decision_memory_refs": [],
        "completeness": compute_completeness(claims),
        "version_history": [],
        "fabricated": False,
        "llm_used": False,
    }


def compute_completeness(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Claim-state completeness — no percentages."""
    counts: dict[str, int] = {s: 0 for s in CLAIM_STATES}
    required = 0
    for c in claims:
        st = str(c.get("state") or "UNKNOWN")
        counts[st] = counts.get(st, 0) + 1
        if c.get("required") is not False:
            required += 1
    total = len(claims) or required
    return {
        "required_claims": required or total,
        "total_claims": total,
        "supported": counts.get("SUPPORTED", 0),
        "answered": counts.get("ANSWERED", 0),
        "partial": counts.get("PARTIAL", 0),
        "contradicted": counts.get("CONTRADICTED", 0),
        "stale": counts.get("STALE", 0),
        "unknown": counts.get("UNKNOWN", 0),
        "under_review": counts.get("UNDER_REVIEW", 0),
        "no_percentages": True,
    }
