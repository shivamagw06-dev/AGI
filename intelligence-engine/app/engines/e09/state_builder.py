"""E09-003 EngineState builder — schema / conf-1.0 / evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e09.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e09.trend_state import E09State


def build_e09_engine_state(
    trend: E09State,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
    confidence_value: float | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E09_P0": True,
        "E09_BREAKOUT": False,
        "E09_CROSS_ASSET": False,
        "E09_ML": False,
    }
    base = float(
        max(0.0, min(1.0, confidence_value if confidence_value is not None else trend.confidence))
    )
    c_coverage = base
    c_freshness = 1.0 - min(0.5, 0.05 * len(trend.stale_inputs))
    c_stability = max(0.4, min(0.9, 0.55 + 0.35 * trend.persistence - 0.25 * trend.exhaustion))
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_stability) ** (1 / 3))))

    evidence = empty_evidence_pack()
    evidence["positive"].append(
        {
            "id": "e09_pos_composite",
            "claim": f"CTA composite {trend.composite_score:.1f} ({trend.side})",
        }
    )
    evidence["positive"].append(
        {
            "id": "e09_pos_ts_mom",
            "claim": f"TS momentum {trend.ts_momentum:.4f}; vol-scaled {trend.vol_scaled_signal:.3f}",
        }
    )
    if trend.persistence >= 0.5:
        evidence["positive"].append(
            {"id": "e09_pos_persist", "claim": f"Trend persistence {trend.persistence:.2f}"}
        )
    if trend.exhaustion >= 0.6:
        evidence["negative"].append(
            {"id": "e09_neg_exhaust", "claim": f"Trend exhaustion {trend.exhaustion:.2f}"}
        )
        evidence["risks"].append(
            {"id": "e09_risk_reversal", "claim": "Elevated exhaustion raises reversal risk"}
        )
    for sid in trend.stale_inputs[:5]:
        evidence["unknowns"].append({"id": f"e09_stale_{sid}", "claim": f"stale/derived metric {sid}"})
    evidence["risks"].append(
        {"id": "e09_risk_scope", "claim": "P0 single-name CTA signals only (no portfolio/cross-asset)"}
    )

    input_payload = {
        "symbol": trend.symbol,
        "as_of": trend.as_of,
        "composite_score": trend.composite_score,
        "ts_momentum": trend.ts_momentum,
        "vol_scaled_signal": trend.vol_scaled_signal,
        "persistence": trend.persistence,
        "exhaustion": trend.exhaustion,
        "metrics": trend.metrics,
        "model_version": MODEL_VERSION,
        "formula_id": FORMULA_ID,
        "flags": flag_map,
        "e01_ref": trend.e01_ref,
        "e14_ref": trend.e14_ref,
    }
    input_hash = _sha(input_payload)
    signed = max(-1.0, min(1.0, (trend.composite_score - 50.0) / 50.0))

    metadata: dict[str, Any] = {
        "e09_state": trend.model_dump(mode="json"),
        "short_trend": trend.short_trend,
        "medium_trend": trend.medium_trend,
        "long_trend": trend.long_trend,
        "ts_momentum": trend.ts_momentum,
        "vol_scaled_signal": trend.vol_scaled_signal,
        "persistence": trend.persistence,
        "exhaustion": trend.exhaustion,
        "side": trend.side,
        "label": trend.label,
        "formula_id": FORMULA_ID,
        "universe_id": trend.universe_id,
        "sector_id": trend.sector_id,
        "flags": flag_map,
    }

    body = {
        "engine": "E09",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": trend.as_of,
        "universe_id": trend.universe_id,
        "symbol": trend.symbol,
        "score": {
            "raw": trend.composite_score,
            "normalized_0_100": trend.composite_score,
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
            "sample_size": float(len(trend.metrics)),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{trend.symbol} {trend.label}: short={trend.short_trend:.3f}, "
                f"med={trend.medium_trend:.3f}, long={trend.long_trend:.3f}, "
                f"composite={trend.composite_score:.1f}."
            ),
            "top_drivers": [
                f"ts_momentum:{trend.ts_momentum:.4f}",
                f"persistence:{trend.persistence:.2f}",
                f"exhaustion:{trend.exhaustion:.2f}",
            ],
            "falsifiers": [
                "momentum_crash",
                "trend_exhaustion",
                "vol_spike",
                "e14_hard_derisk",
            ],
        },
        "warnings": [],
        "stale_inputs": list(trend.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if trend.e14_ref.get("playbook") == "hard_derisk":
        body["warnings"].append("e14_hard_derisk_context")
    if trend.exhaustion >= 0.75:
        body["warnings"].append("e09_trend_exhaustion")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
