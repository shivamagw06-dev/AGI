"""Management discussion diff — priorities, tone, warnings."""

from __future__ import annotations

from typing import Any

from filing_diff.comparator.cause import explain_change
from filing_diff.comparator.materiality import classify_materiality, thesis_impact
from filing_diff.schema import ChangeRecord

COSMETIC_TOKENS = ("the", "a", "and", "of", "to", "in", "for", "on")


def _is_cosmetic(prev: str, cur: str) -> bool:
    """True if only stopword / trivial wording differs."""
    a = {t for t in prev.lower().split() if t not in COSMETIC_TOKENS}
    b = {t for t in cur.lower().split() if t not in COSMETIC_TOKENS}
    if not a and not b:
        return True
    if a == b:
        return True  # identical after stopword removal
    overlap = len(a & b) / max(1, len(a | b))
    return overlap >= 0.9


def management_diff(ctx: dict[str, Any]) -> list[ChangeRecord]:
    cur_p = ctx.get("current_period")
    prev_p = ctx.get("previous_period")
    if not cur_p or not prev_p:
        return []
    qual = ctx.get("qual_by_period") or {}
    prev_m = (qual.get(prev_p) or {}).get("management") or {}
    cur_m = (qual.get(cur_p) or {}).get("management") or {}
    ticker = ctx["ticker"]
    out: list[ChangeRecord] = []

    for key in sorted(set(prev_m) | set(cur_m)):
        pv, cv = prev_m.get(key), cur_m.get(key)
        if pv == cv:
            continue
        if pv and not cv:
            change_type = "removed_priority" if "Priorit" in key else "dropped_commentary"
        elif cv and not pv:
            change_type = "new_priority" if "Priorit" in key else "new_commentary"
        else:
            cosmetic = _is_cosmetic(str(pv), str(cv))
            if cosmetic:
                continue  # ignore cosmetic wording
            change_type = "changed_language"
            if "Margin" in key or "Outlook" in key or key == "outlook_tone":
                change_type = "changed_outlook"
        mat = classify_materiality(
            metric=key, domain="management", previous=pv, current=cv, change_type=change_type
        )
        cause = explain_change(
            metric=key,
            change_type=change_type,
            previous=pv,
            current=cv,
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:mgmt:{key}:{prev_p}->{cur_p}",
                ticker=ticker,
                domain="management",
                metric=key,
                change_type=change_type,
                previous_value=pv,
                current_value=cv,
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="management_discussion",
                materiality=mat,
                thesis_impact=thesis_impact(mat, change_type, key, pv, cv),
                confidence=0.75,
                **cause,
            )
        )

    # optimism / warnings from text markers + current FIL management snippets
    prev_markers = (qual.get(prev_p) or {}).get("text_markers") or {}
    cur_text = " ".join(str(v) for v in cur_m.values()).lower()
    prev_tone = str(prev_markers.get("optimism") or "neutral")
    cur_tone = "cautious" if any(w in cur_text for w in ("pressure", "elevated", "compression")) else "constructive"
    if prev_tone != cur_tone:
        if cur_tone == "cautious" and prev_tone == "constructive":
            change_type = "optimism_decreased"
        elif cur_tone == "constructive" and prev_tone == "cautious":
            change_type = "optimism_increased"
        else:
            change_type = "changed_outlook"
        mat = classify_materiality(
            metric="Optimism", domain="management", previous=prev_tone, current=cur_tone, change_type=change_type
        )
        cause = explain_change(
            metric="Optimism",
            change_type=change_type,
            previous=prev_tone,
            current=cur_tone,
            previous_period=prev_p,
            current_period=cur_p,
        )
        out.append(
            ChangeRecord(
                change_id=f"{ticker}:mgmt:optimism:{prev_p}->{cur_p}",
                ticker=ticker,
                domain="management",
                metric="Optimism",
                change_type=change_type,
                previous_value=prev_tone,
                current_value=cur_tone,
                previous_period=prev_p,
                current_period=cur_p,
                previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                section="management_discussion",
                materiality=mat,
                thesis_impact=thesis_impact(mat, change_type, "Optimism", prev_tone, cur_tone),
                confidence=0.7,
                **cause,
            )
        )

    # new warnings
    prev_warn = set(prev_markers.get("warnings") or [])
    cur_warn = {w for w in ("deposit-cost pressure", "funding-cost pressure", "nim pressure") if w.replace("-", " ") in cur_text or w in cur_text}
    # normalize
    if "pressure" in cur_text and not prev_warn:
        cur_warn.add("funding/margin pressure")
    for w in sorted(cur_warn):
        if not any(w.split()[0] in p for p in prev_warn):
            change_type = "new_warning"
            mat = "high"
            cause = explain_change(
                metric="Management_Warning",
                change_type=change_type,
                previous="absent",
                current=w,
                previous_period=prev_p,
                current_period=cur_p,
            )
            out.append(
                ChangeRecord(
                    change_id=f"{ticker}:mgmt:warn:{w}",
                    ticker=ticker,
                    domain="management",
                    metric="Management_Warning",
                    change_type=change_type,
                    previous_value="absent",
                    current_value=w,
                    previous_period=prev_p,
                    current_period=cur_p,
                    previous_doc_id=((qual.get(prev_p) or {}).get("docs") or [""])[0],
                    current_doc_id=((qual.get(cur_p) or {}).get("docs") or [""])[0],
                    section="management_discussion",
                    materiality=mat,
                    thesis_impact=thesis_impact(mat, change_type, "Management_Warning", None, w),
                    confidence=0.72,
                    **cause,
                )
            )
    return out
