"""Module 1 — Framework Registry.

Every framework is an executable object — not a hardcoded type map.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iki.schema import FrameworkSpec

REGISTRY_VERSION = "framework-registry-v1.0.0"

_FRAMEWORKS: dict[str, FrameworkSpec] = {
    "rel_val_damodaran": FrameworkSpec(
        framework_id="rel_val_damodaran",
        name="Damodaran Relative Valuation",
        author="Damodaran",
        school="damodaran",
        question_types=("valuation", "comparison", "investment_decision"),
        requires=("current_pe", "peer_pe"),
        produces=("premium_discount", "confidence"),
        applicable_entity_types=("Company", "Index"),
        not_applicable_sectors=(),
        priority=80,
        confidence_weight=0.75,
        failure_conditions=("peer_pe missing",),
        competing_frameworks=("dcf_fcff", "residual_income", "margin_of_safety"),
        alternative_frameworks=("hist_multiples",),
        notes="Profitable and growth companies; peer-relative premium/discount.",
    ),
    "hist_multiples": FrameworkSpec(
        framework_id="hist_multiples",
        name="Historical Multiples Percentile",
        author="Institutional",
        school="institutional",
        question_types=("valuation", "investment_decision", "sector"),
        requires=("current_pe", "historical_pe", "historical_percentile"),
        produces=("historical_percentile", "confidence"),
        applicable_entity_types=("Company", "Index"),
        priority=78,
        confidence_weight=0.8,
        failure_conditions=("historical_pe missing",),
        competing_frameworks=("rel_val_damodaran",),
    ),
    "margin_of_safety": FrameworkSpec(
        framework_id="margin_of_safety",
        name="Graham Margin of Safety",
        author="Graham",
        school="graham",
        question_types=("valuation", "investment_decision"),
        requires=("current_pe", "historical_pe"),
        produces=("mos_pct", "confidence"),
        applicable_entity_types=("Company",),
        not_applicable_entity_types=("Index",),
        not_applicable_sectors=("consumer_internet", "pre_profit_growth"),
        priority=55,
        confidence_weight=0.65,
        failure_conditions=("no margin of safety", "speculative growth"),
        competing_frameworks=("rel_val_damodaran", "dcf_fcff", "buffett_quality"),
        notes="Rejects speculative growth stories without asset/earnings floor.",
    ),
    "dcf_applicability": FrameworkSpec(
        framework_id="dcf_applicability",
        name="DCF Applicability Test",
        author="Damodaran",
        school="damodaran",
        question_types=("valuation", "investment_decision"),
        requires=(),
        produces=("applicable", "reason"),
        applicable_entity_types=("Company",),
        not_applicable_entity_types=("Index",),
        not_applicable_sectors=("bank", "insurance", "nbfc"),
        priority=70,
        confidence_weight=0.7,
        failure_conditions=("financial institution", "no forecastable FCF"),
        competing_frameworks=("residual_income", "rel_val_damodaran"),
        alternative_frameworks=("residual_income",),
        notes="Invalid for banks/insurance/indices; prefer residual income for FI.",
    ),
    "dcf_fcff": FrameworkSpec(
        framework_id="dcf_fcff",
        name="Damodaran Growth DCF (FCFF)",
        author="Damodaran",
        school="damodaran",
        question_types=("valuation", "investment_decision"),
        requires=("fcf", "wacc", "terminal_growth", "shares"),
        produces=("intrinsic_value", "confidence"),
        applicable_entity_types=("Company",),
        not_applicable_entity_types=("Index",),
        not_applicable_sectors=("bank", "insurance", "nbfc"),
        priority=65,
        confidence_weight=0.55,
        failure_conditions=("missing cash flows", "financial institution"),
        competing_frameworks=("rel_val_damodaran", "residual_income", "margin_of_safety"),
        alternative_frameworks=("rel_val_damodaran", "residual_income"),
    ),
    "residual_income": FrameworkSpec(
        framework_id="residual_income",
        name="Residual Income Valuation",
        author="Institutional",
        school="institutional",
        question_types=("valuation", "investment_decision"),
        requires=("roe", "book_value", "cost_of_equity"),
        produces=("intrinsic_value", "confidence"),
        applicable_entity_types=("Company",),
        applicable_sectors=("bank", "insurance", "nbfc"),
        not_applicable_entity_types=("Index",),
        priority=85,
        confidence_weight=0.72,
        failure_conditions=("missing book value",),
        competing_frameworks=("dcf_fcff", "dcf_applicability"),
        alternative_frameworks=(),
        notes="Preferred alternative when DCF is invalid for financial institutions.",
    ),
    "peer_comparison": FrameworkSpec(
        framework_id="peer_comparison",
        name="Peer Comparison",
        author="Institutional",
        school="institutional",
        question_types=("comparison", "valuation"),
        requires=("peer_set", "comparable_metrics"),
        produces=("peer_rank", "confidence"),
        applicable_entity_types=("Company", "Index"),
        priority=75,
        confidence_weight=0.7,
    ),
    "business_quality_roic": FrameworkSpec(
        framework_id="business_quality_roic",
        name="ROIC Quality Assessment",
        author="Institutional",
        school="institutional",
        question_types=("business_quality", "investment_decision", "comparison"),
        requires=("roic", "margins"),
        produces=("quality_grade", "confidence"),
        applicable_entity_types=("Company",),
        priority=80,
        confidence_weight=0.78,
        competing_frameworks=("buffett_quality",),
    ),
    "buffett_quality": FrameworkSpec(
        framework_id="buffett_quality",
        name="Buffett Wonderful Business Screen",
        author="Buffett",
        school="buffett",
        question_types=("business_quality", "investment_decision", "valuation"),
        requires=("roic", "margins"),
        produces=("quality_score", "stance", "confidence"),
        applicable_entity_types=("Company",),
        not_applicable_sectors=("pre_profit_growth", "consumer_internet"),
        priority=70,
        confidence_weight=0.7,
        failure_conditions=("no durable moat evidence", "speculative growth"),
        competing_frameworks=("rel_val_damodaran", "dcf_fcff", "margin_of_safety"),
        notes="Increases quality score when ROIC/margins/capital allocation pass.",
    ),
    "accounting_quality_screen": FrameworkSpec(
        framework_id="accounting_quality_screen",
        name="Accounting Quality Screen",
        author="Institutional",
        school="institutional",
        question_types=("financial_quality", "investment_decision"),
        requires=("cash_conversion", "leverage", "earnings_quality"),
        produces=("accounting_flags", "confidence"),
        applicable_entity_types=("Company",),
        priority=72,
        confidence_weight=0.7,
    ),
    "graham_net_net": FrameworkSpec(
        framework_id="graham_net_net",
        name="Graham Net-Net / Asset Floor",
        author="Graham",
        school="graham",
        question_types=("valuation",),
        requires=("current_pe",),
        produces=("asset_floor_signal", "confidence"),
        applicable_entity_types=("Company",),
        not_applicable_sectors=("consumer_internet", "pre_profit_growth", "bank"),
        priority=40,
        confidence_weight=0.5,
        failure_conditions=("growth franchise", "no tangible asset floor"),
        competing_frameworks=("dcf_fcff", "rel_val_damodaran", "buffett_quality"),
    ),
}


def list_frameworks() -> list[dict[str, Any]]:
    return [f.to_dict() for f in _FRAMEWORKS.values()]


def get_framework(framework_id: str) -> FrameworkSpec | None:
    return _FRAMEWORKS.get(str(framework_id or ""))


def frameworks_for_question_type(question_type: str) -> list[FrameworkSpec]:
    qt = str(question_type or "").lower()
    out = [f for f in _FRAMEWORKS.values() if qt in f.question_types or not f.question_types]
    # Always include applicability-critical peers for valuation
    if qt == "valuation":
        for extra in ("residual_income", "dcf_fcff", "buffett_quality", "graham_net_net"):
            f = _FRAMEWORKS.get(extra)
            if f and f not in out:
                out.append(f)
    out.sort(key=lambda f: -f.priority)
    return out


def registry_snapshot() -> dict[str, Any]:
    return {
        "registry_version": REGISTRY_VERSION,
        "n": len(_FRAMEWORKS),
        "frameworks": list_frameworks(),
    }
