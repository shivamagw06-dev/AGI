"""Authoritative Consumer subsector models; explanations never replace AFE math."""
from __future__ import annotations

from financials_valuation.schema import KPIKnowledge, SectorValuationModel, ValuationMethodRule

VERSION = "consumer-valuation-v3.0.0"
PARENT_SECTOR = "CONSUMER"


def k(key: str, name: str, why: str, causal: str, limitation: str = "Definitions and scope can differ by company.") -> KPIKnowledge:
    return KPIKnowledge(key, name, why, "reported or AFE-calculated from cited inputs", "context_specific",
        "Quarterly/Annual", ("Audited filing", "NSE/BSE filing", "Official results", "Investor presentation"),
        why, (causal,), "Changes expected revenue, margins, cash conversion, ROIC and the appropriate valuation range.",
        limitation, ("VALIDATED", "TRUSTED"))


def m(method: str, tier: str, reason: str, required: tuple[str, ...]) -> ValuationMethodRule:
    return ValuationMethodRule(method, tier, reason, required, (reason,),
        ("Requires normalized point-in-time inputs and comparable accounting.",),
        ("Missing or stale inputs", "Structurally negative denominator", "Materially unnormalized earnings"))


COMMON = (
    k("revenue_growth", "Revenue Growth", "Starting output measure requiring decomposition.", "demand -> volume + price + mix -> revenue"),
    k("gross_margin", "Gross Margin", "Measures pricing, mix and input-cost transmission.", "price/mix - input cost -> gross margin"),
    k("ebitda_margin", "EBITDA Margin", "Captures gross margin and operating leverage.", "gross margin - operating cost -> EBITDA margin"),
    k("fcf_margin", "FCF Margin", "Tests whether earnings convert to cash.", "EBITDA -> working capital -> capex -> FCF"),
    k("roce", "ROCE", "Tests whether growth creates value after capital employed.", "margin x capital turns -> ROCE"),
    k("inventory_days", "Inventory Days", "Reveals demand, assortment and cash-conversion risk.", "inventory growth -> working capital -> FCF"),
)

CONFIG = {
"FMCG": dict(name="FMCG", types=("Branded staples","Foods and beverages","Household and personal care"),
 drivers=("Volume growth","Price/mix","Market share","Distribution","Rural and urban demand","Premiumization","Commodity costs","Advertising"),
 kpis=(k("volume_growth","Volume Growth","Separates physical demand from inflation.","demand -> volume -> revenue"),k("price_mix_growth","Price/Mix Growth","Separates realization and premiumization from units.","pricing + mix -> realization -> gross margin"),k("market_share","Market Share","Tests competitive growth quality.","distribution + brand -> share -> volume"),k("advertising_spend","Advertising Spend","Measures reinvestment behind brand demand.","advertising -> salience -> demand with lag"),k("distribution_reach","Distribution Reach","Measures availability and route-to-market strength.","distribution -> availability -> volume")),
 methods=(m("PRICE_TO_EARNINGS","PRIMARY","Mature branded earnings support normalized P/E.",( "market_price","normalized_eps")),m("EV_EBITDA","CROSS_CHECK","Cross-checks operating value independent of capital structure.",( "enterprise_value","ebitda")),m("GORDON_DCF","SECONDARY","Links brand durability, reinvestment and FCF.",( "next_fcf","discount_rate","terminal_growth")),m("FCF_YIELD","SECONDARY","Tests cash support for quoted price.",( "fcf_per_share","market_price"))),
 errors=("Treating value growth as volume growth","Assuming premiumization without mix evidence","Ignoring commodity and advertising reinvestment")),
"CONSUMER_DURABLES": dict(name="Consumer Durables", types=("Appliances","White goods","Consumer electricals","Electronics"),
 drivers=("Volume","ASP","Replacement cycle","Penetration","Housing and income cycle","Financing","Capacity","Commodity costs"),
 kpis=(k("volume_growth","Volume Growth","Measures unit demand.","income + replacement -> units"),k("asp","Average Selling Price","Captures pricing and product mix.","price + mix -> ASP"),k("capacity_utilization","Capacity Utilization","Connects demand with operating leverage.","volume -> utilization -> margin"),k("dealer_inventory","Dealer Inventory","Flags channel stuffing or demand weakness.","sell-in - sell-through -> dealer inventory"),k("market_share","Market Share","Tests competitive position.","distribution + product -> share")),
 methods=(m("PRICE_TO_EARNINGS","PRIMARY","Normalized profitable durable earnings support P/E.",( "market_price","normalized_eps")),m("EV_EBITDA","PRIMARY_CROSS_CHECK","Useful across capital structures and cycles.",( "enterprise_value","ebitda")),m("GORDON_DCF","SECONDARY","Captures replacement growth and reinvestment.",( "next_fcf","discount_rate","terminal_growth"))),
 errors=("Ignoring channel inventory","Treating replacement demand as structural growth","Ignoring commodity pass-through lags")),
"RETAIL": dict(name="Retail", types=("Grocery","Fashion","Specialty","Value retail","Premium retail","Omnichannel"),
 drivers=("Same-store sales","Store additions","Footfall","Conversion","Basket size","Sales density","Store maturity","Private label","Rent","Inventory turns"),
 kpis=(k("sssg","Same-store Sales Growth","Separates existing-store demand from expansion.","footfall x conversion x basket -> SSSG"),k("store_count","Store Count","Measures physical network scale.","net additions -> retail space"),k("sales_per_store","Sales per Store","Measures unit productivity.","transactions x basket -> sales/store"),k("sales_density","Sales Density","Tests space productivity.","revenue / area -> store economics"),k("lease_adjusted_leverage","Lease-adjusted Leverage","Captures fixed rent obligations.","leases + debt -> fixed claims")),
 methods=(m("EV_EBITDA","PRIMARY","Operating multiple suits scaled retail with lease consistency.",( "enterprise_value","ebitda")),m("EV_SALES","SUPPLEMENTARY","Useful only with margin and maturity context.",( "enterprise_value","revenue")),m("PRICE_TO_EARNINGS","CROSS_CHECK","Applies when earnings are normalized.",( "market_price","normalized_eps")),m("GORDON_DCF","SECONDARY","Captures store maturation, capex and leases.",( "next_fcf","discount_rate","terminal_growth"))),
 errors=("Treating store-led growth as SSSG","Ignoring leases","Ignoring maturation and cannibalization")),
"QSR": dict(name="Restaurants / QSR", types=("Company-operated QSR","Franchised QSR","Casual dining","Delivery-led restaurants"),
 drivers=("SSSG","Traffic","Average order value","Store additions","Delivery mix","Franchise mix","Food inflation","Labour","Rent","Store maturity"),
 kpis=(k("sssg","Same-store Sales Growth","Measures mature network demand.","traffic x average ticket -> SSSG"),k("average_order_value","Average Order Value","Separates ticket from transaction growth.","price + mix -> AOV"),k("store_level_ebitda","Store-level EBITDA","Measures unit economics before corporate overhead.","store sales - food - labour - rent -> store EBITDA"),k("payback_period","Store Payback","Tests expansion capital efficiency.","store capex / store cash flow -> payback"),k("restaurant_margin","Restaurant Margin","Measures unit-level profitability.","SSSG + input costs -> restaurant margin")),
 methods=(m("EV_EBITDA","PRIMARY","Captures network operating economics.",( "enterprise_value","ebitda")),m("EV_SALES","SUPPLEMENTARY","Requires mature-store margin context.",( "enterprise_value","revenue")),m("GORDON_DCF","SECONDARY","Captures openings, maturation and capex.",( "next_fcf","discount_rate","terminal_growth"))),
 errors=("Treating openings as same-store growth","Ignoring immature-store losses","Ignoring franchise versus company-operated mix")),
"HOTELS_HOSPITALITY": dict(name="Hotels & Hospitality", types=("Owned hotels","Managed hotels","Luxury","Business","Budget","Resorts"),
 drivers=("Occupancy","ADR","RevPAR","Room supply","Travel demand","Events","Seasonality","Room additions","Owned/managed mix"),
 kpis=(k("occupancy","Occupancy","Measures utilized room capacity.","demand / available rooms -> occupancy"),k("adr","Average Daily Rate","Measures realized room pricing.","pricing + mix -> ADR"),k("revpar","RevPAR","Combines price and utilization.","ADR x occupancy -> RevPAR"),k("rooms","Rooms / Keys","Measures physical and managed scale.","rooms x days -> capacity"),k("ebitda_per_room","EBITDA per Room","Compares asset productivity.","hotel EBITDA / rooms")),
 methods=(m("EV_EBITDA","PRIMARY","Captures cyclical operating earnings.",( "enterprise_value","ebitda")),m("CONSUMER_EV_PER_KEY","CROSS_CHECK","Compares asset/network value per room.",( "enterprise_value","rooms")),m("NAV","SECONDARY","Relevant for owned real estate.",( "asset_value","net_debt")),m("GORDON_DCF","SECONDARY","Captures supply, cycle and owned/managed mix.",( "next_fcf","discount_rate","terminal_growth"))),
 errors=("Treating revenue growth as demand without ADR/occupancy split","Ignoring room supply","Mixing owned and managed economics")),
"TEXTILES_APPAREL": dict(name="Textiles / Apparel", types=("Yarn","Fabric","Processing","Garments","Branded apparel"),
 drivers=("Raw-material prices","Export demand","Volume","ASP","Utilization","Labour","Power","Freight","FX","Inventory cycle","Brand premium"),
 kpis=(k("volume_growth","Volume Growth","Separates physical demand from price and FX.","demand -> volume"),k("realization","Realization","Captures pricing, mix and currency.","ASP + FX -> realization"),k("capacity_utilization","Capacity Utilization","Measures cycle and operating leverage.","orders -> utilization -> margin"),k("export_share","Export Share","Measures global and currency exposure.","export demand + FX -> revenue"),k("normalized_margin","Normalized Margin","Prevents peak-cycle extrapolation.","mid-cycle spread -> normalized earnings")),
 methods=(m("EV_EBITDA","PRIMARY","Useful with normalized-cycle EBITDA.",( "enterprise_value","ebitda")),m("PRICE_TO_EARNINGS","CROSS_CHECK","Requires normalized earnings.",( "market_price","normalized_eps")),m("EV_SALES","SUPPLEMENTARY","Only with margin context.",( "enterprise_value","revenue"))),
 errors=("Capitalizing peak-cycle earnings","Treating FX growth as volume","Ignoring inventory losses and working capital")),
"FOOTWEAR": dict(name="Footwear", types=("Branded footwear","Retail-led footwear","Wholesale footwear","Athleisure"),
 drivers=("Pairs sold","ASP","Premiumization","Market share","Stores","SSSG","Distribution","E-commerce","Raw materials","Inventory"),
 kpis=(k("pairs_sold","Pairs Sold","Measures physical demand.","distribution + demand -> pairs"),k("asp","Average Selling Price","Measures price and product mix.","brand + premium mix -> ASP"),k("sssg","Same-store Sales Growth","Separates network productivity from additions.","footfall x conversion x ASP -> SSSG"),k("sales_per_store","Sales per Store","Measures unit productivity.","transactions x ASP -> sales/store"),k("inventory_turns","Inventory Turns","Measures assortment and cash quality.","sales / inventory -> turns")),
 methods=(m("PRICE_TO_EARNINGS","PRIMARY","Fits profitable branded consumer earnings.",( "market_price","normalized_eps")),m("EV_EBITDA","CROSS_CHECK","Cross-checks operating value.",( "enterprise_value","ebitda")),m("GORDON_DCF","SECONDARY","Captures store/distribution investment and FCF.",( "next_fcf","discount_rate","terminal_growth"))),
 errors=("Treating store additions as organic demand","Ignoring inventory ageing","Assuming ASP growth is pure pricing")),
"JEWELLERY": dict(name="Jewellery", types=("Branded retail jewellery","Gold-heavy retail","Diamond manufacturing","Asset-light jewellery"),
 drivers=("Gold price","Volume","Realization","SSSG","Stores","Making charges","Inventory","Gold-on-loan","Wedding demand","Organized penetration","Market share"),
 kpis=(k("jewellery_volume","Jewellery Volume","Separates real demand from gold inflation.","demand + affordability -> volume"),k("gold_price","Gold Price","Drives ticket size, affordability and working capital.","gold price -> realization + inventory funding"),k("sssg","Same-store Sales Growth","Measures existing-store growth but still needs price/volume split.","volume + gold price + mix -> SSSG"),k("making_charge","Making Charges","Measures value-add and pricing economics.","design + brand -> making charge -> margin"),k("gold_inventory","Gold Inventory","Measures funding and price exposure.","gold price x inventory -> working capital")),
 methods=(m("PRICE_TO_EARNINGS","PRIMARY","Fits normalized branded retail earnings.",( "market_price","normalized_eps")),m("EV_EBITDA","CROSS_CHECK","Cross-checks operating value and leverage.",( "enterprise_value","ebitda")),m("GORDON_DCF","SECONDARY","Captures inventory funding and cash conversion.",( "next_fcf","discount_rate","terminal_growth"))),
 errors=("Treating gold-price inflation as demand","Ignoring gold-on-loan and inventory funding","Ignoring volume and making-charge mix")),
}


def _model(subsector: str, cfg: dict) -> SectorValuationModel:
    return SectorValuationModel(
        sector_id=f"CONSUMER.{subsector}", sector_name=cfg["name"], subsector=subsector,
        business_model_types=cfg["types"], economic_structure="Demand converts through volume, price and mix into revenue; gross margin, operating leverage, working capital and capex determine FCF and ROCE.",
        revenue_drivers=cfg["drivers"], cost_drivers=("Raw materials","Employee cost","Rent and leases","Distribution","Advertising","Freight","Energy"),
        capital_structure="Subsector-specific working capital, leases, stores, owned assets and capex must be reflected consistently.",
        regulatory_characteristics=("Consumer protection","Product standards","GST and duties","Labour","Environmental and sourcing rules"),
        key_kpis=COMMON+cfg["kpis"], valuation_methods=cfg["methods"], valuation_drivers=cfg["drivers"],
        valuation_risks=("Demand slowdown","Input inflation","Price elasticity","Inventory","Working capital","Leverage","Competitive intensity"),
        scenario_variables=tuple(k.key for k in cfg["kpis"][:3])+("gross_margin","ebitda_margin","fcf"),
        monitoring_variables=tuple(k.name for k in cfg["kpis"])+( "Gross Margin","Inventory Days","FCF Conversion","ROCE"),
        common_analytical_errors=cfg["errors"], evidence_sources=("Audited filings","NSE/BSE","Official results","Investor presentations","Licensed industry data"),
        effective_date="2026-08-16", confidence=.82, validation_status="IMPLEMENTED_NOT_RESEARCH_VALIDATED", version=VERSION)


MODELS = {key:_model(key,cfg) for key,cfg in CONFIG.items()}

CAUSAL_TEMPLATES = {
    "FMCG": (("commodity_cost","gross_margin","pricing","volume","ebitda","fcf"),("premium_mix","realization","gross_margin","roic")),
    "CONSUMER_DURABLES": (("income_and_replacement","volume","utilization","ebitda","fcf"),("commodity_cost","pricing","volume","margin")),
    "RETAIL": (("footfall","transactions","revenue","sales_density","roce"),("store_additions","rent_and_capex","maturation","fcf")),
    "QSR": (("traffic","transactions","aov","sssg","store_ebitda","fcf"),("food_inflation","restaurant_margin","pricing","traffic")),
    "HOTELS_HOSPITALITY": (("demand","occupancy","adr","revpar","ebitda","fcf"),("room_supply","occupancy","adr","revpar")),
    "TEXTILES_APPAREL": (("raw_material_price","gross_margin","ebitda"),("export_demand","volume","fx","realization","fcf")),
    "FOOTWEAR": (("brand_strength","pricing_power","asp","gross_margin","roce"),("distribution","volume","working_capital","fcf")),
    "JEWELLERY": (("gold_price","ticket_size","revenue","working_capital","fcf"),("organized_penetration","market_share","store_productivity","roce")),
}
