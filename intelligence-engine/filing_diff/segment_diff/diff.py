"""Segment mix diff."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.schema import ChangeRecord


def segment_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    qual = ctx.get("qual_by_period") or {}
    # segments stored as joined strings sometimes
    def _flat(period: str) -> set[str]:
        raw = (qual.get(period) or {}).get("segments") or []
        out: set[str] = set()
        for item in raw:
            for part in str(item).split(","):
                part = part.strip()
                if part:
                    out.add(part)
        return out

    cur, prev = _flat(cur_p), _flat(prev_p)
    ticker = ctx["ticker"]
    out: list[ChangeRecord] = []
    for s in sorted(cur - prev):
        cause = explain_change(
            metric="Business_Segments",
            change_type="segment_added",
            previous="absent",
            current=s,
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:seg:add:{s}",
                ticker=ticker,
                domain="segment",
                metric="Business_Segments",
                change_type="segment_added",
                previous_value="absent",
                current_value=s,
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="segments",
                materiality="medium",
                thesis_impact="needs_committee_review",
                confidence=0.65,
                **cause,
            )
        )
    for s in sorted(prev - cur):
        cause = explain_change(
            metric="Business_Segments",
            change_type="segment_removed",
            previous=s,
            current="absent",
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:seg:rem:{s}",
                ticker=ticker,
                domain="segment",
                metric="Business_Segments",
                change_type="segment_removed",
                previous_value=s,
                current_value="absent",
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="segments",
                materiality="medium",
                thesis_impact="needs_committee_review",
                confidence=0.65,
                **cause,
            )
        )
    return out
