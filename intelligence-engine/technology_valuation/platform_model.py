"""Phase 2C Internet Platforms and Marketplaces institutional curriculum."""
from __future__ import annotations
from financials_valuation.schema import KPIKnowledge, SectorValuationModel, ValuationMethodRule
from technology_valuation.model import TECHNOLOGY_PARENT_SECTOR

PLATFORM_VERSION="technology-valuation-v2c.0.0"

def _k(key,name,definition,formula,unit,why,causal,valuation,limitations):
    return KPIKnowledge(key,name,definition,formula,unit,"Quarterly/Annual",("Regulatory filing","NSE/BSE filing","Audited financial statements","Official company disclosure"),why,(causal,),valuation,limitations,("VALIDATED","TRUSTED"))

def _m(method,tier,reason,required,failure):
    return ValuationMethodRule(method,tier,reason,required,(reason,),("Sensitive to platform scope, incentives, liquidity and PIT assumptions.",),(failure,))

PLATFORM_KPIS=(
    _k("gmv","Gross Merchandise Value","Value transacted through the platform before cancellations and returns.","reported transacted value","currency","Measures activity, not recognized revenue.","buyers x frequency x order value -> GMV","Denominator for EV/GMV only with take-rate context.","Definitions, returns and first-party sales vary."),
    _k("gmv_growth","GMV Growth","Change in platform transaction value.","closing GMV / opening GMV - 1","decimal","Separates transaction growth from monetization.","buyers, frequency and order value -> GMV growth","Feeds scenario revenue.","Acquisitions and inflation require separation."),
    _k("take_rate","Take Rate","Platform revenue divided by GMV.","revenue / GMV","decimal","Measures monetization of activity.","fees and mix -> take rate -> revenue","Links GMV to revenue.","First-party revenue can make this meaningless."),
    _k("active_buyers","Active Buyers","Unique transacting buyers in the disclosed period.","reported active buyers","users","Measures demand-side liquidity.","acquisition and retention -> active buyers","Supports network and cohort analysis.","Active-window definitions vary."),
    _k("active_sellers","Active Sellers","Unique supply participants in the disclosed period.","reported active sellers","users","Measures supply depth.","seller acquisition and retention -> selection","Supports liquidity assessment.","Seller quality matters more than raw count."),
    _k("order_frequency","Order Frequency","Transactions per active buyer.","orders / active buyers","orders_per_buyer","Shows engagement and repeat behavior.","retention and utility -> frequency -> GMV","Tests growth quality.","Seasonality and cohort mix matter."),
    _k("repeat_rate","Repeat Purchase Rate","Share of customers repeating within a defined window.","repeat customers / eligible customers","decimal","Distinguishes durable utility from paid acquisition.","experience -> repeat rate -> lower CAC burden","Supports durability.","Window and cohort definitions must match."),
    _k("contribution_margin","Contribution Margin","Revenue after variable fulfillment, payment, incentives and support costs.","contribution profit / revenue","decimal","Tests transaction-level economics.","take rate - variable costs - incentives -> contribution","Controls valuation of growth.","Company definitions often exclude different costs."),
    _k("platform_cac","Customer Acquisition Cost","Sales and marketing spend per new customer.","sales and marketing / new customers","currency_per_customer","Measures acquisition efficiency.","marketing -> new customers -> repeat use","Supports unit economics.","Brand spend and organic acquisition allocations vary."),
    _k("seller_concentration","Seller Concentration","Share of GMV from the largest sellers.","top seller GMV / total GMV","decimal","Concentrated supply weakens platform bargaining power.","concentration -> bargaining and leakage risk","Raises durability risk.","Requires consistent seller grouping."),
    _k("refund_cancellation_rate","Refund and Cancellation Rate","Share of orders cancelled or refunded.","cancelled and refunded orders / gross orders","decimal","Tests service quality and true economic volume.","quality failures -> refunds -> lower net GMV","Reduces monetizable activity.","Policy and category mix differ."),
    _k("fcf_margin","FCF Margin","Free cash flow divided by revenue.","FCF / revenue","decimal","Tests whether platform scale becomes self-funded.","contribution profit - fixed costs - capex -> FCF","Supports mature valuation.","Working capital and SBC require adjustment."),
)

PLATFORM_METHODS=(
    _m("EV_SALES","PRIMARY","EV/revenue fits monetizing platforms when revenue recognition and contribution economics are verified.",("enterprise_value","revenue"),"Revenue scope or contribution economics are unreliable"),
    _m("EV_GMV","SECONDARY","EV/GMV is only a transaction-scale cross-check alongside take rate.",("enterprise_value","gmv"),"Used without take-rate and revenue-recognition context"),
    _m("EV_GROSS_PROFIT","SECONDARY","EV/gross profit controls for first-party and pass-through differences.",("enterprise_value","gross_profit"),"Gross profit is unreliable"),
    _m("GORDON_DCF","MATURE_SECONDARY","DCF fits platforms with supportable normalized cash economics.",("next_fcf","discount_rate","terminal_growth"),"Cash flows or terminal economics are unstable"),
)

PLATFORM_MODEL=SectorValuationModel(
    sector_id=f"{TECHNOLOGY_PARENT_SECTOR}.INTERNET_PLATFORMS_MARKETPLACES",sector_name="Internet Platforms and Marketplaces",subsector="INTERNET_PLATFORMS_MARKETPLACES",
    business_model_types=("Internet Platform","Marketplace","Digital Marketplace"),
    economic_structure="Buyers and sellers create transaction liquidity. Active participants, frequency and order value drive GMV; take rate converts GMV to revenue; incentives, payments, fulfillment, trust and support determine contribution profit and cash flow.",
    revenue_drivers=("Active buyers","Active sellers","Order frequency","Average order value","Take rate","Advertising","Subscriptions","Payments and ancillary services"),
    cost_drivers=("Customer acquisition","Seller incentives","Fulfillment","Payments","Trust and safety","Refunds","Technology","Support"),
    capital_structure="Often asset-light at the platform layer, but fulfillment assets, working capital, acquisitions, incentives and dilution can materially change economics.",
    regulatory_characteristics=("Competition law","Consumer protection","Data privacy","Payments regulation","Gig-worker rules","Tax collection","Foreign investment"),
    key_kpis=PLATFORM_KPIS,valuation_methods=PLATFORM_METHODS,
    valuation_drivers=("GMV growth","Take rate","Repeat rate","Marketplace liquidity","Contribution margin","CAC","FCF margin","Network durability"),
    valuation_risks=("Disintermediation","Subsidized growth","Weak repeat behavior","Seller concentration","Fraud","Regulation","First-party inventory risk","Take-rate pressure","SBC dilution"),
    scenario_variables=("GMV growth","Take rate","Target EV/revenue"),
    monitoring_variables=("GMV growth","Active buyers","Active sellers","Order frequency","Repeat rate","Take rate","Contribution margin","CAC","Refund rate","FCF margin"),
    common_analytical_errors=("Treating GMV as revenue","Calling user growth a network effect","Ignoring incentives","Using EV/GMV without take rate","Ignoring cohort retention","Assuming higher take rate is always positive"),
    evidence_sources=("Regulatory filings","Audited annual reports","NSE","BSE","Official results","Investor presentations","Licensed transcripts"),
    effective_date="2026-08-15",confidence=.86,validation_status="VALIDATED",version=PLATFORM_VERSION)
