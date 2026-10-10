"""Guidance diff — raised / maintained / lowered / withdrawn."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.comparator.materiality import classify_materiality, thesis_impact
from filing_diff.schema import ChangeRecord


def guidance_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    qual = ctx.get("qual_by_period") or {}
    prev_g = (qual.get(prev_p) or {}).get("guidance_status")
    cur_g = (qual.get(cur_p) or {}).get("guidance_status")
    if not prev_g and not cur_g:
        return []
    if prev_g == cur_g:
        # still emit maintained as informational medium/low — not ignore if explicit
        change_type = "maintained"
        mat = "medium"
    else:
        change_type = str(cur_g or "unknown")
        if change_type == "reduced":
            change_type = "lowered"
        mat = classify_materiality(
            metric="Guidance_Status",
            domain="guidance",
            previous=prev_g,
            current=cur_g,
            change_type=change_type,
        )
    cause = explain_change(
        metric="Guidance_Status",
        change_type=change_type,
        previous=prev_g,
        current=cur_g,
        previous_period=prev_p,
        current_period=cur_p,
    )
    return [
        ChangeRecord(
            change_id=f"{ctx['ticker']}:guidance:{prev_p}->{cur_p}",
            ticker=ctx["ticker"],
            domain="guidance",
            metric="Guidance_Status",
            change_type=change_type,
            previous_value=prev_g,
            current_value=cur_g,
            previous_period=prev_p,
            current_period=cur_p,
            previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
            current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
            section="guidance",
            materiality=mat,
            thesis_impact=thesis_impact(mat, change_type, "Guidance_Status", prev_g, cur_g),
            confidence=0.85,
            **cause,
        )
    ]
