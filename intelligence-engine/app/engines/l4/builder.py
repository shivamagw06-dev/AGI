"""L4-004 L4Opinion Builder — assemble canonical shadow opinion."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.engines.l4.collector import CollectedInputs
from app.engines.l4.conflict import ConflictResolution
from app.engines.l4.fusion.vote import FusionResult
from app.engines.l4.mapping import MODEL_VERSION
from app.engines.l4.opinion import L4Opinion


def build_opinion(
    inputs: CollectedInputs,
    *,
    evidence: dict[str, list[dict[str, Any]]],
    resolution: ConflictResolution,
    fusion: FusionResult,
    universe_id: str,
) -> L4Opinion:
    e14_gate = None
    if inputs.e14 is not None:
        e14_gate = str((inputs.e14.metadata or {}).get("gate") or "") or None

    drivers = [d.get("engine") for d in fusion.dominant_drivers if d.get("engine") != "E02"]
    conflicting = sorted(
        {p for c in resolution.conflicts for p in (c.get("parties") or [])}
    )
    summary = (
        f"Shadow composite opinion is {fusion.label} "
        f"(score={fusion.composite_score:.1f}, c={fusion.confidence:.2f}). "
        f"Drivers: {', '.join(str(d) for d in drivers[:3]) or 'n/a'}. "
        f"Conflicts: {', '.join(conflicting) or 'none'}. "
        f"Production remains E03."
    )
    explanation = {
        "summary": summary,
        "why": resolution.notes,
        "top_drivers": drivers[:5],
        "contributing_engines": [c["engine"] for c in fusion.engine_contributions],
        "conflicting_engines": conflicting,
        "risks": [r.get("claim") for r in evidence.get("risks") or []],
        "falsifiers": ["E14_hard_derisk", "E01_crisis", "E03_breakdown"],
    }

    digest = _sha(
        {
            "symbol": inputs.symbol,
            "as_of": inputs.as_of,
            "label": fusion.label,
            "score": fusion.composite_score,
            "upstream": inputs.upstream_hashes,
            "model_version": MODEL_VERSION,
            "resolution": resolution.resolution,
        }
    )

    return L4Opinion(
        as_of=inputs.as_of,
        universe_id=universe_id,
        symbol=inputs.symbol,
        label=fusion.label,
        composite_score=fusion.composite_score,
        confidence=fusion.confidence,
        positive_evidence=list(evidence.get("positive") or []),
        negative_evidence=list(evidence.get("negative") or []),
        contradictions=list(resolution.conflicts),
        unknowns=list(evidence.get("unknowns") or []),
        dominant_drivers=fusion.dominant_drivers,
        explanation=explanation,
        engine_contributions=fusion.engine_contributions,
        hierarchy_trace=list(resolution.hierarchy_trace),
        conflict_resolution=resolution.resolution,
        confidence_mult=resolution.confidence_mult,
        e14_gate=e14_gate,
        weight_set_id=fusion.weight_set_id,
        shadow=True,
        primary=False,
        upstream_hashes=dict(inputs.upstream_hashes),
        stale_inputs=[],
        missing_inputs=list(inputs.missing),
        model_version=MODEL_VERSION,
        hash=digest,
    )


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
