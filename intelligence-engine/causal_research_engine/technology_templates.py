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


def platform_marketplace_templates(company_id: str | None = None) -> list[CausalRelationship]:
    rows=(
        ("active_buyers","seller_value_proposition","POSITIVE","More relevant demand can improve seller conversion.",(CounterEffect("Low-intent users dilute liquidity","NEGATIVE","Raw user count may not create transactions","1_QUARTER"),)),
        ("active_sellers","buyer_selection","POSITIVE","More quality supply can improve selection.",(CounterEffect("Low-quality supply raises trust costs","NEGATIVE","Uncurated supply can weaken experience","1_QUARTER"),)),
        ("marketplace_liquidity","order_frequency","POSITIVE","Better matching encourages repeat transactions.",()),
        ("order_frequency","gmv","POSITIVE","More transactions per active buyer increase activity.",()),
        ("take_rate","revenue","POSITIVE","Fees convert GMV into revenue.",(CounterEffect("Higher fees encourage disintermediation","NEGATIVE","Participants may transact off-platform or churn","2_QUARTERS"),)),
        ("customer_incentives","gmv_growth","POSITIVE","Discounts can stimulate transactions.",(CounterEffect("Subsidies weaken contribution economics","NEGATIVE","Purchased growth may disappear when incentives end","1_QUARTER"),)),
        ("repeat_rate","customer_lifetime_value","POSITIVE","Repeat cohorts distribute acquisition cost over more gross profit.",()),
        ("refund_cancellation_rate","contribution_margin","NEGATIVE","Refunds and failed fulfillment consume transaction economics.",()),
        ("contribution_margin","free_cash_flow","POSITIVE","Positive transaction economics can absorb fixed costs.",()),
        ("free_cash_flow","valuation","POSITIVE","Durable cash generation reduces reliance on distant scale assumptions.",()),
        ("seller_concentration","platform_bargaining_power","NEGATIVE","Concentrated supply can negotiate fees or multi-home.",()),
        ("ai_matching","marketplace_liquidity","CONDITIONAL","AI can improve discovery, fraud detection and support.",(CounterEffect("AI lowers discovery differentiation","NEGATIVE","Competitors may replicate matching capabilities","MULTI_YEAR"),)),
    )
    return [CausalRelationship(relationship_id=f"CRE-TECH2C-{i:02d}",cause=cause,effect=effect,direction=direction,
        relationship_type="CAUSAL_HYPOTHESIS",epistemic_label="HYPOTHESIS",industry="Internet Platforms and Marketplaces",company_id=company_id,
        strength="MEDIUM",confidence=.55,time_lag="1_QUARTER",mechanism=mechanism,counter_effects=counter,
        source_quality="UNVALIDATED",status="PROPOSED",created_by="phase_2c_code_reviewed_curriculum")
        for i,(cause,effect,direction,mechanism,counter) in enumerate(rows,1)]


def consumer_digital_templates(company_id: str | None = None) -> list[CausalRelationship]:
    rows=(
        ("active_customers","net_revenue","POSITIVE","More retained purchasing customers expand the revenue base.",(CounterEffect("Paid acquisition can mask weak retention","NEGATIVE","New users may not repeat after incentives","2_QUARTERS"),)),
        ("order_frequency","net_sales","POSITIVE","Higher repeat frequency increases sales per active customer.",()),
        ("average_order_value","net_sales","POSITIVE","Price and basket mix raise sales per order.",(CounterEffect("Higher prices can reduce conversion","NEGATIVE","Elastic demand can offset ticket growth","1_QUARTER"),)),
        ("return_rate","net_revenue","NEGATIVE","Returns reverse sales and add handling and inventory costs.",()),
        ("inventory_turns","cash_conversion","POSITIVE","Faster inventory movement reduces capital tied in stock.",(CounterEffect("Understocking causes lost sales","NEGATIVE","Excessively lean inventory can reduce availability","1_QUARTER"),)),
        ("gross_margin","contribution_margin","POSITIVE","Merchandise and ad/subscription mix set the profit pool before fulfillment and marketing.",()),
        ("fulfillment_cost_per_order","contribution_margin","NEGATIVE","Delivery, warehousing and service costs consume order economics.",()),
        ("customer_acquisition_cost","growth_efficiency","NEGATIVE","Higher acquisition cost increases the repeat behavior needed for payback.",()),
        ("repeat_rate","customer_lifetime_value","POSITIVE","Repeat cohorts spread acquisition cost across more gross profit.",()),
        ("advertising_arpu","gross_margin","POSITIVE","High-margin advertising can lift blended economics.",(CounterEffect("Ad load can damage user experience","NEGATIVE","Excess monetization may reduce engagement","2_QUARTERS"),)),
        ("contribution_margin","free_cash_flow","POSITIVE","Positive cohort and order economics can absorb fixed technology and corporate costs.",()),
        ("ai_personalization","conversion","CONDITIONAL","AI can improve discovery, pricing and service productivity.",(CounterEffect("Privacy, compute cost and commoditization offset gains","NEGATIVE","Implementation can add cost or weaken trust","MULTI_YEAR"),)),
    )
    return [CausalRelationship(relationship_id=f"CRE-TECH2D-{i:02d}",cause=cause,effect=effect,direction=direction,relationship_type="CAUSAL_HYPOTHESIS",epistemic_label="HYPOTHESIS",industry="Consumer Internet and Digital Commerce",company_id=company_id,strength="MEDIUM",confidence=.55,time_lag="1_QUARTER",mechanism=mechanism,counter_effects=counter,source_quality="UNVALIDATED",status="PROPOSED",created_by="phase_2d_code_reviewed_curriculum") for i,(cause,effect,direction,mechanism,counter) in enumerate(rows,1)]


def semiconductor_templates(company_id: str | None = None) -> list[CausalRelationship]:
    rows=(("end_market_demand","unit_shipments","POSITIVE","Device production and semiconductor content determine chip demand.",(CounterEffect("Customer inventory correction delays orders","NEGATIVE","Sell-in can fall despite stable end demand","2_QUARTERS"),)),("average_selling_price","revenue","POSITIVE","Product mix and pricing convert units into revenue.",(CounterEffect("Mature-node oversupply pressures pricing","NEGATIVE","Capacity additions can reduce ASP","MULTI_YEAR"),)),("utilization","gross_margin","POSITIVE","Higher fab or packaging utilization absorbs fixed manufacturing cost.",()),("yield_rate","gross_margin","POSITIVE","More saleable output per wafer or package lowers unit cost.",()),("technology_transition","rnd_intensity","POSITIVE","New nodes, packaging and IP require sustained development.",(CounterEffect("Failed programs impair returns","NEGATIVE","R&D may not produce commercial wins","MULTI_YEAR"),)),("capacity_additions","revenue_capacity","POSITIVE","New qualified capacity raises potential output.",(CounterEffect("Ramp costs and low utilization depress returns","NEGATIVE","Capacity precedes demand and qualification","MULTI_YEAR"),)),("inventory_days","future_shipments","NEGATIVE","Excess channel or customer inventory delays replenishment.",()),("book_to_bill","revenue_growth","POSITIVE","Orders relative to shipments indicate cycle direction when cancellation terms are understood.",()),("gross_margin","free_cash_flow","POSITIVE","Gross profit funds R&D and capital investment.",()),("capex_intensity","free_cash_flow","NEGATIVE","Fabrication and packaging capacity consume cash before utilization.",(CounterEffect("Subsidies reduce net project cost","POSITIVE","Government support can improve project returns","MULTI_YEAR"),)),("free_cash_flow","valuation","POSITIVE","Cycle-adjusted cash generation supports equity value.",()),("ai_demand","high_performance_chip_demand","CONDITIONAL","AI infrastructure increases accelerator, memory, networking and packaging demand.",(CounterEffect("Concentration and export controls raise risk","NEGATIVE","Demand can depend on few customers and regulated markets","MULTI_YEAR"),)))
    return [CausalRelationship(relationship_id=f"CRE-TECH2E-{i:02d}",cause=a,effect=b,direction=d,relationship_type="CAUSAL_HYPOTHESIS",epistemic_label="HYPOTHESIS",industry="Semiconductors",company_id=company_id,strength="MEDIUM",confidence=.55,time_lag="2_QUARTERS",mechanism=m,counter_effects=c,source_quality="UNVALIDATED",status="PROPOSED",created_by="phase_2e_code_reviewed_curriculum") for i,(a,b,d,m,c) in enumerate(rows,1)]


def telecom_templates(company_id: str | None = None) -> list[CausalRelationship]:
    rows=(("tariff_increase","arpu","POSITIVE","Realized pricing can lift monthly revenue per subscriber.",(CounterEffect("Churn and down-trading offset realization","NEGATIVE","Price-sensitive users may leave or reduce spend","2_QUARTERS"),)),("subscriber_growth","service_revenue","POSITIVE","Net additions expand the monetizable base.",()),("data_usage","network_utilization","POSITIVE","Traffic raises capacity use and future network requirements.",()),("postpaid_5g_mix","arpu","POSITIVE","Higher-value mix can raise monetization.",(CounterEffect("Device subsidies and acquisition costs rise","NEGATIVE","Premium additions can require upfront spend","1_QUARTER"),)),("arpu","revenue","POSITIVE","Subscriber monetization transmits into service revenue.",()),("revenue","ebitda","POSITIVE","Incremental service revenue can carry high contribution after variable network costs.",(CounterEffect("Network and customer costs absorb revenue","NEGATIVE","Energy, roaming and acquisition costs limit flow-through","1_QUARTER"),)),("spectrum_cost","net_debt","POSITIVE","Spectrum purchases and deferred liabilities increase funding burden.",()),("network_capex","free_cash_flow","NEGATIVE","4G/5G, fiber and capacity investment consume cash.",(CounterEffect("Coverage and quality reduce churn","POSITIVE","Investment can improve retention and future ARPU","MULTI_YEAR"),)),("ebitda","deleveraging","POSITIVE","Cash earnings support interest and debt reduction after capex.",()),("net_debt","equity_value","NEGATIVE","Debt and spectrum obligations reduce value attributable to equity.",()),("enterprise_contracts","revenue_visibility","POSITIVE","Longer enterprise connectivity contracts can stabilize revenue.",()),("competition_intensity","tariff_realization","NEGATIVE","Aggressive pricing can delay industry tariff repair.",()))
    return [CausalRelationship(relationship_id=f"CRE-TECH2F-{i:02d}",cause=a,effect=b,direction=d,relationship_type="CAUSAL_HYPOTHESIS",epistemic_label="HYPOTHESIS",industry="Telecom",company_id=company_id,strength="MEDIUM",confidence=.58,time_lag="1_QUARTER",mechanism=m,counter_effects=c,source_quality="UNVALIDATED",status="PROPOSED",created_by="phase_2f_code_reviewed_curriculum") for i,(a,b,d,m,c) in enumerate(rows,1)]


def telecom_tower_templates(company_id: str | None = None) -> list[CausalRelationship]:
    rows=(("tenant_additions","tenancy_ratio","POSITIVE","Colocations on existing sites increase tenancy.",(CounterEffect("Operator consolidation removes tenants","NEGATIVE","Network rationalization can cause exits","MULTI_YEAR"),)),("tenancy_ratio","rental_revenue","POSITIVE","More tenants per site increase contracted rent.",()),("rental_escalator","revenue_per_tenant","POSITIVE","Contractual escalators lift rent.",(CounterEffect("Renewal negotiations reset pricing","NEGATIVE","Large customers can demand concessions","MULTI_YEAR"),)),("energy_costs","ebitda_margin","NEGATIVE","Unrecovered energy costs reduce margins.",(CounterEffect("Pass-through clauses offset cost","POSITIVE","Reimbursements can protect economics with a lag","1_QUARTER"),)),("tenancy_ratio","ebitda_margin","POSITIVE","Colocation adds revenue with limited incremental site cost.",()),("site_additions","capex","POSITIVE","New builds consume capital before tenant loading.",()),("customer_concentration","contract_risk","POSITIVE","Dependence on few operators magnifies renewal and credit risk.",()),("contract_duration","revenue_visibility","POSITIVE","Long leases support predictable rental cash flow.",()),("ebitda","free_cash_flow","POSITIVE","Contracted earnings convert after maintenance and growth capex.",()),("net_debt","equity_value","NEGATIVE","Infrastructure leverage reduces equity value.",()),("5g_rollout","tenant_additions","CONDITIONAL","Densification can create colocations.",(CounterEffect("Active sharing reduces incremental tenancy","NEGATIVE","Operators can share infrastructure","MULTI_YEAR"),)),("renewal_rate","terminal_value","POSITIVE","High renewal supports durable terminal cash flow.",()))
    return [CausalRelationship(relationship_id=f"CRE-TECH2G-{i:02d}",cause=a,effect=b,direction=d,relationship_type="CAUSAL_HYPOTHESIS",epistemic_label="HYPOTHESIS",industry="Telecom Infrastructure and Towers",company_id=company_id,strength="MEDIUM",confidence=.58,time_lag="2_QUARTERS",mechanism=m,counter_effects=c,source_quality="UNVALIDATED",status="PROPOSED",created_by="phase_2g_code_reviewed_curriculum") for i,(a,b,d,m,c) in enumerate(rows,1)]
