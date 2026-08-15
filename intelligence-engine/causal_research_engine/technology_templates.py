"""Proposed Phase 2A causal curriculum; models cannot self-promote it."""
from __future__ import annotations
from causal_research_engine.schema import CausalRelationship, CounterEffect


def it_services_templates(company_id: str | None = None) -> list[CausalRelationship]:
    rows = (
        ("enterprise_it_spending", "discretionary_projects", "POSITIVE", "Client budgets determine discretionary project starts.", ()),
        ("discretionary_projects", "deal_wins_tcv", "POSITIVE", "Project demand affects signed contract value and pipeline conversion.", ()),
        ("deal_wins_tcv", "revenue_growth", "POSITIVE", "Signed contracts convert to revenue according to scope, duration and execution.", ()),
        ("revenue_growth", "utilization", "POSITIVE", "Demand can absorb available delivery capacity.", (CounterEffect("Hiring slows and protects utilization", "POSITIVE", "Capacity growth can slow when demand weakens", "1_QUARTER"),)),
        ("utilization", "ebit_margin", "POSITIVE", "Higher billable use spreads employee and bench costs.", ()),
        ("employee_cost_growth", "ebit_margin", "NEGATIVE", "Wages and replacement costs reduce operating profit unless offset by pricing and productivity.", ()),
        ("billing_rates", "revenue_per_employee", "POSITIVE", "Pricing and mix raise realized revenue per delivery unit.", ()),
        ("ebit_margin", "free_cash_flow", "POSITIVE", "Operating profit transmits to cash after tax, working capital and capex.", ()),
        ("free_cash_flow", "valuation", "POSITIVE", "Durable cash generation supports intrinsic value and valuation multiples.", ()),
        ("ai_productivity", "delivery_cost_per_project", "NEGATIVE", "Automation can reduce delivery effort.", (CounterEffect("Hours sold or pricing may fall", "NEGATIVE", "Clients may capture productivity benefits through lower effort-based billing", "2_QUARTERS"),)),
        ("ai_productivity", "ebit_margin", "CONDITIONAL", "Margins improve only if productivity savings are retained rather than competed away.", (CounterEffect("Pricing pressure offsets savings", "NEGATIVE", "Competitive rebidding transfers savings to clients", "2_QUARTERS"),)),
    )
    return [CausalRelationship(
        relationship_id=f"CRE-TECH2A-{i:02d}", cause=cause, effect=effect, direction=direction,
        relationship_type="CAUSAL_HYPOTHESIS", epistemic_label="HYPOTHESIS", industry="IT Services",
        company_id=company_id, strength="MEDIUM", confidence=.55, time_lag="1_QUARTER",
        mechanism=mechanism, counter_effects=counter, source_quality="UNVALIDATED", status="PROPOSED",
        created_by="phase_2a_code_reviewed_curriculum",
    ) for i, (cause, effect, direction, mechanism, counter) in enumerate(rows, 1)]
