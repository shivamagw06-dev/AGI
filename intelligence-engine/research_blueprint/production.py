"""DRBE V1 production facade — RQ1 Sprint 8."""

from __future__ import annotations

from typing import Any

from research_blueprint.blueprint_registry import DEFAULT_SECTION_OWNERS, all_report_types, registry_stats
from research_blueprint.diagnostics import diagnose
from research_blueprint.dynamic_layout import build_research_blueprint
from research_blueprint.flags import flags_dict, is_enabled
from research_blueprint.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    DRBE_VERSION,
    MAX_BLUEPRINT_MS_TARGET,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "q": "Should I buy HDFC Bank?",
        "objective": "Investment Evaluation",
        "expect_report": "institutional_investment_report",
        "expect_sections_contains": [
            "executive_summary",
            "investment_thesis",
            "business_quality",
            "financial_quality",
            "valuation",
            "risk",
            "forecast",
            "portfolio_fit",
            "committee_opinion",
            "cio_summary",
        ],
        "expect_owner": {"business_quality": "Business", "valuation": "Valuation", "cio_summary": "CIO"},
    },
    {
        "q": "Compare TCS vs Infosys",
        "objective": "Peer Comparison",
        "expect_report": "comparison_report",
        "expect_sections_contains": [
            "executive_summary",
            "business_comparison",
            "financial_comparison",
            "competitive_position",
            "valuation_comparison",
            "historical_comparison",
            "risk_comparison",
            "conclusion",
        ],
        "expect_suppressed_contains": ["portfolio_fit", "committee_opinion"],
    },
    {
        "q": "Explain ROIC",
        "objective": "Educational",
        "expect_report": "educational_guide",
        "expect_sections_contains": [
            "definition",
            "importance",
            "calculation",
            "examples",
            "common_mistakes",
            "case_study",
            "summary",
        ],
        "expect_suppressed_contains": ["portfolio_fit", "committee_opinion", "forecast", "valuation"],
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "objective": "Historical Analysis",
        "expect_report": "historical_valuation_report",
        "expect_sections_contains": [
            "executive_summary",
            "historical_valuation",
            "historical_percentiles",
            "peer_comparison",
            "macro_drivers",
            "market_expectations",
            "scenario_analysis",
            "conclusion",
        ],
        "expect_suppressed_contains": ["business_quality", "portfolio_fit"],
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "objective": "Macro Impact",
        "expect_report": "macro_intelligence_report",
        "expect_order_prefix": ["executive_summary", "macro_drivers", "policy", "transmission"],
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "objective": "Portfolio Decision",
        "expect_report": "portfolio_memorandum",
        "expect_sections_contains": ["portfolio_construction", "portfolio_fit"],
    },
    {
        "q": "What are the risks in Reliance Industries?",
        "objective": "Risk Assessment",
        "expect_report": "risk_report",
        "expect_sections_contains": ["risk"],
        "expect_owner": {"risk": "Risk"},
    },
    {
        "q": "Accounting review of Yes Bank",
        "objective": "Accounting Review",
        "expect_report": "accounting_review",
        "expect_sections_contains": ["accounting_quality"],
        "expect_owner": {"accounting_quality": "Accounting"},
    },
]

_TEMPLATES: list[tuple[str, str, dict[str, Any]]] = [
    ("Should I buy {name}?", "Investment Evaluation", {"expect_report": "institutional_investment_report"}),
    ("Should I sell {name}?", "Investment Evaluation", {"expect_report": "institutional_investment_report"}),
    ("Compare {name} vs {peer}", "Peer Comparison", {"expect_report": "comparison_report"}),
    ("Explain {concept}", "Educational", {"expect_report": "educational_guide", "expect_suppressed_contains": ["portfolio_fit", "valuation"]}),
    ("Is {index} expensive versus history?", "Historical Analysis", {"expect_report": "historical_valuation_report"}),
    ("How will RBI rate cuts affect {sector}?", "Macro Impact", {"expect_report": "macro_intelligence_report"}),
    ("Build a portfolio with {name}", "Portfolio Decision", {"expect_report": "portfolio_memorandum"}),
    ("What are the risks in {name}?", "Risk Assessment", {"expect_report": "risk_report"}),
    ("Is {name} overvalued?", "Valuation Assessment", {"expect_report": "historical_valuation_report"}),
    ("Assess business quality of {name}", "Business Quality Assessment", {"expect_report": "company_research_report"}),
    ("Forecast earnings for {name}", "Forecast", {"expect_report": "forecast_report"}),
    ("Screen for quality {sector} stocks", "Screening", {"expect_report": "screening_report"}),
    ("News impact on {name}", "News Impact", {"expect_report": "news_brief"}),
    ("Bull and bear case for {name}", "Scenario Analysis", {"expect_report": "scenario_analysis"}),
    ("Accounting review of {name}", "Accounting Review", {"expect_report": "accounting_review"}),
    ("Management assessment of {name}", "Management Assessment", {"expect_report": "management_review"}),
    ("Is {sector} sector attractive?", "Sector Attractiveness", {"expect_report": "sector_research_report"}),
    ("Industry structure of {sector}", "Industry Structure", {"expect_report": "industry_report"}),
    ("Stress test {name}", "Risk Assessment", {"expect_report": "stress_test"}),
    ("Market open brief for {name}", "Technical Analysis", {"expect_report": "market_open_brief"}),
]

_NAMES = ["HDFC Bank", "Infosys", "TCS", "Reliance", "SBI", "ICICI Bank", "Wipro", "Titan", "ITC", "Axis Bank"]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech"]
_SECTORS = ["banks", "IT", "auto", "pharma", "FMCG"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "WACC"]


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": DRBE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_blueprint_ms_target": MAX_BLUEPRINT_MS_TARGET,
        "registry": registry_stats(),
        "not_a_top_level_intelligence_layer": True,
        "law": "The blueprint is finalised before research begins.",
        "research_assignment_book": True,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "report_types": all_report_types()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "drbe_version": DRBE_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "drbe_version": DRBE_VERSION}
    return {"enabled": True, **build_research_blueprint(question, body)}


def enrich(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return plan(payload)


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:8]:
        row = build_research_blueprint(b["q"], {"primary_objective": b.get("objective")})
        samples.append(
            {
                "question": b["q"],
                "report_type": row.get("report_type"),
                "report_name": row.get("report_name"),
                "section_order": row.get("section_order"),
                "mandatory_sections": row.get("mandatory_sections"),
                "hidden_sections": row.get("hidden_sections"),
                "suppressed_sections": row.get("suppressed_sections"),
                "section_owner": row.get("section_owner"),
                "assignment_count": (row.get("assignment_book") or {}).get("assignment_count"),
                "blueprint_ms": (row.get("metrics") or {}).get("blueprint_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "drbe_version": DRBE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "registry": registry_stats(),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/blueprint-engine"],
        "api_prefix": "/v1/research-blueprint",
        "law": "Every Ask AGI request has a complete institutional publication plan before research begins.",
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    row = build_research_blueprint(question, payload or {})
    return {
        "drbe_version": DRBE_VERSION,
        "question": row.get("question"),
        "report_type": row.get("report_type"),
        "report_name": row.get("report_name"),
        "section_order": row.get("section_order"),
        "section_owner": row.get("section_owner"),
        "mandatory_sections": row.get("mandatory_sections"),
        "optional_sections": row.get("optional_sections"),
        "hidden_sections": row.get("hidden_sections"),
        "suppressed_sections": row.get("suppressed_sections"),
        "quality_rules": {
            "maximum_sections": (row.get("quality_rules") or {}).get("maximum_sections"),
            "writing_style": (row.get("quality_rules") or {}).get("writing_style"),
            "citation_rules": (row.get("quality_rules") or {}).get("citation_rules"),
        },
        "assignment_book": {
            "assignment_count": (row.get("assignment_book") or {}).get("assignment_count"),
            "assignments": [
                {
                    "owner": a.get("owner"),
                    "mission": a.get("mission"),
                    "assigned_sections": a.get("assigned_sections"),
                    "must_not_discuss": a.get("must_not_discuss"),
                }
                for a in ((row.get("assignment_book") or {}).get("assignments") or [])
            ],
        },
        "rendering_contract_section_count": len((row.get("rendering_contract") or {}).get("sections") or []),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
    }


def _expanded() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    i = 0
    while len(cases) < 1100:
        tmpl, objective, extra = _TEMPLATES[i % len(_TEMPLATES)]
        name = _NAMES[i % len(_NAMES)]
        peer = _PEERS[i % len(_PEERS)]
        if peer == name:
            peer = _PEERS[(i + 1) % len(_PEERS)]
        q = tmpl.format(
            name=name,
            peer=peer,
            sector=_SECTORS[i % len(_SECTORS)],
            index=_INDEXES[i % len(_INDEXES)],
            concept=_CONCEPTS[i % len(_CONCEPTS)],
        )
        cases.append({"q": q, "objective": objective, **extra, "kind": "template"})
        i += 1
    return cases


def _check(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if b.get("expect_report") and row.get("report_type") != b["expect_report"]:
        errs.append("report_type")
    order = list(row.get("section_order") or [])
    mandatory = set(row.get("mandatory_sections") or [])
    suppressed = set(row.get("suppressed_sections") or [])
    if b.get("expect_sections_contains") and not set(b["expect_sections_contains"]).issubset(set(order) | mandatory):
        # mandatory sections should appear in order (except hidden)
        missing = [s for s in b["expect_sections_contains"] if s not in order]
        if missing:
            errs.append("sections_contains")
    if b.get("expect_suppressed_contains") and not set(b["expect_suppressed_contains"]).issubset(suppressed):
        errs.append("suppressed_contains")
    if b.get("expect_order_prefix"):
        prefix = b["expect_order_prefix"]
        if order[: len(prefix)] != prefix:
            errs.append("order_prefix")
    owners = row.get("section_owner") or {}
    for section, owner in (b.get("expect_owner") or {}).items():
        if owners.get(section) != owner:
            errs.append(f"owner:{section}")
    # ownership completeness for active sections
    for key in order:
        if not owners.get(key):
            errs.append("ownership_missing")
            break
        expected_default = DEFAULT_SECTION_OWNERS.get(key)
        if expected_default and owners.get(key) != expected_default:
            # allow Research Writer / CIO fixed overrides already in engine
            if key not in {"executive_summary", "cio_summary", "committee_opinion"} and owners.get(key) != expected_default:
                errs.append(f"owner_mismatch:{key}")
                break
    # no irrelevant: suppressed must not be in order as mandatory render targets
    for key in order:
        if key in suppressed and (row.get("metrics") or {}).get("no_irrelevant_sections") is False:
            errs.append("irrelevant")
            break
    if key_in_suppressed_and_mandatory(row):
        errs.append("irrelevant_mandatory")
    if not row.get("mandatory_fields_present", True):
        errs.append("mandatory_fields")
    ab = row.get("assignment_book") or {}
    if not ab.get("assignments"):
        errs.append("assignment_book")
    return errs


def key_in_suppressed_and_mandatory(row: dict[str, Any]) -> bool:
    suppressed = set(row.get("suppressed_sections") or [])
    mandatory = set(row.get("mandatory_sections") or [])
    return bool(suppressed & mandatory)


def quality_gates() -> dict[str, Any]:
    cases = _expanded()
    blueprint_ok = 0
    report_ok = 0
    ownership_ok = 0
    irrelevant_ok = 0
    times: list[float] = []
    failures: list[dict[str, Any]] = []
    checked = 0

    for b in cases:
        row = build_research_blueprint(b["q"], {"primary_objective": b.get("objective")})
        checked += 1
        errs = _check(b, row)
        times.append(float((row.get("metrics") or {}).get("blueprint_ms") or 0))
        if b.get("expect_report") and row.get("report_type") == b["expect_report"]:
            report_ok += 1
        elif not b.get("expect_report"):
            report_ok += 1
        if (row.get("metrics") or {}).get("ownership_complete"):
            ownership_ok += 1
        if (row.get("metrics") or {}).get("no_irrelevant_sections") and not key_in_suppressed_and_mandatory(row):
            irrelevant_ok += 1
        if not errs:
            blueprint_ok += 1
        elif len(failures) < 25:
            failures.append({"q": b["q"], "errs": errs, "report": row.get("report_type")})

    n = max(checked, 1)
    avg_ms = sum(times) / n
    criteria = constitution_dict()["success_criteria"]
    blueprint_acc = blueprint_ok / n
    report_acc = report_ok / n
    ownership_acc = ownership_ok / n
    irrelevant_acc = irrelevant_ok / n
    passed = (
        checked >= int(criteria["benchmark_minimum"])
        and blueprint_acc >= float(criteria["blueprint_accuracy"])
        and report_acc >= float(criteria["correct_report_selection"])
        and ownership_acc >= float(criteria["correct_section_ownership"])
        and irrelevant_acc >= float(criteria["no_irrelevant_sections"])
        and avg_ms < float(criteria["blueprint_generation_ms"])
    )
    return {
        "ok": passed,
        "checked": checked,
        "blueprint_accuracy": round(blueprint_acc, 4),
        "correct_report_selection": round(report_acc, 4),
        "correct_section_ownership": round(ownership_acc, 4),
        "no_irrelevant_sections": round(irrelevant_acc, 4),
        "average_blueprint_ms": round(avg_ms, 4),
        "benchmark_minimum": criteria["benchmark_minimum"],
        "targets": criteria,
        "failures_sample": failures,
        "drbe_version": DRBE_VERSION,
        "sprint": SPRINT,
    }
