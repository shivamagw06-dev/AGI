"""E03 EngineState builder — schema / conf-1.0 / evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e03.alpha import E03Alpha
from app.engines.e03.mapping import ENGINE_VERSION, MODEL_VERSION, SUBMODEL_ID


def build_e03_state(
    alpha: E03Alpha,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E03_P0": True,
        "E03_PARITY": True,
        "E03_COMPOSITE": False,
        "E03_XS_MODE": False,
        "E03_ML": False,
    }
    c_coverage = 1.0 - min(0.5, 0.05 * len(alpha.stale_inputs))
    c_freshness = c_coverage
    c_model = float(alpha.confidence)
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_model) ** (1 / 3))))

    evidence = empty_evidence_pack()
    for name, contrib in sorted(alpha.contributions.items(), key=lambda kv: kv[1], reverse=True):
        if contrib > 0:
            evidence["positive"].append(
                {"id": f"e03_pos_{name}", "claim": f"{name} contribution {contrib:+.0f}"}
            )
        elif contrib < 0:
            evidence["negative"].append(
                {"id": f"e03_neg_{name}", "claim": f"{name} contribution {contrib:+.0f}"}
            )
    for sid in alpha.stale_inputs:
        evidence["unknowns"].append({"id": f"e03_stale_{sid}", "claim": f"stale input {sid}"})

    input_payload = {
        "symbol": alpha.symbol,
        "as_of": alpha.as_of,
        "agi_tech_score": alpha.agi_tech_score,
        "label": alpha.label,
        "model_version": MODEL_VERSION,
        "flags": flag_map,
        "e01_ref": alpha.e01_ref,
        "e02_ref": alpha.e02_ref,
        "e14_ref": alpha.e14_ref,
        "indicators": alpha.indicators,
    }
    input_hash = _sha(input_payload)
    signed = max(-1.0, min(1.0, (alpha.agi_tech_score - 50.0) / 50.0))

    metadata: dict[str, Any] = {
        "e03_alpha": alpha.model_dump(mode="json"),
        "agi_tech_score": alpha.agi_tech_score,
        "composite_alpha_score": alpha.composite_alpha_score,
        "label": alpha.label,
        "confidence_pct": alpha.confidence_pct,
        "submodel_id": SUBMODEL_ID,
        "universe_id": alpha.universe_id,
        "flags": flag_map,
        "dual_write": False,
    }

    body = {
        "engine": "E03",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": alpha.as_of,
        "universe_id": alpha.universe_id,
        "symbol": alpha.symbol,
        "score": {
            "raw": alpha.agi_tech_score,
            "normalized_0_100": alpha.agi_tech_score,
            "normalized_signed": signed,
            "unit": "score",
        },
        "confidence": {
            "value": conf_value,
            "components": {
                "C_coverage": round(c_coverage, 4),
                "C_freshness": round(c_freshness, 4),
                "C_model": round(c_model, 4),
            },
            "method_version": "conf-1.0",
        },
        "reliability": {
            "sample_size": float(len(alpha.indicators) or 1),
            "historical_accuracy": None,
            "stability": 0.55,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{alpha.symbol} exhibits a {alpha.label.lower()} technical profile "
                f"(SM_AGI_TECH={alpha.agi_tech_score:.1f})."
            ),
            "top_drivers": [SUBMODEL_ID]
            + [
                name
                for name, _ in sorted(
                    alpha.contributions.items(), key=lambda kv: abs(kv[1]), reverse=True
                )[:3]
            ],
            "falsifiers": ["breakdown_below_key_level", "momentum_failure", "volume_dryup"],
        },
        "warnings": [],
        "stale_inputs": list(alpha.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
