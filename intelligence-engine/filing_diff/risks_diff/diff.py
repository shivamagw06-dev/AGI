"""Risk register diff — added / removed / promoted."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.comparator.materiality import classify_materiality, thesis_impact
from filing_diff.schema import ChangeRecord


def risks_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    qual = ctx.get("qual_by_period") or {}
    cur = set((qual.get(cur_p) or {}).get("risks") or [])
    prev = set((qual.get(prev_p) or {}).get("risks") or [])
    ticker = ctx["ticker"]
    out: list[ChangeRecord] = []
    for r in sorted(cur - prev):
        change_type = "risk_added"
        mat = classify_materiality(
            metric=r, domain="risks", previous=False, current=True, change_type=change_type
        )
        cause = explain_change(
            metric=r,
            change_type=change_type,
            previous="absent",
            current="present",
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:risk:add:{r}",
                ticker=ticker,
                domain="risks",
                metric=r,
                change_type=change_type,
                previous_value="absent",
                current_value="present",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="risk_factors",
                materiality=mat if mat != "ignore" else "high",
                thesis_impact=thesis_impact("high", change_type, r, False, True),
                confidence=0.8,
                **cause,
            )
        )
    for r in sorted(prev - cur):
        change_type = "risk_removed"
        mat = "medium"
        cause = explain_change(
            metric=r,
            change_type=change_type,
            previous="present",
            current="absent",
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:risk:rem:{r}",
                ticker=ticker,
                domain="risks",
                metric=r,
                change_type=change_type,
                previous_value="present",
                current_value="absent",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="risk_factors",
                materiality=mat,
                thesis_impact=thesis_impact(mat, change_type, r, True, False),
                confidence=0.75,
                **cause,
            )
        )
    return out
