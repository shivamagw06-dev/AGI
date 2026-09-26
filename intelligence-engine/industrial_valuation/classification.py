"""Evidence-labelled industrial subsector classification."""
from __future__ import annotations
from typing import Any

COHORTS = {
    "CAPITAL_GOODS":{"SIEMENS","ABB","BHEL","CUMMINSIND","THERMAX"},
    "ENGINEERING_EPC":{"LT","KEC","KALPATPOWR","NCC"},
    "INFRASTRUCTURE":{"ADANIPORTS","GMRINFRA","GMRAIRPORT","IRB"},
    "CONSTRUCTION":{"NBCC","PSPPROJECT","CAPACITE","KNRCON"},
    "CEMENT":{"ULTRACEMCO","AMBUJACEM","ACC","SHREECEM","DALBHARAT"},
    "STEEL":{"TATASTEEL","JSWSTEEL","SAIL","JINDALSTEL"},
    "METALS_MINING":{"HINDALCO","VEDL","HINDZINC","NMDC","NATIONALUM"},
    "CHEMICALS":{"TATACHEM","GNFC","DEEPAKFERT"},
    "SPECIALTY_CHEMICALS":{"PIIND","SRF","DEEPAKNTR","NAVINFLUOR","CLEAN","FLUOROCHEM"},
    "AUTO_AUTO_COMPONENTS":{"MARUTI","M&M","TATAMOTORS","BAJAJ-AUTO","EICHERMOT","MOTHERSON","BHARATFORG","BOSCHLTD","SONACOMS"},
    "DEFENCE_AEROSPACE":{"HAL","BEL","BDL","MAZDOCK","COCHINSHIP","ZENTEC"},
    "RAIL_TRANSPORT_EQUIPMENT":{"TITAGARH","TEXRAIL","BEML","IRCON","RVNL"},
    "ELECTRICAL_EQUIPMENT":{"CGPOWER","POWERINDIA","POLYCAB","KEI"},
    "RENEWABLE_EQUIPMENT":{"SUZLON","INOXWIND","WAAREEENER","PREMIERENE"},
    "PACKAGING":{"UFLEX","EPL","TCPLPACK"},
    "PAPER_PULP":{"JKPAPER","WSTCSTPAPR","TNPL","ANDHRAPAP"},
}

ALIASES={"CAPITAL_GOODS_INDUSTRIAL_MACHINERY":"CAPITAL_GOODS","EPC":"ENGINEERING_EPC","METALS_AND_MINING":"METALS_MINING","AUTO":"AUTO_AUTO_COMPONENTS","AUTO_COMPONENTS":"AUTO_AUTO_COMPONENTS","DEFENCE":"DEFENCE_AEROSPACE","RAILWAYS":"RAIL_TRANSPORT_EQUIPMENT","RENEWABLE_ENERGY_EQUIPMENT":"RENEWABLE_EQUIPMENT","PAPER":"PAPER_PULP"}

def classify_industrial(company: dict[str,Any]) -> dict[str,Any]:
    symbol=str(company.get("symbol") or company.get("company_id") or "").upper()
    explicit=str(company.get("industrial_subsector") or company.get("subsector") or "").upper().replace(" ","_").replace("&","AND")
    explicit=ALIASES.get(explicit,explicit)
    if explicit in COHORTS:
        return {"status":"CLASSIFIED","parent_sector":"INDUSTRIALS_MANUFACTURING_REAL_ASSETS","subsector":explicit,"model_family":explicit,"source":"company_master.industrial_subsector","confidence":.98,"effective_date":company.get("classification_effective_date")}
    matched=[family for family,symbols in COHORTS.items() if symbol in symbols]
    if len(matched)==1:
        return {"status":"CLASSIFIED","parent_sector":"INDUSTRIALS_MANUFACTURING_REAL_ASSETS","subsector":matched[0],"model_family":matched[0],"source":"phase_4_reviewed_cohort_registry","confidence":.90,"effective_date":"2026-08-16"}
    segments=company.get("segments") if isinstance(company.get("segments"),list) else []
    material=[row for row in segments if ALIASES.get(str(row.get("industrial_subsector") or "").upper(),str(row.get("industrial_subsector") or "").upper()) in COHORTS and float(row.get("revenue_share") or 0)>=.1]
    if len(material)>1:
        return {"status":"DIVERSIFIED","parent_sector":"INDUSTRIALS_MANUFACTURING_REAL_ASSETS","segments":material,"requires_sotp":True,"source":"company_segment_disclosure","confidence":.85}
    return {"status":"CLASSIFICATION_UNAVAILABLE","parent_sector":"INDUSTRIALS_MANUFACTURING_REAL_ASSETS","symbol":symbol,"confidence":0.0}
