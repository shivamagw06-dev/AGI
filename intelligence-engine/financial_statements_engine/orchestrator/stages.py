"""Stage adapters — invoke existing engine façades; contain no business logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from financial_statements_engine.orchestrator.schema import STAGES
from financial_statements_engine.store import ensure_dirs, paths_for

StageResult = dict[str, Any]
StageFn = Callable[[dict[str, Any]], StageResult]


class StageError(Exception):
    def __init__(self, code: str, detail: str, *, transient: bool = False):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.transient = transient


def _stage_bucket(wf: dict[str, Any]) -> dict[str, Any]:
    stages = wf.setdefault("stages", {})
    return stages


def stage_already_completed(wf: dict[str, Any], stage: str) -> bool:
    return str((_stage_bucket(wf).get(stage) or {}).get("status")) == "COMPLETED"


# --- idempotency probes (read-only; do not mutate engines) ---


def _parse_done(wf: dict[str, Any]) -> bool:
    ticker = str(wf.get("ticker") or "").upper()
    if not ticker:
        return False
    draft = ensure_dirs() / "parsing" / "drafts" / ticker / "latest.json"
    return draft.exists()


def _warehouse_done(wf: dict[str, Any]) -> bool:
    ticker = str(wf.get("ticker") or "").upper()
    if not ticker:
        return False
    try:
        from financial_statements_engine.financial_warehouse.production import get_latest

        return int(get_latest(ticker).get("n") or 0) > 0
    except Exception:
        pub = paths_for(ticker)["published"]
        return pub.is_dir() and any(pub.glob("*.json"))


def _dme_done(wf: dict[str, Any]) -> bool:
    ticker = str(wf.get("ticker") or "").upper()
    company_id = str(wf.get("company_id") or f"nse:{ticker}")
    try:
        from financial_statements_engine.derived_metrics.store.versions import list_company_metrics

        if list_company_metrics(company_id):
            return True
    except Exception:
        pass
    der = paths_for(ticker)["derived"]
    return der.is_dir() and any(der.glob("*.json"))


def _raw_done(wf: dict[str, Any]) -> bool:
    # Only skip via stage status / explicit ack — identity fields alone are not completion
    return bool((wf.get("artifacts") or {}).get("raw_acked"))


def _validate_done(wf: dict[str, Any]) -> bool:
    """External probe: approved validation report on disk (not in-memory artifacts)."""
    ticker = str(wf.get("ticker") or "").upper()
    if not ticker:
        return False
    reports = ensure_dirs() / "validation" / "reports" / ticker
    if reports.is_dir() and any(reports.glob("*.json")):
        return True
    pub = paths_for(ticker)["published"]
    return pub.is_dir() and any(pub.glob("*.json"))


IDEMPOTENCY_CHECKS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "RAW_EVIDENCE_STORED": _raw_done,
    "PARSE": _parse_done,
    "VALIDATE": _validate_done,
    "WAREHOUSE_PUBLISH": _warehouse_done,
    "DERIVED_METRICS": _dme_done,
}


def execute_raw_evidence_stored(wf: dict[str, Any]) -> StageResult:
    """Acknowledge raw evidence identity — no collection logic."""
    if not (wf.get("evidence_id") or wf.get("document_hash")):
        raise StageError("MISSING_EVIDENCE", "evidence_id_or_document_hash_required", transient=False)
    return {
        "ok": True,
        "stage": "RAW_EVIDENCE_STORED",
        "evidence_id": wf.get("evidence_id"),
        "document_hash": wf.get("document_hash"),
        "raw_acked": True,
    }


def execute_parse(wf: dict[str, Any]) -> StageResult:
    from financial_statements_engine.parsing.production import parse_bytes
    from financial_statements_engine.raw_evidence import read_raw_bytes

    ticker = str(wf.get("ticker") or "").upper()
    evidence_id = str(wf.get("evidence_id") or "")
    data = None
    if evidence_id:
        data = read_raw_bytes(ticker, evidence_id)
    if data is None and wf.get("inline_bytes_b64"):
        import base64

        data = base64.b64decode(str(wf["inline_bytes_b64"]))
    if data is None:
        raise StageError("MISSING_RAW", "raw_bytes_unavailable", transient=False)

    draft = parse_bytes(
        ticker,
        data,
        evidence_id=evidence_id or None,
        document_type=str(wf.get("document_type") or "xbrl"),
        period_end=wf.get("period"),
        period_type=wf.get("filing_type"),
        source=str(wf.get("source") or "orchestrator"),
    )
    if not isinstance(draft, dict):
        raise StageError("PARSE_FAILED", "parse_returned_non_dict", transient=False)
    if draft.get("quarantined") or draft.get("status") == "failed":
        raise StageError("PARSE_FAILED", str(draft.get("error") or "parse_quarantined"), transient=False)
    return {
        "ok": True,
        "stage": "PARSE",
        "draft_id": draft.get("draft_id"),
        "manifest_id": draft.get("manifest_id"),
        "draft": draft,
    }


def execute_validate(wf: dict[str, Any]) -> StageResult:
    from financial_statements_engine.validation.production import run_validation

    draft = (wf.get("artifacts") or {}).get("draft")
    if not isinstance(draft, dict):
        # load latest draft pointer
        ticker = str(wf.get("ticker") or "").upper()
        latest = ensure_dirs() / "parsing" / "drafts" / ticker / "latest.json"
        if latest.exists():
            meta = json.loads(latest.read_text(encoding="utf-8"))
            path = meta.get("path")
            if path and Path(path).exists():
                draft = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(draft, dict):
        raise StageError("MISSING_DRAFT", "canonical_draft_unavailable", transient=False)

    # publish=False — warehouse is a separate orchestrated stage
    result = run_validation(draft, publish=False)
    approval = (result.get("approval") or {}).get("approval_status")
    if approval not in ("APPROVED", "APPROVED_WITH_WARNINGS"):
        raise StageError(
            "VALIDATION_NOT_APPROVED",
            f"approval_status={approval}",
            transient=False,
        )
    return {
        "ok": True,
        "stage": "VALIDATE",
        "validation_id": result.get("validation_id"),
        "approval_status": approval,
        "validated_pack": result,
        "draft": draft,
    }


def execute_warehouse_publish(wf: dict[str, Any]) -> StageResult:
    from financial_statements_engine.financial_warehouse.production import publish as wh_publish
    from financial_statements_engine.validation.publish import build_validated_facts

    artifacts = wf.get("artifacts") or {}
    validated = artifacts.get("validated_pack")
    draft = artifacts.get("draft")
    if not isinstance(validated, dict):
        raise StageError("MISSING_VALIDATION", "validated_pack_unavailable", transient=False)

    report = validated.get("report") if isinstance(validated.get("report"), dict) else validated
    approval = validated.get("approval") or report.get("approval") or {}

    pack = validated if "facts" in validated else None
    if pack is None and isinstance(draft, dict):
        facts = build_validated_facts(draft, report)
        pack = {
            "approval_status": approval.get("approval_status"),
            "validation_status": approval.get("approval_status"),
            "validation_id": validated.get("validation_id") or report.get("validation_id"),
            "quality_score": validated.get("quality_score") or report.get("quality_score"),
            "ticker": wf.get("ticker"),
            "period_end": wf.get("period"),
            "company_id": wf.get("company_id"),
            "facts": facts,
        }
    if not isinstance(pack, dict):
        raise StageError("PACK_BUILD_FAILED", "unable_to_build_validated_pack", transient=False)

    result = wh_publish(validated_pack=pack, draft=draft if isinstance(draft, dict) else None)
    if not result.get("published"):
        raise StageError(
            "WAREHOUSE_REJECTED",
            str(result.get("reason") or "not_published"),
            transient=False,
        )
    return {"ok": True, "stage": "WAREHOUSE_PUBLISH", "publish_result": result}


def execute_derived_metrics(wf: dict[str, Any]) -> StageResult:
    from financial_statements_engine.derived_metrics.production import calculate

    ticker = str(wf.get("ticker") or "").upper()
    if not ticker:
        raise StageError("MISSING_TICKER", "ticker_required", transient=False)
    out = calculate(ticker, persist=True)
    calc = out.get("calculation") or {}
    if not calc.get("ok"):
        raise StageError("DME_FAILED", str(calc.get("error") or "calculation_failed"), transient=True)
    return {
        "ok": True,
        "stage": "DERIVED_METRICS",
        "metrics_calculated": calc.get("metrics_calculated"),
        "failures_n": calc.get("failures_n"),
        "result": out,
    }


DEFAULT_STAGE_FNS: dict[str, StageFn] = {
    "RAW_EVIDENCE_STORED": execute_raw_evidence_stored,
    "PARSE": execute_parse,
    "VALIDATE": execute_validate,
    "WAREHOUSE_PUBLISH": execute_warehouse_publish,
    "DERIVED_METRICS": execute_derived_metrics,
}


def next_stage(current: str | None) -> str | None:
    if current is None:
        return STAGES[0]
    try:
        i = STAGES.index(current)
    except ValueError:
        return None
    if i + 1 >= len(STAGES):
        return None
    return STAGES[i + 1]
