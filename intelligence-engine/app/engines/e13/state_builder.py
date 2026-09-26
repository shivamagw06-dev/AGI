"""E13-003 EngineState builder — schema / conf-1.0 / evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e13.fundamental import E13Fundamental
from app.engines.e13.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION


def build_e13_state(
    fundamental: E13Fundamental,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
    confidence_value: float | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E13_P0": True,
        "E13_REVISIONS": False,
        "E13_MOAT": False,
        "E13_ML": False,
    }
    base = float(
        max(
            0.0,
            min(1.0, confidence_value if confidence_value is not None else fundamental.confidence),
        )
    )
    c_coverage = base
    c_freshness = 1.0 - min(0.5, 0.05 * len(fundamental.stale_inputs))
    c_stability = 0.72
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_stability) ** (1 / 3))))

    evidence = empty_evidence_pack()
    evidence["positive"].append(
        {
            "id": "e13_pos_composite",
            "claim": f"Composite fundamental score {fundamental.composite_score:.1f} ({fundamental.side})",
        }
    )
    evidence["positive"].append(
        {
            "id": "e13_pos_quality",
            "claim": f"Quality score {fundamental.quality_score:.1f}",
        }
    )
    if fundamental.value_score >= 55:
        evidence["positive"].append(
            {"id": "e13_pos_value", "claim": f"Value score {fundamental.value_score:.1f}"}
        )
    else:
        evidence["negative"].append(
            {"id": "e13_neg_value", "claim": f"Value score {fundamental.value_score:.1f} (soft)"}
        )
    if fundamental.side == "short":
        evidence["negative"].append(
            {"id": "e13_neg_side", "claim": f"Fundamental short bias ({fundamental.label})"}
        )
    for sid in fundamental.stale_inputs[:5]:
        evidence["unknowns"].append({"id": f"e13_stale_{sid}", "claim": f"stale/derived metric {sid}"})
    evidence["risks"].append({"id": "e13_risk_value_trap", "claim": "Value trap / accounting quality risk"})
    if not fundamental.metrics.get("revenue_growth"):
        evidence["missing_data"].append({"id": "e13_miss_growth", "claim": "explicit revenue growth series"})

    input_payload = {
        "symbol": fundamental.symbol,
        "as_of": fundamental.as_of,
        "composite_score": fundamental.composite_score,
        "pillar_scores": fundamental.pillar_scores,
        "metrics": fundamental.metrics,
        "model_version": MODEL_VERSION,
        "formula_id": FORMULA_ID,
        "flags": flag_map,
        "e01_ref": fundamental.e01_ref,
        "e14_ref": fundamental.e14_ref,
    }
    input_hash = _sha(input_payload)
    signed = max(-1.0, min(1.0, (fundamental.composite_score - 50.0) / 50.0))

    metadata: dict[str, Any] = {
        "e13_fundamental": fundamental.model_dump(mode="json"),
        "quality_score": fundamental.quality_score,
        "value_score": fundamental.value_score,
        "growth_score": fundamental.growth_score,
        "balance_sheet_score": fundamental.balance_sheet_score,
        "pillar_scores": fundamental.pillar_scores,
        "side": fundamental.side,
        "label": fundamental.label,
        "formula_id": FORMULA_ID,
        "universe_id": fundamental.universe_id,
        "sector_id": fundamental.sector_id,
        "flags": flag_map,
    }

    body = {
        "engine": "E13",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": fundamental.as_of,
        "universe_id": fundamental.universe_id,
        "symbol": fundamental.symbol,
        "score": {
            "raw": fundamental.composite_score,
            "normalized_0_100": fundamental.composite_score,
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
            "sample_size": float(len(fundamental.metrics)),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{fundamental.symbol} fundamental composite {fundamental.composite_score:.1f} "
                f"({fundamental.label}); quality {fundamental.quality_score:.1f}, "
                f"value {fundamental.value_score:.1f}."
            ),
            "top_drivers": [
                f"quality:{fundamental.quality_score:.1f}",
                f"value:{fundamental.value_score:.1f}",
                f"growth:{fundamental.growth_score:.1f}",
            ],
            "falsifiers": [
                "earnings_fraud",
                "value_trap",
                "leverage_spike",
                "e14_hard_derisk",
            ],
        },
        "warnings": [],
        "stale_inputs": list(fundamental.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if fundamental.e14_ref.get("playbook") == "hard_derisk":
        body["warnings"].append("e14_hard_derisk_context")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
