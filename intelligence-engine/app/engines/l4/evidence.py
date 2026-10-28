"""L4-002 Evidence Aggregator — unify upstream evidence packs."""

from __future__ import annotations

from typing import Any

from app.engines.l4.collector import CollectedInputs, e01_signed, e03_signed, e14_signed


def aggregate_evidence(inputs: CollectedInputs) -> dict[str, list[dict[str, Any]]]:
    """Build positive / negative / contradictions / unknowns / risks / missing_data."""
    positive: list[dict[str, Any]] = []
    negative: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    missing_data: list[dict[str, Any]] = []

    for eng in inputs.missing:
        missing_data.append({"id": f"l4_missing_{eng.lower()}", "claim": f"{eng} absent", "engine": eng[:3]})

    if inputs.e03 is not None:
        s = e03_signed(inputs.e03)
        claim = f"E03 {inputs.e03.label} (SM_AGI_TECH={inputs.e03.agi_tech_score:.1f})"
        item = {"id": "l4_e03", "claim": claim, "engine": "E03", "score_ref": inputs.e03.agi_tech_score}
        (positive if s > 0.05 else negative if s < -0.05 else unknowns).append(item)
        for feat in (inputs.e03.top_features or [])[:3]:
            bucket = positive if s >= 0 else negative
            bucket.append({"id": f"l4_e03_feat_{feat}", "claim": f"E03 driver {feat}", "engine": "E03"})

    if inputs.e01 is not None:
        s = e01_signed(inputs.e01)
        regime = (inputs.e01.metadata or {}).get("primary_regime", "unknown")
        item = {
            "id": "l4_e01",
            "claim": f"E01 regime {regime}",
            "engine": "E01",
            "score_ref": float(inputs.e01.score.normalized_0_100),
        }
        (positive if s > 0.05 else negative if s < -0.05 else unknowns).append(item)
        _absorb_engine_evidence(inputs.e01.evidence, "E01", positive, negative, unknowns, risks)

    if inputs.e14 is not None:
        s = e14_signed(inputs.e14)
        meta = inputs.e14.metadata or {}
        item = {
            "id": "l4_e14",
            "claim": f"E14 {meta.get('risk_level', 'unknown')} / {meta.get('playbook', 'n/a')}",
            "engine": "E14",
            "score_ref": float(inputs.e14.score.normalized_0_100),
        }
        # E14 defensive signed is negative when risk high
        (negative if s < -0.05 else positive if s > 0.05 else unknowns).append(item)
        risks.append(
            {
                "id": "l4_risk_gate",
                "claim": f"E14 gate={meta.get('gate', 'n/a')} size_mult={meta.get('size_multiplier', 'n/a')}",
                "engine": "E14",
            }
        )
        _absorb_engine_evidence(inputs.e14.evidence, "E14", positive, negative, unknowns, risks)

    if inputs.e02 is not None:
        unknowns.append(
            {
                "id": "l4_e02_context",
                "claim": (
                    f"E02 context dominant={inputs.e02.dominant_factor} "
                    f"composite={inputs.e02.composite_score:.1f} (non-voter)"
                ),
                "engine": "E02",
            }
        )

    # Directional contradiction: E03 bullish vs E14 hard risk / E01 risk-off
    e3 = e03_signed(inputs.e03)
    e1 = e01_signed(inputs.e01)
    e14s = e14_signed(inputs.e14)
    if e3 > 0.2 and e14s < -0.35:
        contradictions.append(
            {
                "id": "l4_con_tech_vs_risk",
                "claim": "Technical constructive vs elevated firm risk",
                "parties": ["E03", "E14"],
            }
        )
    if e3 > 0.2 and e1 < -0.35:
        contradictions.append(
            {
                "id": "l4_con_tech_vs_macro",
                "claim": "Technical constructive vs macro risk-off",
                "parties": ["E03", "E01"],
            }
        )
    if e3 < -0.2 and e1 > 0.35:
        contradictions.append(
            {
                "id": "l4_con_tech_vs_macro_bull",
                "claim": "Technical weak vs constructive macro",
                "parties": ["E03", "E01"],
            }
        )

    return {
        "positive": positive,
        "negative": negative,
        "contradictions": contradictions,
        "unknowns": unknowns,
        "risks": risks,
        "missing_data": missing_data,
    }


def _absorb_engine_evidence(
    pack: dict[str, Any] | None,
    engine: str,
    positive: list[dict[str, Any]],
    negative: list[dict[str, Any]],
    unknowns: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> None:
    if not pack:
        return
    for item in pack.get("positive") or []:
        if isinstance(item, dict):
            positive.append({**item, "engine": item.get("engine", engine)})
    for item in pack.get("negative") or []:
        if isinstance(item, dict):
            negative.append({**item, "engine": item.get("engine", engine)})
    for item in pack.get("unknowns") or []:
        if isinstance(item, dict):
            unknowns.append({**item, "engine": item.get("engine", engine)})
    for item in pack.get("risks") or []:
        if isinstance(item, dict):
            risks.append({**item, "engine": item.get("engine", engine)})

