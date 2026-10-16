"""E05-003 EngineState builder — schema / conf-1.0 / evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e05.event_state import E05EventState
from app.engines.e05.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION


def build_e05_engine_state(
    event: E05EventState,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
    confidence_value: float | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E05_P0": True,
        "E05_DEAL_PROBABILITY": False,
        "E05_TRANSCRIPTS": False,
        "E05_ML": False,
    }
    base = float(
        max(0.0, min(1.0, confidence_value if confidence_value is not None else event.confidence))
    )
    c_coverage = base
    c_freshness = 1.0 - min(0.5, 0.05 * len(event.stale_inputs))
    c_stability = max(0.4, min(0.9, 0.50 + 0.40 * event.decay_factor))
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_stability) ** (1 / 3))))

    evidence = empty_evidence_pack()
    evidence["positive"].append(
        {
            "id": "e05_pos_composite",
            "claim": f"Event composite {event.composite_score:.1f} ({event.label})",
        }
    )
    if event.primary_event_type:
        evidence["positive"].append(
            {
                "id": "e05_pos_primary",
                "claim": (
                    f"Primary {event.primary_event_type}; "
                    f"surprise={event.surprise_score:.1f}; decay={event.decay_factor:.2f}"
                ),
            }
        )
    if event.expected_event_impact >= 10:
        evidence["positive"].append(
            {
                "id": "e05_pos_impact",
                "claim": f"Expected impact +{event.expected_event_impact:.1f}",
            }
        )
    elif event.expected_event_impact <= -10:
        evidence["negative"].append(
            {
                "id": "e05_neg_impact",
                "claim": f"Expected impact {event.expected_event_impact:.1f}",
            }
        )
    for sid in event.stale_inputs[:5]:
        evidence["unknowns"].append({"id": f"e05_stale_{sid}", "claim": f"stale/derived {sid}"})
    evidence["risks"].append(
        {
            "id": "e05_risk_scope",
            "claim": "P0 calendar/CA/surprise/decay only — no deal-prob/transcripts/ML",
        }
    )

    input_payload = {
        "symbol": event.symbol,
        "as_of": event.as_of,
        "composite_score": event.composite_score,
        "surprise_score": event.surprise_score,
        "decay_factor": event.decay_factor,
        "event_importance": event.event_importance,
        "primary_event_type": event.primary_event_type,
        "n_upcoming": len(event.upcoming_events),
        "n_recent": len(event.recent_events),
        "model_version": MODEL_VERSION,
        "formula_id": FORMULA_ID,
        "flags": flag_map,
        "e01_ref": event.e01_ref,
        "e14_ref": event.e14_ref,
    }
    input_hash = _sha(input_payload)
    signed = max(-1.0, min(1.0, event.expected_event_impact / 100.0))

    metadata: dict[str, Any] = {
        "e05_state": event.model_dump(mode="json"),
        "primary_event_type": event.primary_event_type,
        "event_importance": event.event_importance,
        "surprise_score": event.surprise_score,
        "decay_factor": event.decay_factor,
        "expected_event_impact": event.expected_event_impact,
        "days_since_event": event.days_since_event,
        "days_until_event": event.days_until_event,
        "side": event.side,
        "label": event.label,
        "formula_id": FORMULA_ID,
        "universe_id": event.universe_id,
        "sector_id": event.sector_id,
        "flags": flag_map,
    }

    body = {
        "engine": "E05",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": event.as_of,
        "universe_id": event.universe_id,
        "symbol": event.symbol,
        "score": {
            "raw": event.composite_score,
            "normalized_0_100": event.composite_score,
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
            "sample_size": float(len(event.recent_events) + len(event.upcoming_events)),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{event.symbol} {event.label}: composite={event.composite_score:.1f}, "
                f"surprise={event.surprise_score:.1f}, decay={event.decay_factor:.2f}, "
                f"primary={event.primary_event_type}."
            ),
            "top_drivers": [
                f"primary:{event.primary_event_type}",
                f"surprise:{event.surprise_score:.2f}",
                f"decay:{event.decay_factor:.2f}",
            ],
            "falsifiers": [
                "revision_collapse",
                "event_cancellation",
                "e14_hard_derisk",
            ],
        },
        "warnings": [],
        "stale_inputs": list(event.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if event.e14_ref.get("playbook") == "hard_derisk":
        body["warnings"].append("e14_hard_derisk_context")
    if "events_synthesized" in event.stale_inputs:
        body["warnings"].append("e05_synthetic_calendar")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
