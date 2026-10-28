"""IDS-01 decision engine — deterministic InstitutionalDecision (no English, no LLM)."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Iterable, Optional, Sequence, Union

from institutional_decision.decision_graph import build_decision_graph
from institutional_decision.models import InstitutionalDecision
from institutional_decision.schema import (
    DECISION_ENGINE_VERSION,
    DECISION_VALIDATOR_VERSION,
    DEFAULT_MONITORING,
    IDS_VERSION,
)
from institutional_decision.recommendation_rules import business_quality_band_safe

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    out: list[str] = []
    for item in value:
        if hasattr(item, "supporting_points"):
            # Reason-like object
            out.extend(str(p).strip() for p in (item.supporting_points or ()) if str(p).strip())
            continue
        if isinstance(item, dict):
            for key in ("supporting_points", "conclusion", "title"):
                if item.get(key):
                    if key == "supporting_points":
                        out.extend(_as_list(item.get(key)))
                    else:
                        out.append(str(item.get(key)).strip())
            continue
        text = str(item or "").strip()
        if text:
            out.append(text)
    # dedupe
    seen: set[str] = set()
    uniq: list[str] = []
    for row in out:
        if row in seen:
            continue
        seen.add(row)
        uniq.append(row)
    return uniq


def _contra_from_reasons(reasons: Any) -> list[str]:
    out: list[str] = []
    if reasons is None:
        return out
    for item in reasons:
        if hasattr(item, "contradicting_points"):
            out.extend(str(p).strip() for p in (item.contradicting_points or ()) if str(p).strip())
        elif isinstance(item, dict):
            out.extend(_as_list(item.get("contradicting_points")))
        else:
            text = str(item or "").strip()
            if text:
                out.append(text)
    seen: set[str] = set()
    uniq: list[str] = []
    for row in out:
        if row in seen:
            continue
        seen.add(row)
        uniq.append(row)
    return uniq


def _unknowns_from_reasons(reasons: Any) -> list[str]:
    out: list[str] = []
    if reasons is None:
        return out
    for item in reasons:
        if hasattr(item, "unknowns"):
            out.extend(str(p).strip() for p in (item.unknowns or ()) if str(p).strip())
        elif isinstance(item, dict):
            out.extend(_as_list(item.get("unknowns")))
    seen: set[str] = set()
    uniq: list[str] = []
    for row in out:
        if row in seen:
            continue
        seen.add(row)
        uniq.append(row)
    return uniq


def _evidence_ids(reasons: Any, explicit: Any = None) -> list[str]:
    out = _as_list(explicit)
    if reasons is not None:
        for item in reasons:
            if hasattr(item, "supporting_evidence"):
                out.extend(str(e).strip() for e in (item.supporting_evidence or ()) if str(e).strip())
            elif isinstance(item, dict):
                out.extend(_as_list(item.get("supporting_evidence") or item.get("evidence_ids")))
    # Prefer ID-like tokens
    seen: set[str] = set()
    uniq: list[str] = []
    for row in out:
        if row in seen:
            continue
        seen.add(row)
        uniq.append(row)
    return uniq


def _fq_band(value: str) -> str:
    text = str(value or "").strip().title()
    if text in {"Excellent", "Strong", "Stable", "Weak"}:
        return text
    return text or "Unclear"


def _score_factors(
    *,
    bq: str,
    fq: str,
    valuation: str,
    risk: str,
) -> tuple[int, str]:
    """Transparent deterministic scoring → recommendation."""
    score = 0
    parts: list[str] = []

    if bq in {"Excellent", "Strong"}:
        score += 2
        parts.append(f"bq:{bq}=+2")
    elif bq == "Adequate":
        score += 1
        parts.append(f"bq:{bq}=+1")
    else:
        parts.append(f"bq:{bq}=+0")

    if fq in {"Excellent", "Strong"}:
        score += 2
        parts.append(f"fq:{fq}=+2")
    elif fq == "Stable":
        score += 1
        parts.append(f"fq:{fq}=+1")
    elif fq == "Weak":
        score -= 1
        parts.append(f"fq:{fq}=-1")
    else:
        parts.append(f"fq:{fq}=+0")

    val = str(valuation or "").strip().title()
    if val == "Cheap":
        score += 2
        parts.append("val:Cheap=+2")
    elif val == "Fair":
        score += 1
        parts.append("val:Fair=+1")
    elif val == "Expensive":
        score -= 1
        parts.append("val:Expensive=-1")
    else:
        parts.append(f"val:{val}=+0")

    risk_l = str(risk or "").strip().title()
    if risk_l == "Low":
        score += 2
        parts.append("risk:Low=+2")
    elif risk_l == "Moderate":
        parts.append("risk:Moderate=+0")
    elif risk_l == "High":
        score -= 2
        parts.append("risk:High=-2")
    elif risk_l == "Severe":
        score -= 3
        parts.append("risk:Severe=-3")
    else:
        parts.append(f"risk:{risk_l}=+0")

    return score, "|".join(parts)


def _recommendation_from_score(score: int) -> tuple[str, str]:
    """Map score → (recommendation, conviction)."""
    if score >= 7:
        return "BUY", "HIGH"
    if score >= 6:
        return "BUY", "MEDIUM"
    if score <= 0:
        return "SELL", "HIGH"
    if score == 1:
        return "SELL", "MEDIUM"
    # HOLD band
    if score <= 3:
        return "HOLD", "LOW"
    if score == 4:
        return "HOLD", "LOW"
    return "HOLD", "MEDIUM"


def _horizon_for(recommendation: str, conviction: str) -> str:
    if recommendation == "BUY" and conviction == "HIGH":
        return "Long"
    if recommendation == "SELL":
        return "Short"
    if conviction == "LOW":
        return "Medium"
    return "Medium"


def _upgrade_conditions(*, bq: str, fq: str, valuation: str, risk: str, recommendation: str) -> tuple[str, ...]:
    items = [
        "ROE improves versus peer median",
        "NIM expands on a sustained basis",
        "Credit costs decline without asset-quality tradeoffs",
        "Retail growth accelerates with controlled risk",
    ]
    if valuation == "Expensive":
        items.insert(0, "Valuation compresses toward peer median / fair value")
    if risk in {"High", "Severe", "Moderate"}:
        items.append("Overall risk profile improves to Low")
    if recommendation == "BUY":
        items = [
            "Maintain BUY if operating metrics remain intact",
            "Raise conviction if credit costs stay benign for two consecutive quarters",
            *items[:2],
        ]
    return tuple(dict.fromkeys(items))


def _downgrade_conditions(*, recommendation: str) -> tuple[str, ...]:
    items = [
        "NPAs increase beyond recent trend",
        "Provisioning rises without earnings absorption",
        "Capital allocation deteriorates",
        "Liability franchise weakens materially",
    ]
    if recommendation == "HOLD":
        items = ("Downgrade if asset quality deteriorates", *items)
    if recommendation == "BUY":
        items = ("Downgrade if thesis pillars break", *items)
    return tuple(dict.fromkeys(items))


def _evidence_snapshot_id(evidence_ids: Sequence[str], ticker: str) -> str:
    raw = f"{ticker}|{'|'.join(evidence_ids)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def generate_decision(
    reasons: Any = None,
    valuation: Any = None,
    risks: Any = None,
    confidence: Any = None,
    *,
    business_quality: Any = None,
    financial_quality: Any = None,
    overall_risk: Any = None,
    ticker: str = "",
    company_name: str = "",
    sector: str = "",
    unknowns: Any = None,
    evidence_ids: Any = None,
    reason_version: str = "",
    report_version: str = "",
    previous_version: int = 0,
    macro: str = "Neutral",
    management: str = "Adequate",
    investment_horizon: str = "",
) -> InstitutionalDecision:
    """Public API — structured InstitutionalDecision only (no English generation)."""
    bq = business_quality_band_safe(business_quality if business_quality is not None else "Adequate")
    fq = _fq_band(str(financial_quality or "Stable"))
    val = str(valuation or "Unclear").strip().title()
    risk_l = str(overall_risk if overall_risk is not None else _first_risk(risks) or "Moderate").strip().title()

    score, rule_path = _score_factors(bq=bq, fq=fq, valuation=val, risk=risk_l)
    recommendation, conviction = _recommendation_from_score(score)
    horizon = investment_horizon or _horizon_for(recommendation, conviction)

    try:
        conf = int(confidence)
    except (TypeError, ValueError):
        conf = 50
    conf = max(0, min(100, conf))

    supporting = _as_list(reasons)
    if not supporting:
        supporting = [
            f"business_quality={bq}",
            f"financial_quality={fq}",
            f"valuation={val}",
            f"risk={risk_l}",
            f"score={score}",
        ]
    contradicting = _contra_from_reasons(reasons)
    if not contradicting:
        contradicting = _as_list(risks) or ["residual_risks_remain"]
    unknown_list = _as_list(unknowns) or _unknowns_from_reasons(reasons) or ["forward_path_unverified"]
    eids = _evidence_ids(reasons, evidence_ids)
    if not eids:
        eids = ["EVIDENCE-REQUIRED"]

    graph = build_decision_graph(
        business_quality=bq,
        financial_quality=fq,
        valuation=val,
        risk=risk_l,
        macro=str(macro or "Neutral"),
        management=str(management or "Adequate"),
        recommendation=recommendation,
        score=score,
        rule_path=rule_path,
    )

    ticker_u = str(ticker or "").strip().upper()
    generated = now_iso()
    version = int(previous_version or 0) + 1
    snap = _evidence_snapshot_id(eids, ticker_u)
    decision_id = f"ids-{ticker_u.lower() or 'unknown'}-{snap}-{version}"

    return InstitutionalDecision(
        ticker=ticker_u,
        recommendation=recommendation,
        conviction=conviction,
        confidence=conf,
        investment_horizon=horizon,
        supporting_reasons=tuple(supporting[:12]),
        contradicting_reasons=tuple(contradicting[:8]),
        unknowns=tuple(unknown_list[:8]),
        upgrade_conditions=_upgrade_conditions(
            bq=bq, fq=fq, valuation=val, risk=risk_l, recommendation=recommendation
        ),
        downgrade_conditions=_downgrade_conditions(recommendation=recommendation),
        monitoring_items=DEFAULT_MONITORING,
        decision_id=decision_id,
        decision_version=version,
        generated_at=generated,
        reason_version=str(reason_version or ""),
        report_version=str(report_version or ""),
        evidence_snapshot_id=snap,
        decision_engine_version=DECISION_ENGINE_VERSION,
        validator_version=DECISION_VALIDATOR_VERSION,
        company_name=str(company_name or "").strip(),
        sector=str(sector or "").strip(),
        decision_graph=graph,
        evidence_ids=tuple(eids),
        rule_path=rule_path,
        score=score,
        llm=False,
    )


def _first_risk(risks: Any) -> str:
    rows = _as_list(risks)
    return rows[0] if rows else ""
