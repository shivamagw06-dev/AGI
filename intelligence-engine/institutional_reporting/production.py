"""IRE-02 production façades — health / compose / company report + reasons."""

from __future__ import annotations

from typing import Any, Optional

from institutional_reporting.composer import compose_report
from institutional_reporting.flags import flags_dict, is_enabled
from institutional_reporting.fixtures import FIXTURES, get_fixture
from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.schema import (
    IRE_PRODUCT,
    IRE_REPORT_TYPE,
    IRE_ROLE,
    IRE_SPEC,
    IRE_VERSION,
    IRE_WORKSTREAM_ID,
    REASON_COMPOSER_VERSION,
    REPORT_SECTIONS,
    VALIDATOR_VERSION,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IRE_WORKSTREAM_ID,
        "product": IRE_PRODUCT,
        "version": IRE_VERSION,
        "role": IRE_ROLE,
        "report_type": IRE_REPORT_TYPE,
        "reason_composer": True,
        "reason_composer_version": REASON_COMPOSER_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "llm": False,
        "external_writer": False,
        "gemini": False,
        "openai": False,
        "sections": list(REPORT_SECTIONS),
        "fixtures": sorted(FIXTURES.keys()),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": IRE_SPEC,
        "brand": "AGI",
        "as_of": now_iso(),
    }


def _serialize_report(report, *, include_reasons: bool = True) -> dict[str, Any]:
    out = report.to_dict()
    out["as_of"] = out.get("as_of") or now_iso()
    if not include_reasons:
        # Keep diagnostics; strip bulky reason payloads when not requested.
        out.pop("reasons", None)
        out.pop("reason_graph_text", None)
        for section in out.get("sections") or []:
            if isinstance(section, dict):
                section.pop("reason", None)
                meta = section.get("meta") or {}
                if isinstance(meta, dict):
                    meta.pop("reason", None)
    return out


def compose_company_report(
    payload: Optional[dict[str, Any]] = None,
    *,
    include_reasons: bool = True,
) -> dict[str, Any]:
    """POST /v1/report/company — compose from InstitutionalReportInput facts."""
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": IRE_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["IRE-02 disabled"],
        }
    body = dict(payload or {})
    include = body.pop("include_reasons", include_reasons)
    if isinstance(include, str):
        include = include.strip().lower() in {"1", "true", "yes", "on"}
    ticker = str(body.get("ticker") or "").strip()
    occupied = {k for k, v in body.items() if v not in (None, "", [], {})}
    ticker_only = occupied <= {"ticker", "as_of"} and bool(ticker)
    if ticker_only and get_fixture(ticker):
        report = compose_report(get_fixture(ticker))
    else:
        report = compose_report(InstitutionalReportInput.from_dict(body))
    return _serialize_report(report, include_reasons=bool(include))


def report_for_ticker(ticker: str, *, include_reasons: bool = True) -> dict[str, Any]:
    fixture = get_fixture(ticker)
    if not fixture:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": IRE_WORKSTREAM_ID,
            "validation_errors": [f"no deterministic fixture for ticker={ticker}"],
            "hint": "Pass a full InstitutionalReportInput body to POST /v1/report/company",
        }
    return _serialize_report(compose_report(fixture), include_reasons=include_reasons)


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    return {
        "status": h.get("status"),
        "workstream_id": IRE_WORKSTREAM_ID,
        "product": IRE_PRODUCT,
        "version": IRE_VERSION,
        "llm": False,
        "reason_composer": True,
        "report_type": IRE_REPORT_TYPE,
        "fixtures": sorted(FIXTURES.keys()),
    }
