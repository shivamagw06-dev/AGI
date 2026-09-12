"""Capital allocation diff."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.comparator.materiality import classify_materiality, thesis_impact
from filing_diff.schema import ChangeRecord

TYPE_MAP = {
    "Buybacks": "buyback",
    "Dividends": "dividend_action",
    "Acquisitions": "acquisition_announced",
    "Capex": "capex_change",
    "Debt_Reduction": "debt_repayment",
    "Capital_Raises": "capital_raise",
    "Organic_Investment": "organic_investment",
    "Capital_Buffer": "capital_buffer_policy",
}


def capital_allocation_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    qual = ctx.get("qual_by_period") or {}
    cur = set((qual.get(cur_p) or {}).get("capital") or [])
    prev = set((qual.get(prev_p) or {}).get("capital") or [])
    # ignore rationale-only metric
    cur.discard("Allocation_Rationale")
    prev.discard("Allocation_Rationale")
    ticker = ctx["ticker"]
    out: list[ChangeRecord] = []
    for item in sorted(cur - prev):
        change_type = TYPE_MAP.get(item, "capital_action_added")
        mat = classify_materiality(
            metric=item, domain="capital", previous=False, current=True, change_type=change_type
        )
        cause = explain_change(
            metric=item,
            change_type=change_type,
            previous="absent",
            current="present",
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:cap:add:{item}",
                ticker=ticker,
                domain="capital",
                metric=item,
                change_type=change_type,
                previous_value="absent",
                current_value="present",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="capital_allocation",
                materiality=mat if mat != "ignore" else "medium",
                thesis_impact=thesis_impact(mat, change_type, item, False, True),
                confidence=0.78,
                **cause,
            )
        )
    for item in sorted(prev - cur):
        change_type = "capital_action_removed"
        mat = "medium"
        cause = explain_change(
            metric=item,
            change_type=change_type,
            previous="present",
            current="absent",
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:cap:rem:{item}",
                ticker=ticker,
                domain="capital",
                metric=item,
                change_type=change_type,
                previous_value="present",
                current_value="absent",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="capital_allocation",
                materiality=mat,
                thesis_impact="needs_committee_review",
                confidence=0.7,
                **cause,
            )
        )
    return out
