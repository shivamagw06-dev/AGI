"""VFQE pipeline — Canonical Draft → Validation Report → Quality Score → Approval → Warehouse."""

from __future__ import annotations

import copy
import time
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.validation import accounting as accounting_stage
from financial_statements_engine.validation import cross_statement as cross_stage
from financial_statements_engine.validation import sector_rules as sector_stage
from financial_statements_engine.validation import statistical as statistical_stage
from financial_statements_engine.validation import structural as structural_stage
from financial_statements_engine.validation import temporal as temporal_stage
from financial_statements_engine.validation.approval.decision import decide
from financial_statements_engine.validation.input_integrity import run as input_integrity_run
from financial_statements_engine.validation.publish import publish_validated_facts, quarantine_draft
from financial_statements_engine.validation.reporting.report import build_report
from financial_statements_engine.validation.scoring.score import compute_quality_score
from financial_statements_engine.validation.store import store_report
from financial_statements_engine.util import now_iso


def validate_draft(
    draft: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
    publish_on_approve: bool = True,
) -> dict[str, Any]:
    """Run full VFQE. Never mutates the input draft. Never reparses documents."""
    t0 = time.perf_counter()
    ctx = dict(context or {})
    # Work on a shallow structural copy reference for reading only — never write back
    draft_view = draft  # read-only by convention; deep-copy fingerprint for mutation check
    before = copy.deepcopy(draft)

    publish(
        "validation.started.v1",
        {"draft_id": draft.get("draft_id"), "ticker": draft.get("ticker")},
    )

    findings: list[dict[str, Any]] = []
    findings.extend(input_integrity_run(draft_view, context=ctx))
    findings.extend(structural_stage.run(draft_view, context=ctx))
    findings.extend(accounting_stage.run(draft_view, context=ctx))
    findings.extend(cross_stage.run(draft_view, context=ctx))
    findings.extend(temporal_stage.run(draft_view, context=ctx))
    findings.extend(statistical_stage.run(draft_view, context=ctx))
    findings.extend(sector_stage.run(draft_view, context=ctx))

    # Provisional block for scoring
    provisional = decide(findings)
    blocked = not provisional["publishable"]
    quality = compute_quality_score(
        findings,
        coverage_scorecard=draft_view.get("coverage_scorecard"),
        confidence=draft_view.get("confidence"),
        blocked=blocked,
    )
    approval = decide(findings, quality=quality)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    report = build_report(
        draft=draft_view,
        findings=findings,
        quality=quality,
        approval=approval,
        processing_time_ms=elapsed_ms,
    )
    report_path = store_report(report)

    publish_result = None
    quarantine_result = None
    if approval["publishable"] and publish_on_approve:
        publish_result = publish_validated_facts(draft_view, report)
        publish(
            "validation.approved.v1",
            {
                "validation_id": report["validation_id"],
                "draft_id": draft.get("draft_id"),
                "approval_status": approval["approval_status"],
                "published": bool(publish_result.get("published")),
            },
        )
    elif approval["approval_status"] == "QUARANTINED":
        quarantine_result = quarantine_draft(draft_view, report)
        publish(
            "validation.quarantined.v1",
            {"validation_id": report["validation_id"], "draft_id": draft.get("draft_id")},
        )
    else:
        publish(
            "validation.rejected.v1",
            {
                "validation_id": report["validation_id"],
                "draft_id": draft.get("draft_id"),
                "approval_status": approval["approval_status"],
            },
        )

    publish(
        "validation.completed.v1",
        {
            "validation_id": report["validation_id"],
            "draft_id": draft.get("draft_id"),
            "approval_status": approval["approval_status"],
            "grade": quality.get("grade"),
            "score": quality.get("score"),
        },
    )

    # Mutation guard — draft must be unchanged
    draft_mutated = draft != before

    return {
        "ok": True,
        "validation_id": report["validation_id"],
        "report": report,
        "report_path": str(report_path),
        "quality_score": quality,
        "approval": approval,
        "publish_result": publish_result,
        "quarantine_result": quarantine_result,
        "draft_mutated": draft_mutated,
        "reparses_documents": False,
        "writes_warehouse": bool((publish_result or {}).get("published")),
        "as_of": now_iso(),
        "issues_recommendations": False,
    }


def validate_draft_path(path: str, **kwargs: Any) -> dict[str, Any]:
    import json
    from pathlib import Path

    draft = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_draft(draft, **kwargs)
