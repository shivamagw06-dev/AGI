"""Production façade for AGI observability (LangSmith tracing)."""

from __future__ import annotations

from typing import Any

from observability.schema import (
    COMPANY,
    FREEZE_LOCKS,
    MODULE_CODE,
    OBSERVABILITY_VERSION,
    PROGRAMME,
    api_key,
    config,
    endpoint,
    is_enabled,
    project,
    sdk_available,
    tracing_requested,
)
from observability.tracing import flush


def status() -> dict[str, Any]:
    enabled = is_enabled()
    if enabled:
        state = "tracing"
    elif not api_key():
        state = "disabled_no_api_key"
    elif not tracing_requested():
        state = "disabled_by_flag"
    elif not sdk_available():
        state = "disabled_sdk_missing"
    else:
        state = "disabled"
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "version": OBSERVABILITY_VERSION,
        "status": "ok",
        "tracing_state": state,
        "enabled": enabled,
        "project": project(),
        "endpoint": endpoint(),
        "observability_only": True,
        "never_changes_answers": True,
        "fails_open": True,
        "freeze_locks": dict(FREEZE_LOCKS),
        "api_prefix": "/v1/observability",
        "required_env": {
            "LANGSMITH_API_KEY": "required",
            "LANGSMITH_TRACING": "optional (defaults on when key present)",
            "LANGSMITH_PROJECT": "optional",
            "LANGSMITH_WORKSPACE_ID": "optional (org-scoped keys)",
        },
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    cfg = config()
    traced_stages = [
        "ask.pipeline (root)",
        "intent_resolution",
        "knowledge+evidence",
        "answer_assembly",
        "framework_selection",
        "playbook_selection",
        "evidence_graph",
        "temporal_integrity.replay_guard",
        "institutional_analog_intelligence",
        "evidence_weighting",
        "evidence_weighting.score",
        "hypothesis_generation",
        "hypothesis_generation.score",
        "hypothesis_generation.hypothesis",
        "hypothesis_evaluation",
        "hypothesis_evaluation.hypothesis",
        "committee_deliberation",
        "committee_deliberation.case",
        "confidence_calibration",
        "investment_thesis",
        "decision_office",
        "portfolio_office",
        "monitoring_office",
        "learning_office",
        "reasoning.governance",
        "institutional_communication",
        "llm:gemini",
        "llm:openai",
    ]
    return {
        **cfg,
        "traced_stages": traced_stages,
        "n_traced_stages": len(traced_stages),
        "cli_hint": (
            "langsmith trace list --project "
            f"{cfg.get('project')} --limit 10 --api-key $LANGSMITH_API_KEY"
        ),
        "skill": "langsmith-trace",
    }


def verify() -> dict[str, Any]:
    """Emit one synthetic trace so operators can confirm the pipe end-to-end."""
    from observability.tracing import span

    enabled = is_enabled()
    emitted = False
    if enabled:
        with span(
            "agi.observability.verify",
            run_type="chain",
            inputs={"check": "connectivity"},
            tags=["verify"],
        ) as sp:
            sp.add_metadata(source="observability.verify")
            sp.end(outputs={"ok": True})
            emitted = bool(getattr(sp, "active", False))
        flush()
    return {
        "enabled": enabled,
        "trace_emitted": emitted,
        "project": project(),
        "endpoint": endpoint(),
        "note": (
            "Set LANGSMITH_API_KEY (and LANGSMITH_TRACING=true) to emit traces."
            if not enabled
            else "Check LangSmith for run name 'agi.observability.verify'."
        ),
        "fabricated": False,
    }
