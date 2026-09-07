"""Business Analyst memory — prior views and Improving / Stable / Deteriorating."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _as_confidence(value: Any) -> float:
    if isinstance(value, dict):
        for key in ("overall", "evidence", "knowledge"):
            if value.get(key) is not None:
                try:
                    return float(value.get(key))
                except Exception:
                    continue
        return 0.0
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _grade_rank(grade: str | None) -> int:
    return {
        "Exceptional": 4,
        "High": 3,
        "Adequate": 2,
        "Weak": 1,
        "Strong": 3,
        "Medium": 2,
        "Improving": 3,
        "Declining": 1,
        "Low": 1,
        "Moderate": 2,
    }.get(str(grade or ""), 0)


def extract_prior_view(memory_snapshot: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    snap = memory_snapshot if isinstance(memory_snapshot, dict) else {}
    has_prior = bool(snap)
    bq = snap.get("business_quality") if isinstance(snap.get("business_quality"), dict) else {}
    moat = snap.get("moat") if isinstance(snap.get("moat"), dict) else snap.get("moat_assessment")
    moat = moat if isinstance(moat, dict) else {}
    return {
        "has_prior": has_prior,
        "prior_stance": (snap.get("prior_stance") or snap.get("stance") or "") if has_prior else "",
        "prior_business_quality": bq.get("grade") or snap.get("prior_quality_grade") or snap.get("quality_grade"),
        "prior_moat": moat.get("durability") or snap.get("prior_moat_durability") or snap.get("moat_durability"),
        "prior_growth_view": snap.get("prior_growth_view") or snap.get("growth_runway"),
        "prior_risks": list(snap.get("prior_risks") or snap.get("risks") or snap.get("weaknesses") or [])[:4],
        "prior_confidence": _as_confidence(
            snap.get("prior_confidence") if "prior_confidence" in snap else snap.get("confidence")
        ),
        "prediction_history": list(snap.get("prediction_history") or [])[:8],
        "lessons_learned": list(snap.get("lessons_learned") or [])[:6],
        "accuracy": snap.get("accuracy"),
        # V1 aliases
        "prior_quality_grade": bq.get("grade") or snap.get("prior_quality_grade") or snap.get("quality_grade"),
        "prior_moat_durability": moat.get("durability") or snap.get("prior_moat_durability") or snap.get("moat_durability"),
    }


def compare_views(
    *,
    current_stance: str,
    current_quality_grade: str,
    current_moat_durability: str,
    current_growth_view: str,
    current_risks: List[str],
    current_confidence: float,
    prior: Dict[str, Any],
) -> Dict[str, Any]:
    if not prior.get("has_prior"):
        return {
            "what_changed": [],
            "view_stable": True,
            "trajectory": "Stable",
            "confidence_delta": 0.0,
            "prior_stance": None,
            "current_stance": current_stance,
            "business_quality_trajectory": "Stable",
            "moat_trajectory": "Stable",
            "growth_trajectory": "Stable",
            "risk_trajectory": "Stable",
        }

    changes: List[str] = []
    prior_stance = str(prior.get("prior_stance") or "")
    if current_stance and prior_stance and current_stance != prior_stance:
        changes.append(f"Stance shifted from {prior_stance} to {current_stance}")

    prior_grade = str(prior.get("prior_business_quality") or "")
    bq_traj = "Stable"
    if prior_grade and current_quality_grade and prior_grade != current_quality_grade:
        delta = _grade_rank(current_quality_grade) - _grade_rank(prior_grade)
        bq_traj = "Improving" if delta > 0 else "Deteriorating" if delta < 0 else "Stable"
        changes.append(f"Business quality moved from {prior_grade} to {current_quality_grade} ({bq_traj})")

    prior_moat = str(prior.get("prior_moat") or "")
    moat_traj = "Stable"
    if prior_moat and current_moat_durability and prior_moat != current_moat_durability:
        delta = _grade_rank(current_moat_durability) - _grade_rank(prior_moat)
        moat_traj = "Improving" if delta > 0 else "Deteriorating" if delta < 0 else "Stable"
        changes.append(f"Moat reassessment: {prior_moat} → {current_moat_durability} ({moat_traj})")

    prior_growth = str(prior.get("prior_growth_view") or "")
    growth_traj = "Stable"
    if prior_growth and current_growth_view and prior_growth != current_growth_view:
        growth_traj = "Improving" if len(current_growth_view) > len(prior_growth) else "Stable"
        changes.append("Growth view updated versus prior review")

    prior_risks = [str(r).lower() for r in (prior.get("prior_risks") or [])]
    risk_traj = "Stable"
    if current_risks and prior_risks:
        if any(r.lower() not in prior_risks for r in current_risks[:2]):
            risk_traj = "Deteriorating"
            changes.append(f"Lead risk shifted toward: {current_risks[0]}")
        elif current_risks and current_risks[0].lower() == prior_risks[0]:
            risk_traj = "Stable"

    prior_conf = float(prior.get("prior_confidence") or 0.0)
    delta = round(float(current_confidence or 0.0) - prior_conf, 3)
    if abs(delta) >= 0.08:
        direction = "up" if delta > 0 else "down"
        changes.append(f"Confidence {direction} by {abs(delta):.2f}")

    traj_pos = sum(1 for t in (bq_traj, moat_traj, growth_traj) if t == "Improving")
    traj_neg = sum(1 for t in (bq_traj, moat_traj, risk_traj) if t == "Deteriorating")
    if traj_pos > traj_neg:
        overall = "Improving"
    elif traj_neg > traj_pos:
        overall = "Deteriorating"
    else:
        overall = "Stable"

    return {
        "what_changed": changes,
        "view_stable": len(changes) == 0,
        "trajectory": overall,
        "confidence_delta": delta,
        "prior_stance": prior_stance or None,
        "current_stance": current_stance,
        "business_quality_trajectory": bq_traj,
        "moat_trajectory": moat_traj,
        "growth_trajectory": growth_traj,
        "risk_trajectory": risk_traj,
    }


def build_memory_record(
    *,
    company: str,
    stance: str,
    quality_grade: str,
    moat_durability: str,
    growth_view: str,
    risks: List[str],
    confidence: float,
    opinion_summary: str,
    comparison: Dict[str, Any],
    prior: Dict[str, Any],
) -> Dict[str, Any]:
    history = list(prior.get("prediction_history") or [])
    history.append(
        {
            "company": company,
            "stance": stance,
            "quality_grade": quality_grade,
            "moat_durability": moat_durability,
            "growth_view": growth_view,
            "risks": risks[:3],
            "confidence": confidence,
            "trajectory": comparison.get("trajectory"),
        }
    )
    lessons = list(prior.get("lessons_learned") or [])
    if comparison.get("what_changed"):
        lessons.append(
            f"Updated view on {company or 'subject'}: {'; '.join(comparison.get('what_changed')[:2])}"
        )
    return {
        "stance": stance,
        "quality_grade": quality_grade,
        "business_quality": {"grade": quality_grade},
        "moat": {"durability": moat_durability},
        "moat_durability": moat_durability,
        "growth_runway": growth_view,
        "risks": risks[:4],
        "confidence": confidence,
        "opinion_summary": opinion_summary,
        "prediction_history": history[-12:],
        "accuracy": prior.get("accuracy"),
        "changes_in_view": list(comparison.get("what_changed") or []),
        "trajectory": comparison.get("trajectory") or "Stable",
        "lessons_learned": lessons[-8:],
    }
