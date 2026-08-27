"""Temporal execution evaluation — status from later evidence only."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from evidence_fusion.signals import check_expectation
from financial_intelligence.trends import normalize_series
from management_execution.objectives import detect_supersessions
from management_execution.periods import (
    filter_series_in_window,
    months_between,
    parse_period_to_date,
    window_end,
)
from management_execution.schema import (
    CONF_HIGH,
    CONF_LOW,
    CONF_MEDIUM,
    DEFAULT_WINDOWS,
    STATUS_CANNOT,
    STATUS_DELIVERED,
    STATUS_NOT_YET,
    STATUS_PARTIAL,
    STATUS_SUPERSEDED,
    VERSION,
)


def _temporal_signal(
    series: list[dict[str, Any]],
    *,
    origin: date,
    end: date | None,
) -> dict[str, Any] | None:
    """Direction from baseline at/before origin to latest point in (origin, end]."""
    win = filter_series_in_window(series, origin=origin, end=end, include_baseline=True)
    baseline = win.get("baseline")
    post = win.get("post") or []
    if not baseline or not post:
        return {
            "available": bool(baseline or post),
            "comparable": False,
            "direction": "unknown",
            "pct_change": None,
            "history_n": len(normalize_series(series or [])),
            "evidence_ids": [],
            "validation_status": (baseline or (post[0] if post else {})).get("validation_status"),
            "baseline": baseline,
            "latest": post[-1] if post else None,
            "reporting_period": (post[-1] if post else baseline or {}).get("period"),
            "n_post": len(post),
        }
    prior, latest = baseline, post[-1]
    curr, prev = float(latest["value"]), float(prior["value"])
    if prev == 0:
        pct = None
        direction = "up" if curr > 0 else ("down" if curr < 0 else "flat")
    else:
        pct = round(100.0 * (curr - prev) / abs(prev), 4)
        if abs(pct) < 0.5:
            direction = "flat"
        else:
            direction = "up" if pct > 0 else "down"
    eids = []
    for r in (prior, latest):
        eid = r.get("validation_id") or r.get("fact_key")
        if eid and str(eid) not in eids:
            eids.append(str(eid))
    return {
        "available": True,
        "comparable": True,
        "direction": direction,
        "pct_change": pct,
        "history_n": len(normalize_series(series or [])),
        "evidence_ids": eids,
        "validation_status": latest.get("validation_status") or prior.get("validation_status"),
        "baseline": prior,
        "latest": latest,
        "reporting_period": latest.get("period"),
        "n_post": len(post),
        "delivery_months": round(months_between(origin, parse_period_to_date(latest.get("period")) or end or origin), 1),
    }


def _classify(
    *,
    support_w: float,
    conflict_w: float,
    partial_w: float,
    available: int,
    force_cannot: bool,
    any_support_ok: bool,
) -> str:
    if force_cannot or available == 0:
        return STATUS_CANNOT
    if any_support_ok and support_w > 0 and conflict_w == 0:
        return STATUS_DELIVERED
    if conflict_w <= 0 and partial_w <= 0 and support_w > 0:
        return STATUS_DELIVERED
    if support_w > 0 and conflict_w > 0:
        return STATUS_PARTIAL
    if support_w > 0 and partial_w > 0 and conflict_w <= 0:
        return STATUS_PARTIAL if partial_w >= support_w else STATUS_DELIVERED
    if conflict_w > 0 and support_w <= 0:
        return STATUS_NOT_YET if conflict_w >= partial_w else STATUS_PARTIAL
    if partial_w > 0:
        return STATUS_PARTIAL
    return STATUS_CANNOT


def _confidence(
    *,
    available: int,
    history_n: int,
    coverage_pct: float | None,
    status: str,
    validation_status: str | None,
) -> str:
    points = 0
    if available >= 2:
        points += 2
    elif available == 1:
        points += 1
    if history_n >= 4:
        points += 1
    if coverage_pct is not None:
        if coverage_pct >= 80:
            points += 1
        elif coverage_pct < 40:
            points -= 1
    if (validation_status or "").upper() == "APPROVED":
        points += 1
    if status == STATUS_CANNOT:
        return CONF_LOW
    if status == STATUS_SUPERSEDED:
        return CONF_MEDIUM if points >= 2 else CONF_LOW
    if points >= 4:
        return CONF_HIGH
    if points >= 2:
        return CONF_MEDIUM
    return CONF_LOW


def _narrative(status: str, statement: str, bits: list[str]) -> str:
    fin = "; ".join(bits) if bits else "no post-statement measurable financial evidence"
    if status == STATUS_DELIVERED:
        return f"Objective '{statement}' is classified Delivered based on later evidence ({fin})."
    if status == STATUS_PARTIAL:
        return f"Objective '{statement}' is classified Partially Delivered based on mixed later evidence ({fin})."
    if status == STATUS_NOT_YET:
        return f"Objective '{statement}' is classified Not Yet Delivered based on later evidence ({fin})."
    if status == STATUS_SUPERSEDED:
        return f"Objective '{statement}' is classified Superseded by a later disclosure (not treated as failure)."
    return f"Objective '{statement}' is classified Cannot Yet Evaluate ({fin})."


def evaluate_objective(
    objective: dict[str, Any],
    *,
    series_map: dict[str, list[dict[str, Any]]],
    window_key: str | None = None,
    as_of: date | None = None,
    coverage_pct: float | None = None,
    supersede_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    origin = parse_period_to_date(objective.get("origin_period"))
    stmt = str(objective.get("statement") or objective.get("original_statement") or "")
    eval_date = as_of or date.today()

    if supersede_info:
        return _execution_finding(
            objective,
            status=STATUS_SUPERSEDED,
            financial_evidence=[],
            evidence_ids=[str(supersede_info.get("fact_id") or "")] if supersede_info.get("fact_id") else [],
            supporting_metrics=[],
            bits=["later disclosure withdraws / cancels objective"],
            coverage_pct=coverage_pct,
            window_key=window_key or objective.get("primary_window") or "year",
            evaluation_date=eval_date,
            delivery_months=None,
            later_business_evidence=supersede_info,
            history_n=0,
            validation_status=None,
            available=0,
        )

    if origin is None:
        return _execution_finding(
            objective,
            status=STATUS_CANNOT,
            financial_evidence=[],
            evidence_ids=[],
            supporting_metrics=[],
            bits=["origin period could not be parsed"],
            coverage_pct=coverage_pct,
            window_key=window_key or "year",
            evaluation_date=eval_date,
            delivery_months=None,
            later_business_evidence=None,
            history_n=0,
            validation_status=None,
            available=0,
        )

    wkey = window_key or str(objective.get("primary_window") or "year")
    end = window_end(origin, wkey)
    if as_of and as_of < end:
        end = as_of

    if objective.get("force_cannot_evaluate"):
        return _execution_finding(
            objective,
            status=STATUS_CANNOT,
            financial_evidence=[],
            evidence_ids=[str(objective.get("origin_fact_id") or "")] if objective.get("origin_fact_id") else [],
            supporting_metrics=[],
            bits=["no durable financial metric mapping for this objective type"],
            coverage_pct=coverage_pct,
            window_key=wkey,
            evaluation_date=eval_date,
            delivery_months=None,
            later_business_evidence=None,
            history_n=0,
            validation_status=None,
            available=0,
        )

    checks = list(objective.get("checks") or [])
    prefer = objective.get("prefer_metric")
    skip: set[str] = set()
    if prefer and prefer == "net_debt":
        # If both net_debt and total_debt have post evidence, prefer net_debt
        nd = _temporal_signal(series_map.get("net_debt") or [], origin=origin, end=end)
        td = _temporal_signal(series_map.get("total_debt") or [], origin=origin, end=end)
        if nd and nd.get("comparable") and td and td.get("comparable"):
            skip.add("total_debt")

    support_w = conflict_w = partial_w = 0.0
    available = 0
    financial_evidence: list[dict[str, Any]] = []
    bits: list[str] = []
    supporting: list[str] = []
    evidence_ids: list[str] = []
    history_n = 0
    validation_status = None
    delivery_months = None

    if objective.get("origin_fact_id"):
        evidence_ids.append(str(objective["origin_fact_id"]))

    for chk in checks:
        metric = chk["metric"]
        if metric in skip:
            continue
        sig = _temporal_signal(series_map.get(metric) or [], origin=origin, end=end)
        outcome = check_expectation(sig, chk["expected"])
        if outcome == "insufficient":
            continue
        available += 1
        weight = float(chk.get("weight") or 1)
        history_n = max(history_n, int((sig or {}).get("history_n") or 0))
        validation_status = validation_status or (sig or {}).get("validation_status")
        for eid in (sig or {}).get("evidence_ids") or []:
            if eid not in evidence_ids:
                evidence_ids.append(eid)
        if (sig or {}).get("delivery_months") is not None:
            delivery_months = (sig or {}).get("delivery_months")
        pct = (sig or {}).get("pct_change")
        direction = (sig or {}).get("direction")
        bit = f"{metric} {direction}"
        if pct is not None:
            bit += f" ({pct:+.1f}% since origin)"
        bits.append(bit)
        financial_evidence.append(
            {
                "metric": metric,
                "expected": chk["expected"],
                "outcome": outcome,
                "direction": direction,
                "pct_change": pct,
                "baseline_period": ((sig or {}).get("baseline") or {}).get("period"),
                "evidence_period": (sig or {}).get("reporting_period"),
            }
        )
        if outcome == "support":
            support_w += weight
            supporting.append(metric)
        elif outcome == "conflict":
            conflict_w += weight
        else:
            partial_w += weight

    status = _classify(
        support_w=support_w,
        conflict_w=conflict_w,
        partial_w=partial_w,
        available=available,
        force_cannot=False,
        any_support_ok=bool(objective.get("any_support_ok")),
    )

    return _execution_finding(
        objective,
        status=status,
        financial_evidence=financial_evidence,
        evidence_ids=evidence_ids,
        supporting_metrics=supporting,
        bits=bits,
        coverage_pct=coverage_pct,
        window_key=wkey,
        evaluation_date=eval_date,
        delivery_months=delivery_months,
        later_business_evidence=None,
        history_n=history_n,
        validation_status=validation_status,
        available=available,
    )


def _execution_finding(
    objective: dict[str, Any],
    *,
    status: str,
    financial_evidence: list[dict[str, Any]],
    evidence_ids: list[str],
    supporting_metrics: list[str],
    bits: list[str],
    coverage_pct: float | None,
    window_key: str,
    evaluation_date: date,
    delivery_months: float | None,
    later_business_evidence: dict[str, Any] | None,
    history_n: int,
    validation_status: str | None,
    available: int,
) -> dict[str, Any]:
    stmt = str(objective.get("statement") or "")
    conf = _confidence(
        available=available,
        history_n=history_n,
        coverage_pct=coverage_pct,
        status=status,
        validation_status=validation_status,
    )
    fid = "ex:" + hashlib.sha1(
        f"{objective.get('objective_id')}|{status}|{window_key}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "finding_id": fid,
        "objective_id": objective.get("objective_id"),
        "category": objective.get("category"),
        "topic_key": objective.get("topic_key"),
        "statement": stmt,
        "original_statement": objective.get("original_statement"),
        "original_source": objective.get("origin_document"),
        "original_period": objective.get("origin_period"),
        "origin_page": objective.get("origin_page"),
        "origin_section": objective.get("origin_section"),
        "expected_horizon": objective.get("expected_horizon"),
        "evaluation_window": window_key,
        "evidence": financial_evidence,
        "later_business_evidence": later_business_evidence,
        "current_status": status,
        "status": status,
        "confidence": conf,
        "evidence_ids": [e for e in evidence_ids if e],
        "supporting_metrics": supporting_metrics,
        "evaluation_date": evaluation_date.isoformat(),
        "delivery_months": delivery_months,
        "narrative": _narrative(status, stmt, bits),
        "bucket": objective.get("bucket"),
        "inferred_intent": False,
        "judges_honesty": False,
        "uses_llm": False,
        "engine_version": VERSION,
    }


def evaluate_all(
    objectives: list[dict[str, Any]],
    *,
    series_map: dict[str, list[dict[str, Any]]],
    later_facts: list[dict[str, Any]] | None = None,
    windows: tuple[str, ...] | list[str] | None = None,
    as_of: date | None = None,
    coverage_pct: float | None = None,
) -> list[dict[str, Any]]:
    """Evaluate each objective on its primary window (plus optional multi-window detail)."""
    supersedes = detect_supersessions(objectives, later_facts or [])
    wins = list(windows or DEFAULT_WINDOWS)
    findings: list[dict[str, Any]] = []

    for obj in objectives:
        sid = str(obj.get("objective_id"))
        primary = str(obj.get("primary_window") or "year")
        if primary not in wins:
            wins_for = [primary] + [w for w in wins if w != primary]
        else:
            wins_for = [primary] + [w for w in wins if w != primary]

        primary_finding = evaluate_objective(
            obj,
            series_map=series_map,
            window_key=primary,
            as_of=as_of,
            coverage_pct=coverage_pct,
            supersede_info=supersedes.get(sid),
        )
        # Multi-window detail (non-superseded)
        window_results = {primary: primary_finding["current_status"]}
        if primary_finding["current_status"] != STATUS_SUPERSEDED:
            for w in wins_for[1:]:
                alt = evaluate_objective(
                    obj,
                    series_map=series_map,
                    window_key=w,
                    as_of=as_of,
                    coverage_pct=coverage_pct,
                    supersede_info=None,
                )
                window_results[w] = alt["current_status"]
        primary_finding["window_results"] = window_results
        findings.append(primary_finding)

    order = {
        STATUS_DELIVERED: 0,
        STATUS_PARTIAL: 1,
        STATUS_NOT_YET: 2,
        STATUS_CANNOT: 3,
        STATUS_SUPERSEDED: 4,
    }
    findings.sort(key=lambda f: (order.get(str(f.get("current_status")), 9), str(f.get("category") or "")))
    return findings
