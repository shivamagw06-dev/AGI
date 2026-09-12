"""Phase 2B Software and SaaS institutional curriculum."""
from __future__ import annotations
from financials_valuation.schema import KPIKnowledge, SectorValuationModel, ValuationMethodRule
from technology_valuation.model import TECHNOLOGY_PARENT_SECTOR

SOFTWARE_SAAS_VERSION="technology-valuation-v2b.0.0"


def _k(key,name,definition,formula,unit,why,causal,valuation,limitations):
    return KPIKnowledge(key,name,definition,formula,unit,"Quarterly/Annual",("Regulatory filing","NSE/BSE filing","Audited financial statements","Official company disclosure"),why,(causal,),valuation,limitations,("VALIDATED","TRUSTED"))


def _m(method,tier,reason,required,failure):
    return ValuationMethodRule(method,tier,reason,required,(reason,),("Sensitive to retention, margins, maturity and PIT assumptions.",),(failure,))


SOFTWARE_SAAS_KPIS=(
    _k("arr","Annual Recurring Revenue","Contracted recurring revenue normalized to an annual run rate.","validated recurring contract value annualized","currency","Recurring scale and forward visibility.","customers and contracts -> ARR","Denominator for EV/ARR.","ARR is not GAAP revenue and definitions vary."),
    _k("arr_growth","ARR Growth","Change in annual recurring revenue.","closing ARR / opening ARR - 1","decimal","Measures recurring expansion before revenue recognition.","new ARR + expansion - churn -> ARR growth","Growth is a major multiple input.","Acquisitions and currency require separation."),
    _k("nrr","Net Revenue Retention","Opening cohort ARR after churn, contraction and expansion.","(opening ARR - churn - contraction + expansion) / opening ARR","decimal","Shows installed-base growth without new customers.","retention and expansion -> NRR -> ARR growth","Durable NRR supports growth quality.","Cohort scope and currency can differ."),
    _k("grr","Gross Revenue Retention","Opening cohort ARR retained before expansion.","(opening ARR - churn - contraction) / opening ARR","decimal","Separates defensive retention from upsell.","churn and contraction -> GRR","Supports durability and downside analysis.","May exclude downsells or product migrations."),
    _k("customer_count","Customer Count","Active paying customers under the disclosed definition.","reported paying customers","customers","Separates logo growth from monetization.","new customers - lost customers -> customer count","Supports unit and market-size analysis.","Free users and subsidiaries may distort counts."),
    _k("acv","Average Contract Value","Contracted value per customer or contract.","contract value / customers","currency_per_customer","Measures customer mix and monetization.","pricing and seat expansion -> ACV","Higher durable ACV can improve CAC economics.","Enterprise and SMB mixes are not comparable."),
    _k("cac_payback","CAC Payback","Months of gross profit required to recover acquisition cost.","CAC / monthly new-customer gross profit","months","Measures growth efficiency and funding burden.","sales spend -> acquisition -> gross profit payback","Shorter payback supports value-creating growth.","Allocated CAC and sales cycles require consistency."),
    _k("ltv_cac","LTV/CAC","Estimated customer lifetime value divided by acquisition cost.","LTV / CAC","multiple","Frames unit-economic return.","retention and gross margin -> LTV/CAC","Supports sustainable reinvestment.","Highly sensitive to churn and allocation assumptions."),
    _k("gross_margin","Gross Margin","Revenue less direct delivery and infrastructure costs divided by revenue.","gross profit / revenue","decimal","Shows delivery economics before growth investment.","hosting and support costs -> gross margin","Controls comparability of revenue multiples.","Capitalized costs and pass-through revenue matter."),
    _k("rule_of_40","Rule of 40","ARR or revenue growth plus a defined profitability margin.","ARR growth + FCF margin","decimal","Balances growth and cash generation.","growth plus cash margin -> balanced quality","Supplementary multiple context.","Not a valuation method and definitions must be explicit."),
    _k("fcf_margin","FCF Margin","Free cash flow divided by revenue.","FCF / revenue","decimal","Tests self-funded growth and cash conversion.","gross profit - opex - working capital - capex -> FCF","Supports DCF and maturity assessment.","SBC and working-capital timing require adjustment."),
    _k("sbc_dilution","SBC Dilution","Stock compensation and resulting share-count dilution.","SBC / revenue plus diluted share growth","decimal","Adjusted profit can conceal economic dilution.","SBC -> dilution -> per-share value","Reduces equity value retained by existing holders.","Grant-date expense and realized dilution differ."),
)

SOFTWARE_SAAS_METHODS=(
    _m("EV_ARR","PRIMARY_RECURRING_UNPROFITABLE","EV/ARR fits recurring businesses only when ARR quality and retention are verified.",("enterprise_value","arr"),"ARR definition or retention is unreliable"),
    _m("EV_GROSS_PROFIT","PRIMARY_CROSS_CHECK","EV/gross profit controls for delivery-cost and pass-through differences.",("enterprise_value","gross_profit"),"Gross profit is unreliable"),
    _m("EV_SALES","SECONDARY","EV/sales is usable only with gross-margin, retention and cash-flow context.",("enterprise_value","revenue"),"Applied without unit-economics context"),
    _m("GORDON_DCF","MATURE_SECONDARY","DCF becomes meaningful when long-run cash economics are supportable.",("next_fcf","discount_rate","terminal_growth"),"Cash flows or terminal economics are unstable"),
    _m("TECH_PRICE_TO_EARNINGS","MATURE_ONLY","P/E fits normalized, profitable mature software.",("market_price","normalized_eps"),"Negative or unnormalized earnings"),
)

SOFTWARE_SAAS_MODEL=SectorValuationModel(
    sector_id=f"{TECHNOLOGY_PARENT_SECTOR}.SOFTWARE_SAAS",sector_name="Software and SaaS",subsector="SOFTWARE_SAAS",
    business_model_types=("Software Products","SaaS","Enterprise Software"),
    economic_structure="Customers enter subscriptions, licenses and maintenance contracts. Retention, expansion, pricing and new logos determine ARR and revenue; gross margin, CAC, R&D and sales efficiency determine operating leverage and FCF.",
    revenue_drivers=("New customers","ARR expansion","NRR and GRR","Pricing and seats","Usage","License and maintenance mix","Currency","Acquisitions"),
    cost_drivers=("Cloud and hosting","Customer support","R&D","Sales and marketing","CAC","Implementation","Stock-based compensation"),
    capital_structure="Usually capital-light, but capitalized development, acquisitions, deferred revenue and dilution affect economic value.",
    regulatory_characteristics=("Data privacy","Cybersecurity","Software licensing","Sector-specific customer regulation","Tax and cross-border data"),
    key_kpis=SOFTWARE_SAAS_KPIS,valuation_methods=SOFTWARE_SAAS_METHODS,
    valuation_drivers=("ARR growth","NRR","GRR","Gross margin","CAC payback","LTV/CAC","FCF margin","Competitive durability","SBC dilution"),
    valuation_risks=("Churn","Weak expansion","CAC inflation","Price competition","Platform dependence","Cybersecurity","Capitalized development","SBC dilution","Acquisition-driven growth"),
    scenario_variables=("ARR growth","NRR","Gross margin","FCF margin","Target EV/ARR"),
    monitoring_variables=("ARR growth","NRR","GRR","Customer growth","ACV","CAC payback","Gross margin","R&D intensity","FCF margin","SBC dilution"),
    common_analytical_errors=("Treating recurring revenue as contracted revenue","Using EV/sales without margin context","Treating Rule of 40 as valuation","Ignoring churn","Ignoring SBC","Assuming all ARR converts immediately to revenue"),
    evidence_sources=("Regulatory filings","Audited annual reports","NSE","BSE","Official results","Investor presentations","Licensed earnings transcripts"),
    effective_date="2026-08-15",confidence=.88,validation_status="VALIDATED",version=SOFTWARE_SAAS_VERSION)
