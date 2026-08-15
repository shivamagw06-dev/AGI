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


def software_saas_templates(company_id: str | None = None) -> list[CausalRelationship]:
    rows=(
        ("new_customers","arr","POSITIVE","New contracted customers add recurring value.",()),
        ("net_revenue_retention","arr_growth","POSITIVE","Retention and expansion compound the installed base.",(CounterEffect("Concentration can magnify one loss", "NEGATIVE", "A large customer loss can overwhelm expansion", "1_QUARTER"),)),
        ("gross_revenue_retention","growth_durability","POSITIVE","Defensive retention indicates whether recurring revenue persists without upsell.",()),
        ("churn","arr_growth","NEGATIVE","Lost customer and contract value reduce the recurring base.",()),
        ("pricing","average_contract_value","POSITIVE","Price and mix affect monetization per contract.",(CounterEffect("Price increases can raise churn", "NEGATIVE", "Customers may downgrade or leave", "2_QUARTERS"),)),
        ("gross_margin","customer_ltv","POSITIVE","Higher gross profit retained per customer improves lifetime economics.",()),
        ("cac_payback","growth_efficiency","NEGATIVE","Longer payback increases capital required for growth.",()),
        ("arr_growth","operating_leverage","CONDITIONAL","Recurring growth can absorb R&D and go-to-market costs after sufficient scale.",(CounterEffect("Sales and R&D reinvestment delays leverage", "NEGATIVE", "Management may prioritize market capture", "MULTI_YEAR"),)),
        ("operating_leverage","free_cash_flow","POSITIVE","Scale can convert recurring gross profit into cash generation.",()),
        ("free_cash_flow","valuation","POSITIVE","Cash generation reduces dependence on terminal multiple assumptions.",()),
        ("ai_productivity","software_value_proposition","CONDITIONAL","AI can improve product utility and development efficiency.",(CounterEffect("AI commoditizes features", "NEGATIVE", "Lower switching costs and new entrants pressure pricing", "MULTI_YEAR"),)),
        ("stock_based_compensation","per_share_value","NEGATIVE","Equity compensation transfers value through dilution even when excluded from adjusted profit.",()),
    )
    return [CausalRelationship(relationship_id=f"CRE-TECH2B-{i:02d}",cause=cause,effect=effect,direction=direction,
        relationship_type="CAUSAL_HYPOTHESIS",epistemic_label="HYPOTHESIS",industry="Software and SaaS",company_id=company_id,
        strength="MEDIUM",confidence=.55,time_lag="1_QUARTER",mechanism=mechanism,counter_effects=counter,
        source_quality="UNVALIDATED",status="PROPOSED",created_by="phase_2b_code_reviewed_curriculum")
        for i,(cause,effect,direction,mechanism,counter) in enumerate(rows,1)]
