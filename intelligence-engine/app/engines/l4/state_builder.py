"""L4 EngineState builder — schema / conf-1.0 / evidence compliant. Shadow only."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.l4.mapping import ENGINE_VERSION, MODEL_VERSION
from app.engines.l4.opinion import L4Opinion


def build_l4_state(
    opinion: L4Opinion,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "L4_SHADOW": True,
        "L4_PRIMARY": False,
        "L4_BAYES": False,
        "L4_ML": False,
        "L4_PROBABILITY": False,
    }
    c_coverage = 1.0 - min(0.5, 0.1 * len(opinion.missing_inputs))
    c_freshness = 1.0 - min(0.4, 0.05 * len(opinion.stale_inputs))
    c_model = float(opinion.confidence)
    fusion_mult = float(opinion.confidence_mult)
    conf_value = float(
        max(0.05, min(0.95, ((c_coverage * c_freshness * c_model) ** (1 / 3)) * fusion_mult))
    )

    evidence = empty_evidence_pack()
    evidence["positive"] = list(opinion.positive_evidence)
    evidence["negative"] = list(opinion.negative_evidence)
    evidence["contradictions"] = list(opinion.contradictions)
    evidence["unknowns"] = list(opinion.unknowns)
    evidence["risks"] = [
        {"id": "l4_shadow", "claim": "L4 shadow mode — production remains E03"}
    ]
    evidence["missing_data"] = [
        {"id": f"l4_miss_{m}", "claim": f"missing {m}"} for m in opinion.missing_inputs
    ]

    signed = max(-1.0, min(1.0, (opinion.composite_score - 50.0) / 50.0))
    input_payload = {
        "symbol": opinion.symbol,
        "as_of": opinion.as_of,
        "label": opinion.label,
        "composite_score": opinion.composite_score,
        "upstream_hashes": opinion.upstream_hashes,
        "model_version": MODEL_VERSION,
        "flags": flag_map,
    }
    input_hash = _sha(input_payload)

    metadata: dict[str, Any] = {
        "l4_opinion": opinion.model_dump(mode="json"),
        "label": opinion.label,
        "shadow": True,
        "primary": False,
        "weight_set_id": opinion.weight_set_id,
        "contributing_engines": [c["engine"] for c in opinion.engine_contributions],
        "conflicting_engines": [
            p for c in opinion.contradictions for p in (c.get("parties") or [])
        ],
        "flags": flag_map,
        "production_influence": False,
    }

    body = {
        "engine": "L4",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": opinion.as_of,
        "universe_id": opinion.universe_id,
        "symbol": opinion.symbol,
        "score": {
            "raw": opinion.composite_score,
            "normalized_0_100": opinion.composite_score,
            "normalized_signed": signed,
            "unit": "score",
        },
        "confidence": {
            "value": conf_value,
            "components": {
                "C_coverage": round(c_coverage, 4),
                "C_freshness": round(c_freshness, 4),
                "C_model": round(c_model, 4),
                "fusion_mult": round(fusion_mult, 4),
            },
            "method_version": "conf-1.0",
        },
        "reliability": {
            "sample_size": float(len(opinion.engine_contributions) or 1),
            "historical_accuracy": None,
            "stability": 0.5,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": opinion.explanation.get("summary", ""),
            "top_drivers": opinion.explanation.get("top_drivers", []),
            "falsifiers": opinion.explanation.get("falsifiers", []),
        },
        "warnings": ["shadow_mode"],
        "stale_inputs": list(opinion.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if flag_map.get("L4_PRIMARY"):
        body["warnings"].append("l4_primary_enabled_unexpected")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
