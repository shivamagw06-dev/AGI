"""Notes / accounting policy diff."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.comparator.materiality import classify_materiality, thesis_impact
from filing_diff.schema import ChangeRecord


def notes_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    return _set_diff(ctx, key="notes", domain="notes", prefix="accounting")


def accounting_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    # alias domain for accounting-specific labeling
    rows = notes_diff(ctx)
    for r in rows:
        r.domain = "accounting"
        if "Impairment" in r.metric:
            r.change_type = "impairment_added" if r.change_type == "policy_added" else "impairment_removed"
    return rows


def _set_diff(ctx: dict[str, Any], *, key: str, domain: str, prefix: str) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    qual = ctx.get("qual_by_period") or {}
    cur = set((qual.get(cur_p) or {}).get(key) or [])
    prev = set((qual.get(prev_p) or {}).get(key) or [])
    ticker = ctx["ticker"]
    out: list[ChangeRecord] = []
    for item in sorted(cur - prev):
        change_type = "policy_added"
        mat = classify_materiality(
            metric=item, domain=domain, previous=False, current=True, change_type=change_type
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
                change_id=f"{ticker}:{prefix}:add:{item}",
                ticker=ticker,
                domain=domain,
                metric=item,
                change_type=change_type,
                previous_value="absent",
                current_value="present",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="notes",
                materiality=mat,
                thesis_impact=thesis_impact(mat, change_type, item, False, True),
                confidence=0.7,
                **cause,
            )
        )
    for item in sorted(prev - cur):
        change_type = "policy_removed"
        mat = classify_materiality(
            metric=item, domain=domain, previous=True, current=False, change_type=change_type
        )
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
                change_id=f"{ticker}:{prefix}:rem:{item}",
                ticker=ticker,
                domain=domain,
                metric=item,
                change_type=change_type,
                previous_value="present",
                current_value="absent",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="notes",
                materiality=mat,
                thesis_impact=thesis_impact(mat, change_type, item, True, False),
                confidence=0.7,
                **cause,
            )
        )
    return out
