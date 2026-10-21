"""Evidence-labelled Consumer subsector classification."""
from __future__ import annotations
from typing import Any

COHORTS = {
    "FMCG": {"HINDUNILVR","ITC","NESTLEIND","DABUR","MARICO","GODREJCP","BRITANNIA","TATACONSUM"},
    "CONSUMER_DURABLES": {"HAVELLS","VOLTAS","BLUESTARCO","CROMPTON","DIXON","WHIRLPOOL","AMBER"},
    "RETAIL": {"TRENT","DMART","V2RETAIL","SHOPERSTOP","ABFRL"},
    "QSR": {"JUBLFOOD","DEVYANI","WESTLIFE","SAPPHIRE"},
    "HOTELS_HOSPITALITY": {"INDHOTEL","EIHOTEL","CHALET","LEMONTREE"},
    "TEXTILES_APPAREL": {"PAGEIND","ARVIND","WELSPUNLIV","KPRMILL","TRIDENT","VTL"},
    "FOOTWEAR": {"BATAINDIA","RELAXO","METROBRAND","CAMPUS"},
    "JEWELLERY": {"TITAN","KALYANKJIL","SENCO","TBZ"},
}


def classify_consumer(company: dict[str, Any]) -> dict[str, Any]:
    symbol=str(company.get("symbol") or company.get("company_id") or "").upper()
    explicit=str(company.get("consumer_subsector") or company.get("subsector") or "").upper().replace(" ","_")
    aliases={"HOTELS":"HOTELS_HOSPITALITY","HOSPITALITY":"HOTELS_HOSPITALITY","RESTAURANTS":"QSR","RESTAURANTS_QSR":"QSR","TEXTILES":"TEXTILES_APPAREL","APPAREL":"TEXTILES_APPAREL"}
    explicit=aliases.get(explicit,explicit)
    if explicit in COHORTS:
        return {"status":"CLASSIFIED","parent_sector":"CONSUMER","subsector":explicit,"model_family":explicit,
                "source":"company_master.consumer_subsector","confidence":.98,"effective_date":company.get("classification_effective_date")}
    matched=[key for key,values in COHORTS.items() if symbol in values]
    if len(matched)==1:
        return {"status":"CLASSIFIED","parent_sector":"CONSUMER","subsector":matched[0],"model_family":matched[0],
                "source":"phase_3_reviewed_cohort_registry","confidence":.90,"effective_date":"2026-08-16"}
    segments=company.get("segments") if isinstance(company.get("segments"),list) else []
    material=[row for row in segments if str(row.get("consumer_subsector") or "").upper() in COHORTS and float(row.get("revenue_share") or 0)>=.1]
    if len(material)>1:
        return {"status":"DIVERSIFIED","parent_sector":"CONSUMER","segments":material,"requires_sotp":True,
                "source":"company_segment_disclosure","confidence":.85}
    return {"status":"CLASSIFICATION_UNAVAILABLE","parent_sector":"CONSUMER","symbol":symbol,"confidence":0.0}
