"""S11 Decision Quality recording + S12 Outcome registration (no learning)."""

from __future__ import annotations

import time
import uuid
from typing import Any

from ask_pipeline.store import utc_now


def record_decision_quality(
    *,
    context: dict[str, Any],
    governance: dict[str, Any],
    evidence: dict[str, Any],
    telemetry_latency_ms: int | None = None,
) -> dict[str, Any]:
    """Record-only IDQ decision object — no scoring redesign."""
    started = time.time()
    run_id = governance.get("run_id") or context.get("pipeline_id")
    decision_id = f"idq_ask_{uuid.uuid4().hex[:14]}"
    committee = governance.get("committee") or {}
    frameworks = governance.get("frameworks") or []
    confidences = [
        float(f["confidence"])
        for f in frameworks
        if isinstance(f.get("confidence"), (int, float))
    ]
    confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    primary = (governance.get("entity") or {}) if isinstance(governance.get("entity"), dict) else {}
    raw = {
        "decision_id": decision_id,
        "question": context.get("question") or governance.get("question"),
        "entity": primary.get("entity_id") or (context.get("ticker_hint")),
        "sector": None,
        "date": utc_now()[:10],
        "available_from": utc_now()[:10],
        "research": {
            "run_id": run_id,
            "pipeline_id": context.get("pipeline_id"),
            "replay_id": context.get("replay_id"),
            "question_type": governance.get("question_type"),
            "path": governance.get("path"),
            "narrative_allowed": governance.get("narrative_allowed"),
            "iki": bool(governance.get("ipi") is not None or governance.get("iki")),
        },
        "portfolio": governance.get("ipi") or governance.get("portfolio_recommendation") or {},
        "evidence_pack": {
            "coverage": evidence.get("coverage"),
            "pack_count": evidence.get("pack_count"),
            "packs_found": evidence.get("packs_found"),
            "governance_pack_keys": list((evidence.get("governance_packs") or {}).keys()),
        },
        "frameworks": [
            {"id": f.get("framework_id") or f.get("id"), "status": f.get("status"), "confidence": f.get("confidence")}
            for f in frameworks
        ],
        "primary_framework": (frameworks[0].get("framework_id") if frameworks else None),
        "committee": committee,
        "confidence": confidence,
        "djg": governance.get("justification_graph") or {},
        "pdg": governance.get("portfolio_decision_graph") or {},
        "outcome_graph": {"available": False},
        "learning_proposal": None,
        "macro_regime": None,
        "latency_ms": telemetry_latency_ms or governance.get("execution_ms"),
        "coverage": evidence.get("coverage"),
        "quality": evidence.get("coverage"),
        "replay_id": context.get("replay_id"),
        "fabricated": False,
    }
    try:
        from decision_quality.objects.decision import compile_decision_object

        obj = compile_decision_object(raw)
        return {
            "stage": "decision_quality_recording",
            "status": "executed",
            "decision_id": decision_id,
            "object_found": True,
            "recording_only": True,
            "scoring_changed": False,
            "duration_ms": int((time.time() - started) * 1000),
            "snapshot_keys": list(obj.keys())[:20] if isinstance(obj, dict) else [],
        }
    except Exception as exc:
        return {
            "stage": "decision_quality_recording",
            "status": "error",
            "decision_id": decision_id,
            "error": str(exc)[:200],
            "recording_only": True,
            "duration_ms": int((time.time() - started) * 1000),
        }


def register_outcome(
    *,
    policy: dict[str, Any],
    governance: dict[str, Any],
) -> dict[str, Any]:
    """Registration only — never evaluate / never CAL."""
    started = time.time()
    if not policy.get("run_outcome_registration"):
        return {
            "stage": "outcome_registration",
            "status": "skipped_by_policy",
            "reason": (policy.get("skips") or {}).get("outcome") or "skipped_by_policy",
            "learning": False,
            "duration_ms": int((time.time() - started) * 1000),
        }

    ipi = governance.get("ipi") or {}
    # Prefer existing track handle from govern_answer
    if (governance.get("ioi") or {}).get("decision_id"):
        return {
            "stage": "outcome_registration",
            "status": "executed",
            "decision_id": governance["ioi"]["decision_id"],
            "source": "govern_answer.ioi",
            "learning": False,
            "duration_ms": int((time.time() - started) * 1000),
        }

    if ipi:
        try:
            from institutional_reasoning.ioi.pipeline import track_decision

            tracked = track_decision(ipi, research_record=governance)
            return {
                "stage": "outcome_registration",
                "status": "executed" if tracked.get("found") else "empty",
                "decision_id": tracked.get("decision_id"),
                "source": "ioi.track_decision",
                "learning": False,
                "duration_ms": int((time.time() - started) * 1000),
            }
        except Exception as exc:
            return {
                "stage": "outcome_registration",
                "status": "error",
                "error": str(exc)[:200],
                "learning": False,
                "duration_ms": int((time.time() - started) * 1000),
            }

    # Soft registration without IPI — lifecycle stub via register_decision if possible
    try:
        from institutional_reasoning.ioi.lifecycle import register_decision

        stub = {
            "recommendation": {
                "action": "Watch",
                "conclusion": (governance.get("committee") or {}).get("conclusion")
                or "Research path registration",
            },
            "withheld": not governance.get("narrative_allowed"),
            "ticker": ((governance.get("entity") or {}) or {}).get("entity_id"),
            "entity_id": ((governance.get("entity") or {}) or {}).get("entity_id"),
            "run_id": governance.get("run_id"),
        }
        life = register_decision(stub, research_record=governance)
        return {
            "stage": "outcome_registration",
            "status": "executed",
            "decision_id": life.get("decision_id"),
            "source": "ioi.register_decision_soft",
            "learning": False,
            "duration_ms": int((time.time() - started) * 1000),
        }
    except Exception as exc:
        return {
            "stage": "outcome_registration",
            "status": "error",
            "error": str(exc)[:200],
            "learning": False,
            "duration_ms": int((time.time() - started) * 1000),
        }
