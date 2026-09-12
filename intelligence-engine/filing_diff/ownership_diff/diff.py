"""Ownership diff."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.schema import ChangeRecord


def ownership_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    qual = ctx.get("qual_by_period") or {}
    cur = set((qual.get(cur_p) or {}).get("ownership") or [])
    prev = set((qual.get(prev_p) or {}).get("ownership") or [])
    ticker = ctx["ticker"]
    out: list[ChangeRecord] = []
    for item in sorted(cur ^ prev):
        added = item in cur
        change_type = "ownership_signal_added" if added else "ownership_signal_removed"
        cause = explain_change(
            metric=item,
            change_type=change_type,
            previous="absent" if added else "present",
            current="present" if added else "absent",
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:own:{item}",
                ticker=ticker,
                domain="ownership",
                metric=item,
                change_type=change_type,
                previous_value="absent" if added else "present",
                current_value="present" if added else "absent",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="ownership",
                materiality="medium",
                thesis_impact="needs_committee_review",
                confidence=0.6,
                **cause,
            )
        )
    return out
