"""Statement diff — financial metric changes."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.comparator.materiality import classify_materiality, thesis_impact
from filing_diff.schema import ChangeRecord

CHANGE_MAP = {
    "NIM": ("margin_compression", "margin_expansion"),
    "Operating_Margin": ("margin_compression", "margin_expansion"),
    "EBIT_Margin": ("margin_compression", "margin_expansion"),
    "Revenue_Growth": ("revenue_deceleration", "revenue_acceleration"),
    "Deposits_YoY": ("revenue_deceleration", "revenue_acceleration"),
    "CASA": ("casa_decline", "casa_improvement"),
    "CET1": ("capital_ratio_decline", "capital_ratio_increase"),
    "CAR": ("capital_ratio_decline", "capital_ratio_increase"),
    "ROE": ("roe_decline", "roe_improvement"),
    "ROIC": ("roic_decline", "roic_improvement"),
    "GNPA": ("asset_quality_deterioration", "asset_quality_improvement"),
}


def statement_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    cur = (ctx.get("period_metrics") or {}).get(cur_p) or {}
    prev = (ctx.get("period_metrics") or {}).get(prev_p) or {}
    src_cur = (ctx.get("period_sources") or {}).get(cur_p) or {}
    src_prev = (ctx.get("period_sources") or {}).get(prev_p) or {}
    ticker = ctx["ticker"]
    out: list[ChangeRecord] = []
    for metric, cur_v in cur.items():
        if metric not in prev:
            continue
        prev_v = prev[metric]
        if not isinstance(cur_v, (int, float)) or not isinstance(prev_v, (int, float)):
            continue
        if float(cur_v) == float(prev_v):
            continue
        down, up = CHANGE_MAP.get(metric, ("decline", "increase"))
        # GNPA lower is better
        if metric in {"GNPA", "NNPA", "Credit_Cost"}:
            change_type = up if cur_v < prev_v else down
        else:
            change_type = up if cur_v > prev_v else down
        mat = classify_materiality(
            metric=metric, domain="statement", previous=prev_v, current=cur_v, change_type=change_type
        )
        if mat == "ignore":
            continue
        cause = explain_change(
            metric=metric,
            change_type=change_type,
            previous=prev_v,
            current=cur_v,
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:stmt:{metric}:{prev_p}->{cur_p}",
                ticker=ticker,
                domain="statement",
                metric=metric,
                change_type=change_type,
                previous_value=prev_v,
                current_value=cur_v,
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=str(src_prev.get(metric) or ""),
                current_doc_id=str(src_cur.get(metric) or ""),
                section="financial_statements",
                evidence_tier=1,
                materiality=mat,
                thesis_impact=thesis_impact(mat, change_type, metric, prev_v, cur_v),
                confidence=0.9,
                **cause,
            )
        )
    return out
