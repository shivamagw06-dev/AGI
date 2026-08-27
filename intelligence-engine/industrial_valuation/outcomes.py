"""Reviewed Phase 4 outcome candidates; no automatic framework promotion."""
from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from industrial_valuation.models import MODELS
def build_industrial_outcome(*,company_id:str,subsector:str,metric:str,predicted_value:float,actual_value:float,predicted_at:str,evaluated_at:str,source_id:str,failed_assumptions:list[str]|None=None)->dict[str,Any]:
    family=str(subsector or "").upper(); allowed={item.key for item in MODELS[family].key_kpis} if family in MODELS else set()
    if metric not in allowed:return {"status":"UNSUPPORTED_METRIC","trusted_update_allowed":False}
    try: predicted=float(predicted_value); actual=float(actual_value); datetime.fromisoformat(predicted_at.replace("Z","+00:00")); datetime.fromisoformat(evaluated_at.replace("Z","+00:00"))
    except (TypeError,ValueError):return {"status":"INVALID_INPUT","trusted_update_allowed":False}
    if not company_id or not source_id:return {"status":"DATA_UNAVAILABLE","trusted_update_allowed":False}
    error=actual-predicted
    return {"status":"PROPOSED","company_id":company_id,"subsector":family,"metric":metric,"prediction":predicted,"actual":actual,"absolute_error":error,"percentage_error":None if predicted==0 else error/abs(predicted),"predicted_at":predicted_at,"evaluated_at":evaluated_at,"source_id":source_id,"failed_assumptions":failed_assumptions or [],"review_status":"pending","trusted_update_allowed":False,"automatic_framework_change":False,"created_at":datetime.now(timezone.utc).isoformat()}
