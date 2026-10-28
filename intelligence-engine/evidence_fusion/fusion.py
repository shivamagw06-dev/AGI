"""Consistency + contradiction engines → EvidenceFusionFinding list."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from evidence_fusion.confidence import score_fusion_confidence
from evidence_fusion.schema import (
    CAT_CONTRADICTION,
    RESULT_INSUFFICIENT,
    RESULT_NOT_SUPPORTED,
    RESULT_PARTIAL,
    RESULT_SUPPORTED,
    VERSION,
)
from evidence_fusion.signals import build_signal_map, check_expectation
from evidence_fusion.topics import match_topics


def _finding_id(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return "ef:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _related_fire01(findings: list[dict[str, Any]], metrics: list[str]) -> list[dict[str, Any]]:
    mset = set(metrics)
    return [f for f in findings if f.get("metric") in mset]


def _related_fire02(rels: list[dict[str, Any]], metrics: list[str]) -> list[dict[str, Any]]:
    mset = set(metrics)
    out = []
    for r in rels:
        blob = f"{r.get('code') or ''} {r.get('relationship') or ''} {r.get('observation') or ''}".lower()
        evid = r.get("evidence") or []
        evid_metrics = {e.get("metric") for e in evid if isinstance(e, dict)}
        if evid_metrics & mset or any(m in blob for m in mset):
            out.append(r)
    return out


def _classify(
    *,
    support_w: float,
    conflict_w: float,
    partial_w: float,
    available_checks: int,
    force_insufficient: bool,
    any_support_ok: bool,
) -> str:
    if force_insufficient or available_checks == 0:
        return RESULT_INSUFFICIENT
    if any_support_ok and support_w > 0 and conflict_w == 0:
        return RESULT_SUPPORTED
    if conflict_w <= 0 and partial_w <= 0 and support_w > 0:
        return RESULT_SUPPORTED
    if support_w > 0 and conflict_w > 0:
        return RESULT_PARTIAL
    if support_w > 0 and partial_w > 0 and conflict_w <= 0:
        return RESULT_PARTIAL if partial_w >= support_w else RESULT_SUPPORTED
    if conflict_w > 0 and support_w <= 0:
        return RESULT_NOT_SUPPORTED if conflict_w >= partial_w else RESULT_PARTIAL
    if partial_w > 0 and support_w <= 0 and conflict_w <= 0:
        return RESULT_PARTIAL
    return RESULT_INSUFFICIENT


def _narrative(result: str, claim: str, financial_bits: list[str]) -> str:
    fin = "; ".join(financial_bits) if financial_bits else "no comparable financial metrics"
    if result == RESULT_SUPPORTED:
        return f"Management statement on {claim} is supported by financial evidence ({fin})."
    if result == RESULT_PARTIAL:
        return f"Management statement on {claim} is only partially supported by financial evidence ({fin})."
    if result == RESULT_NOT_SUPPORTED:
        return f"Management statement on {claim} is not supported by current financial evidence ({fin})."
    return f"Management discusses {claim}, but measurable financial evidence is insufficient ({fin})."


def fuse_statement(
    fact: dict[str, Any],
    rule: dict[str, Any],
    *,
    signals: dict[str, dict[str, Any]],
    fire01: list[dict[str, Any]],
    fire02: list[dict[str, Any]],
    coverage_pct: float | None,
) -> dict[str, Any]:
    checks = list(rule.get("checks") or [])
    support_w = conflict_w = partial_w = 0.0
    available = 0
    financial_evidence: list[dict[str, Any]] = []
    financial_bits: list[str] = []
    supporting_metrics: list[str] = []
    evidence_ids: list[str] = []
    history_n = 0
    validation_status = None

    # For debt_reduction prefer net_debt over total_debt when both comparable
    skip_metrics: set[str] = set()
    if rule.get("topic_id") == "debt_reduction":
        nd = signals.get("net_debt")
        td = signals.get("total_debt")
        if nd and nd.get("comparable") and td and td.get("comparable"):
            skip_metrics.add("total_debt")

    for chk in checks:
        metric = chk["metric"]
        if metric in skip_metrics:
            continue
        expected = chk["expected"]
        weight = float(chk.get("weight") or 1)
        sig = signals.get(metric)
        outcome = check_expectation(sig, expected)
        if outcome == "insufficient":
            continue
        available += 1
        history_n = max(history_n, int((sig or {}).get("history_n") or 0))
        validation_status = validation_status or (sig or {}).get("validation_status")
        for eid in (sig or {}).get("evidence_ids") or []:
            if eid not in evidence_ids:
                evidence_ids.append(eid)
        pct = (sig or {}).get("pct_change")
        direction = (sig or {}).get("direction")
        bit = f"{metric} {direction}"
        if pct is not None:
            bit += f" ({pct:+.1f}%)"
        financial_bits.append(bit)
        financial_evidence.append(
            {
                "metric": metric,
                "expected": expected,
                "outcome": outcome,
                "direction": direction,
                "pct_change": pct,
                "reporting_period": (sig or {}).get("reporting_period"),
            }
        )
        if outcome == "support":
            support_w += weight
            supporting_metrics.append(metric)
        elif outcome == "conflict":
            conflict_w += weight
        else:
            partial_w += weight

    # Risk alignment mode: "support" means financial stress aligns with disclosed risk
    # (already encoded via expected directions). No special rewrite needed.

    result = _classify(
        support_w=support_w,
        conflict_w=conflict_w,
        partial_w=partial_w,
        available_checks=available,
        force_insufficient=bool(rule.get("force_insufficient")),
        any_support_ok=bool(rule.get("any_support_ok")),
    )

    metrics_for_rel = [c["metric"] for c in checks]
    rel_f01 = _related_fire01(fire01, metrics_for_rel)
    rel_f02 = _related_fire02(fire02, metrics_for_rel)
    for f in rel_f01:
        if f.get("finding_id") and f["finding_id"] not in evidence_ids:
            evidence_ids.append(str(f["finding_id"]))
    for r in rel_f02:
        rid = r.get("code") or r.get("relationship_id")
        if rid and str(rid) not in evidence_ids:
            evidence_ids.append(str(rid))
    if fact.get("fact_id"):
        evidence_ids.insert(0, str(fact["fact_id"]))

    sources_n = 1  # business fact
    if available:
        sources_n += 1
    if rel_f01:
        sources_n += 1
    if rel_f02:
        sources_n += 1

    conf = score_fusion_confidence(
        history_n=history_n,
        windows_n=1 if available else 0,
        validation_status=validation_status,
        coverage_pct=coverage_pct,
        supporting_sources_n=sources_n if result == RESULT_SUPPORTED else max(0, sources_n - 1),
        conflict=result == RESULT_NOT_SUPPORTED or (support_w > 0 and conflict_w > 0),
    )

    period = fact.get("reporting_period")
    for fe in financial_evidence:
        if fe.get("reporting_period"):
            period = fe["reporting_period"]
            break

    return {
        "finding_id": _finding_id(rule.get("topic_id"), fact.get("fact_id"), fact.get("statement")),
        "category": rule.get("category"),
        "topic_id": rule.get("topic_id"),
        "consistency_bucket": rule.get("consistency_bucket"),
        "business_statement": fact.get("statement"),
        "business_fact_id": fact.get("fact_id"),
        "business_category": fact.get("category"),
        "financial_evidence": financial_evidence,
        "fusion_result": result,
        "confidence": conf["confidence"],
        "confidence_detail": conf,
        "evidence_ids": evidence_ids,
        "supporting_metrics": supporting_metrics,
        "reporting_period": period,
        "narrative": _narrative(result, str(rule.get("claim") or "this topic"), financial_bits),
        "fire01_refs": [{"finding_id": f.get("finding_id"), "metric": f.get("metric"), "trend_label": f.get("trend_label")} for f in rel_f01[:5]],
        "fire02_refs": [{"code": r.get("code"), "relationship": r.get("relationship")} for r in rel_f02[:5]],
        "document": fact.get("document"),
        "page": fact.get("page"),
        "section": fact.get("section"),
        "inferred_intent": False,
        "judges_honesty": False,
        "uses_llm": False,
        "engine_version": VERSION,
    }


def _optimism_keywords(text: str) -> bool:
    return bool(
        re.search(
            r"improv(?:e|ing)|strong(?:er)?|expand(?:ing)?|growth|optimis|optimiz|priority|adequate|healthy",
            text or "",
            re.I,
        )
    )


def contradiction_findings(
    fusion_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit contradiction-tagged rows for optimism vs deterioration (deterministic)."""
    out: list[dict[str, Any]] = []
    for row in fusion_rows:
        if row.get("fusion_result") != RESULT_NOT_SUPPORTED:
            continue
        stmt = str(row.get("business_statement") or "")
        if not _optimism_keywords(stmt):
            continue
        # Financial deterioration opposing management optimism
        fin = row.get("financial_evidence") or []
        deteriorating = [
            fe
            for fe in fin
            if fe.get("outcome") == "conflict"
            and fe.get("direction") in {"down", "up"}  # conflict already encodes mismatch
        ]
        if not deteriorating:
            continue
        out.append(
            {
                **row,
                "finding_id": _finding_id("contradiction", row.get("finding_id")),
                "category": CAT_CONTRADICTION,
                "consistency_bucket": "financial_consistency",
                "fusion_result": RESULT_NOT_SUPPORTED,
                "narrative": (
                    "Management optimism is not aligned with current financial evidence "
                    f"({row.get('narrative')})"
                ),
                "contradiction_type": "management_optimism_vs_financial_deterioration",
            }
        )
    return out


def fuse_all(
    *,
    fire03_facts: list[dict[str, Any]],
    series_map: dict[str, list[dict[str, Any]]],
    fire01_findings: list[dict[str, Any]] | None = None,
    fire02_relationships: list[dict[str, Any]] | None = None,
    coverage_pct: float | None = None,
) -> list[dict[str, Any]]:
    signals = build_signal_map(series_map)
    fire01 = fire01_findings or []
    fire02 = fire02_relationships or []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for fact in fire03_facts or []:
        rules = match_topics(fact)
        if not rules:
            continue
        for rule in rules:
            row = fuse_statement(
                fact,
                rule,
                signals=signals,
                fire01=fire01,
                fire02=fire02,
                coverage_pct=coverage_pct,
            )
            key = f"{row['topic_id']}|{row.get('business_fact_id')}|{row.get('business_statement')}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    rows.extend(contradiction_findings(rows))
    # Stable order: Supported → Partial → Not Supported → Insufficient
    order = {
        RESULT_SUPPORTED: 0,
        RESULT_PARTIAL: 1,
        RESULT_NOT_SUPPORTED: 2,
        RESULT_INSUFFICIENT: 3,
    }
    rows.sort(key=lambda r: (order.get(str(r.get("fusion_result")), 9), str(r.get("category") or "")))
    return rows
