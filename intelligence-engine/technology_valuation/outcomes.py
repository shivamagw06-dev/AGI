"""Phase 2A forecast outcome records; observations propose, never self-teach."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

TRACKED_METRICS=frozenset({"revenue_growth","constant_currency_growth","ebit_margin","fcf_margin","utilization","attrition","book_to_bill","arr_growth","nrr","grr","gross_margin","cac_payback","logo_churn","gmv_growth","take_rate","active_buyers","order_frequency","repeat_rate","contribution_margin","net_revenue_growth","return_rate","inventory_turns","advertising_arpu"})


def build_outcome_record(*, company_id: str, metric: str, predicted_value: float, actual_value: float,
                         predicted_at: str, evaluated_at: str, source_id: str,
                         failed_assumptions: list[str] | None=None) -> dict[str,Any]:
    key=str(metric or "").strip().lower()
    if key not in TRACKED_METRICS:
        return {"status":"UNSUPPORTED_METRIC","trusted_update_allowed":False}
    if not company_id or not source_id or not predicted_at or not evaluated_at:
        return {"status":"DATA_UNAVAILABLE","trusted_update_allowed":False}
    try:
        predicted=float(predicted_value); actual=float(actual_value)
        datetime.fromisoformat(predicted_at.replace("Z","+00:00")); datetime.fromisoformat(evaluated_at.replace("Z","+00:00"))
    except (TypeError,ValueError):
        return {"status":"INVALID_INPUT","trusted_update_allowed":False}
    error=actual-predicted
    pct_error=None if predicted==0 else error/abs(predicted)
    subsector="CONSUMER_INTERNET_DIGITAL_COMMERCE" if key in {"net_revenue_growth","return_rate","inventory_turns","advertising_arpu"} else "INTERNET_PLATFORMS_MARKETPLACES" if key in {"gmv_growth","take_rate","active_buyers","order_frequency","repeat_rate","contribution_margin"} else "SOFTWARE_SAAS" if key in {"arr_growth","nrr","grr","gross_margin","cac_payback","logo_churn"} else "IT_SERVICES"
    return {"status":"PROPOSED","company_id":company_id,"subsector":subsector,"metric":key,
        "prediction":predicted,"actual":actual,"absolute_error":error,"percentage_error":pct_error,
        "predicted_at":predicted_at,"evaluated_at":evaluated_at,"source_id":source_id,
        "failed_assumptions":failed_assumptions or [],"review_status":"pending",
        "learning_candidate":True,"trusted_update_allowed":False,"automatic_framework_change":False,
        "created_at":datetime.now(timezone.utc).isoformat()}
