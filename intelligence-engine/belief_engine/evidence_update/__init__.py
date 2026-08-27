"""Evidence update — convert support/contradiction/effects into log-likelihood ratios."""

from __future__ import annotations

from typing import Any

from belief_engine.schema import EFFECT_LOG_LR, FALSIFICATION_LOG_LR


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def collect_log_likelihoods(tested: dict[str, Any], falsification: dict[str, Any] | None = None) -> dict[str, Any]:
    """Aggregate log-LR contributions from evidence effects and falsification."""
    contributions: list[dict[str, Any]] = []
    total = 0.0

    for e in _safe_list(tested.get("evidence_effects")):
        effect = str(e.get("effect") or "Neutral")
        llr = float(EFFECT_LOG_LR.get(effect, 0.0))
        # Mild strength scaling when available (0-100)
        strength = e.get("support_score") or e.get("contradiction_score")
        if strength is None and e.get("probability_delta") is not None:
            strength = abs(float(e.get("probability_delta"))) * 100
        if strength is not None:
            scale = 0.6 + 0.4 * min(1.0, abs(float(strength)) / 100.0)
            llr *= scale
        total += llr
        contributions.append(
            {
                "evidence_id": e.get("id"),
                "effect": effect,
                "log_lr": round(llr, 4),
                "text": e.get("text"),
            }
        )

    # Fallback when effects absent — use support/contradiction scores
    if not contributions:
        support = float(tested.get("support_score") or 0) / 100.0
        contra = float(tested.get("contradiction_score") or 0) / 100.0
        llr = 1.1 * support - 1.2 * contra
        total += llr
        contributions.append({"evidence_id": None, "effect": "aggregate", "log_lr": round(llr, 4)})

    fals = falsification or {}
    severity = str(fals.get("severity") or fals.get("status") or "").lower()
    if severity:
        # Map common falsification statuses
        key = "inconclusive"
        if "falsif" in severity or "reject" in severity or "refut" in severity:
            key = "falsified"
        elif "weaken" in severity or "challeng" in severity:
            key = "weakened"
        elif "stress" in severity or "partial" in severity:
            key = "stressed"
        elif "surviv" in severity or "pass" in severity or "hold" in severity:
            key = "survived"
        f_llr = float(FALSIFICATION_LOG_LR.get(key, -0.1))
        total += f_llr
        contributions.append(
            {
                "evidence_id": "falsification",
                "effect": key,
                "log_lr": round(f_llr, 4),
                "text": fals.get("summary") or fals.get("note") or severity,
            }
        )

    # Missing evidence dampens extreme updates slightly via small negative LR
    missing_n = len(_safe_list(tested.get("missing_evidence")))
    if missing_n:
        miss_llr = -0.08 * min(missing_n, 4)
        total += miss_llr
        contributions.append(
            {
                "evidence_id": "missing",
                "effect": "missing_evidence",
                "log_lr": round(miss_llr, 4),
                "text": f"{missing_n} missing evidence items",
            }
        )

    return {
        "log_likelihood_total": round(total, 4),
        "contributions": contributions,
        "supporting_evidence": _safe_list(tested.get("supporting_evidence")),
        "contradicting_evidence": _safe_list(tested.get("contradicting_evidence")),
    }
