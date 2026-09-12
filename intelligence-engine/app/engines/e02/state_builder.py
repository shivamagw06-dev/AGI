"""E02 EngineState builder — schema / conf-1.0 / evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e02.exposure import E02Exposure
from app.engines.e02.mapping import ENGINE_VERSION, MODEL_VERSION


def build_e02_state(
    exposure: E02Exposure,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
    confidence_value: float | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E02_P0": True,
        "E02_TIMING": False,
        "E02_ROTATION": False,
        "E02_SMART_BETA": False,
        "E02_ML": False,
    }
    conf = float(
        max(0.0, min(1.0, confidence_value if confidence_value is not None else exposure.factor_confidence))
    )
    c_coverage = conf
    c_freshness = 1.0 - min(0.5, 0.05 * len(exposure.stale_inputs))
    c_stability = 0.70
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_stability) ** (1 / 3))))

    evidence = empty_evidence_pack()
    for fid, score in sorted(exposure.scores.items(), key=lambda kv: kv[1], reverse=True)[:3]:
        evidence["positive"].append(
            {"id": f"e02_pos_{fid}", "claim": f"{fid} score {score:.1f}"}
        )
    for fid, score in sorted(exposure.scores.items(), key=lambda kv: kv[1])[:2]:
        if score <= 35:
            evidence["negative"].append(
                {"id": f"e02_neg_{fid}", "claim": f"{fid} score {score:.1f} (low)"}
            )
    for sid in exposure.stale_inputs:
        evidence["unknowns"].append({"id": f"e02_stale_{sid}", "claim": f"stale metric {sid}"})

    input_payload = {
        "symbol": exposure.symbol,
        "as_of": exposure.as_of,
        "scores": exposure.scores,
        "loadings": exposure.loadings,
        "model_version": MODEL_VERSION,
        "flags": flag_map,
        "e01_ref": exposure.e01_ref,
        "e14_ref": exposure.e14_ref,
    }
    input_hash = _sha(input_payload)

    signed = max(-1.0, min(1.0, (exposure.composite_score - 50.0) / 50.0))
    metadata: dict[str, Any] = {
        "e02_exposure": exposure.model_dump(mode="json"),
        "dominant_factor": exposure.dominant_factor,
        "style_box": exposure.style_box,
        "scores": exposure.scores,
        "loadings": exposure.loadings,
        "factor_features": exposure.factor_features,
        "universe_id": exposure.universe_id,
        "sector_id": exposure.sector_id,
        "flags": flag_map,
    }

    body = {
        "engine": "E02",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": exposure.as_of,
        "universe_id": exposure.universe_id,
        "symbol": exposure.symbol,
        "score": {
            "raw": exposure.composite_score,
            "normalized_0_100": exposure.composite_score,
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
            "sample_size": float(len(exposure.scores)),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{exposure.symbol} dominant factor {exposure.dominant_factor} "
                f"with composite {exposure.composite_score:.1f} "
                f"({exposure.style_box.get('size')}/{exposure.style_box.get('style')})."
            ),
            "top_drivers": [exposure.dominant_factor] + [
                m["metric"] for m in exposure.top_metrics[:2]
            ],
            "falsifiers": [
                "momentum_crash",
                "value_trap",
                "liquidity_dryup",
                "e14_hard_derisk",
            ],
        },
        "warnings": [],
        "stale_inputs": list(exposure.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if exposure.e14_ref.get("playbook") == "hard_derisk":
        body["warnings"].append("e14_hard_derisk_context")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
