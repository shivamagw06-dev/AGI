"""Production façade — Temporal Integrity & Replay Certification (TIRC)."""

from __future__ import annotations

from typing import Any

from temporal_integrity.certification.engine import certify_from_iel_summary
from temporal_integrity.dashboard.board import build_board
from temporal_integrity.replay_guard.guard import apply_replay_guard
from temporal_integrity.reports.builder import build_markdown
from temporal_integrity.schema import COMPANY, FREEZE_LOCKS, MODULE_CODE, PROGRAMME, TIRC_VERSION
from temporal_integrity import store as tirc_store
from temporal_integrity.telemetry.metrics import snapshot
from temporal_integrity.validator.contract import evaluate_object


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "version": TIRC_VERSION,
        "programme": PROGRAMME,
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "Historical replay uses only information with available_from <= as_of"
        ),
        "api_prefix": "/v1/temporal-integrity",
        "fabricated": False,
    }


def guard(
    *,
    as_of: str | None,
    evidence_graph: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    documents: list[dict[str, Any]] | None = None,
    stage: str = "full",
) -> dict[str, Any]:
    out = apply_replay_guard(
        as_of=as_of,
        evidence_graph=evidence_graph,
        institutional_memory=institutional_memory,
        evidence=evidence,
        documents=documents,
        stage=stage,
    )
    tirc_store.record_guard(out.get("report") or {}, out.get("rejected") or [])
    return out


def validate_object(obj: dict[str, Any], *, as_of: str | None) -> dict[str, Any]:
    return evaluate_object(obj, as_of=as_of, source="api")


def dashboard() -> dict[str, Any]:
    return build_board()


def rejected(*, limit: int = 50) -> dict[str, Any]:
    return {"n": limit, "rejected": tirc_store.latest_rejected(limit=limit)}


def certification(iel_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    if iel_summary is None:
        latest = tirc_store.latest_certification()
        if latest:
            return latest
        return certify_from_iel_summary({})
    return certify_from_iel_summary(iel_summary)


def telemetry() -> dict[str, Any]:
    return snapshot()


def report_markdown(iel_summary: dict[str, Any] | None = None) -> str:
    cert = certification(iel_summary)
    return build_markdown(cert, build_board())
