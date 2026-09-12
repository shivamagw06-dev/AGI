"""Decision reasoning — full institutional judgement narrative (not a trade ticket)."""

from __future__ import annotations

from typing import Any


def build_reasoning(
    *,
    question: str,
    evidence: dict[str, Any],
    weights: dict[str, Any],
    conflicts: dict[str, Any],
    uncertainty: dict[str, Any],
    confidence: dict[str, Any],
    consensus: dict[str, Any],
    gate: dict[str, Any],
    inputs: dict[str, Any],
    simulation: dict[str, Any] | None = None,
    learning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t = inputs.get("ticker")
    summary = inputs.get("stack_summary") or {}
    ssl = simulation or (inputs.get("layers") or {}).get("simulation_lab") or {}
    ilm = learning or (inputs.get("layers") or {}).get("institutional_memory") or {}
    alternatives = ssl.get("alternative_strategies") or []
    trade_offs = (ssl.get("committee") or {}).get("trade_offs") or [
        "Franchise quality vs portfolio concentration",
        "Forward scenario mass vs historical learning lessons",
    ]
    judgement = (
        f"For {t}, readiness={gate.get('status')} with confidence {confidence.get('confidence')}. "
        f"Committee position: {consensus.get('committee_position')}. "
        f"Dominant uncertainty: {uncertainty.get('dominant')}. "
        f"Conflicts explained: {conflicts.get('conflict_count')}. "
        "This is institutional judgement — not a buy/sell instruction."
    )
    chain = [
        {"step": "question", "content": question},
        {"step": "evidence", "content": f"Coverage {evidence.get('coverage')} across soft intelligence layers"},
        {"step": "reasoning", "content": f"Transparent weights {weights.get('weights')}"},
        {"step": "alternatives", "content": alternatives[:3] if alternatives else "Strategy alternatives via SSL soft slice"},
        {
            "step": "trade_offs",
            "content": trade_offs,
        },
        {
            "step": "portfolio_impact",
            "content": {
                "net_effect": summary.get("portfolio_net_effect"),
                "fit": summary.get("portfolio_fit"),
                "quality": summary.get("portfolio_quality"),
            },
        },
        {
            "step": "scenario_impact",
            "content": {
                "most_likely": summary.get("forecast_most_likely"),
                "simulation_er": summary.get("simulation_expected_return") or ssl.get("expected_return"),
            },
        },
        {
            "step": "learning_history",
            "content": {
                "lessons": summary.get("memory_lesson_count") or ilm.get("lesson_count"),
                "thinking_improved": summary.get("memory_thinking_improved")
                if summary.get("memory_thinking_improved") is not None
                else ilm.get("thinking_improved"),
            },
        },
        {"step": "final_institutional_judgement", "content": judgement},
    ]
    return {
        "question": question,
        "evidence": evidence,
        "reasoning_chain": chain,
        "alternatives": alternatives[:4] if isinstance(alternatives, list) else alternatives,
        "trade_offs": trade_offs,
        "portfolio_impact": chain[5]["content"],
        "scenario_impact": chain[6]["content"],
        "learning_history": chain[7]["content"],
        "final_institutional_judgement": judgement,
        "never_recommendation_language": True,
    }
