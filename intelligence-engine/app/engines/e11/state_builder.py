"""E11-003 EngineState builder — soft envelope, conf-1.0, evidence, social caps."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e11.mapping import (
    ENGINE_VERSION,
    FORMULA_ID,
    MODEL_VERSION,
    SOCIAL_WEIGHT_CAP,
    WEIGHT_SET_ID,
)
from app.engines.e11.sentiment_state import E11State


def build_e11_engine_state(
    sent: E11State,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
    confidence_value: float | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E11_P0": True,
        "E11_SOCIAL": False,
        "E11_TRANSCRIPTS": False,
        "E11_LLM": False,
        "E11_ML": False,
        "E11_ALTDATA": False,
    }
    base = float(
        max(0.0, min(1.0, confidence_value if confidence_value is not None else sent.confidence))
    )
    c_coverage = base
    c_freshness = max(0.4, min(1.0, 1.0 - min(0.5, (sent.freshness_hours or 0.0) / 168.0)))
    c_stability = max(0.4, min(0.9, 0.45 + 0.40 * sent.reliability_weight + 0.15 * sent.decay_weight))
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_stability) ** (1 / 3))))

    evidence = empty_evidence_pack()
    evidence["positive"].append(
        {
            "id": "e11_pos_news",
            "claim": f"News sentiment {sent.news_score:.1f} ({sent.label})",
        }
    )
    evidence["positive"].append(
        {
            "id": "e11_pos_entity",
            "claim": f"Entity {sent.entity_id} conf={sent.entity_confidence:.2f}",
        }
    )
    evidence["positive"].append(
        {
            "id": "e11_pos_decay",
            "claim": (
                f"Decay {sent.decay_weight:.2f}; reliability {sent.reliability_weight:.2f}; "
                f"freshness {sent.freshness_hours:.1f}h"
            ),
        }
    )
    evidence["positive"].append(
        {
            "id": "e11_pos_soft_cap",
            "claim": (
                f"Soft voter weight {sent.soft_voter_weight:.3f}; "
                f"social_cap={SOCIAL_WEIGHT_CAP} social_enabled={sent.social_enabled}"
            ),
        }
    )
    for sid in sent.stale_inputs[:5]:
        evidence["unknowns"].append({"id": f"e11_stale_{sid}", "claim": f"stale/derived {sid}"})
    evidence["risks"].append(
        {
            "id": "e11_risk_scope",
            "claim": "P0 news soft voter only — broker/ownership P1; social/LLM/ML off",
        }
    )

    input_payload = {
        "symbol": sent.symbol,
        "as_of": sent.as_of,
        "entity_id": sent.entity_id,
        "news_score": sent.news_score,
        "composite_score": sent.composite_score,
        "reliability_weight": sent.reliability_weight,
        "decay_weight": sent.decay_weight,
        "soft_voter_weight": sent.soft_voter_weight,
        "model_version": MODEL_VERSION,
        "formula_id": FORMULA_ID,
        "weight_set_id": WEIGHT_SET_ID,
        "flags": flag_map,
        "e01_ref": sent.e01_ref,
        "e14_ref": sent.e14_ref,
    }
    input_hash = _sha(input_payload)
    signed = max(-1.0, min(1.0, (sent.composite_score - 50.0) / 50.0))

    metadata: dict[str, Any] = {
        "e11_state": sent.model_dump(mode="json"),
        "entity_id": sent.entity_id,
        "news_score": sent.news_score,
        "reliability_weight": sent.reliability_weight,
        "decay_weight": sent.decay_weight,
        "freshness_hours": sent.freshness_hours,
        "soft_voter_weight": sent.soft_voter_weight,
        "social_weight_cap": SOCIAL_WEIGHT_CAP,
        "social_enabled": False,
        "side": sent.side,
        "label": sent.label,
        "formula_id": FORMULA_ID,
        "weight_set_id": WEIGHT_SET_ID,
        "universe_id": sent.universe_id,
        "flags": flag_map,
    }

    body = {
        "engine": "E11",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": sent.as_of,
        "universe_id": sent.universe_id,
        "symbol": sent.symbol,
        "score": {
            "raw": sent.composite_score,
            "normalized_0_100": sent.composite_score,
            "normalized_signed": signed,
            "unit": "score",
        },
        "confidence": {
            "value": conf_value,
            "components": {
                "C_coverage": round(c_coverage, 4),
                "C_freshness": round(c_freshness, 4),
                "C_stability": round(c_stability, 4),
            },
            "method_version": "conf-1.0",
        },
        "reliability": {
            "sample_size": float(sent.doc_count or 1),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{sent.symbol} {sent.label}: news={sent.news_score:.1f}, "
                f"decay={sent.decay_weight:.2f}, soft_w={sent.soft_voter_weight:.3f}."
            ),
            "top_drivers": [
                f"news:{sent.news_score:.1f}",
                f"entity:{sent.entity_id}",
                f"decay:{sent.decay_weight:.2f}",
            ],
            "falsifiers": ["downgrade_cluster", "entity_unlink", "e14_hard_derisk"],
        },
        "warnings": [],
        "stale_inputs": list(sent.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if sent.e14_ref.get("playbook") == "hard_derisk":
        body["warnings"].append("e14_hard_derisk_context")
    if "news_synthesized" in sent.stale_inputs:
        body["warnings"].append("e11_synthetic_news")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
