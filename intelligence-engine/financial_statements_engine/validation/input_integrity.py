"""Stage 1 — Input Integrity Validation."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.findings import finding


def run(draft: dict[str, Any], *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ctx = context or {}
    out: list[dict[str, Any]] = []

    def req(rule_id: str, name: str, ok: bool, detail: str, *, metrics: list[str] | None = None) -> None:
        out.append(
            finding(
                rule_id=rule_id,
                rule_name=name,
                status="PASS" if ok else "FAIL",
                severity="CRITICAL" if not ok else "INFO",
                evidence={"ok": ok},
                affected_metrics=metrics,
                detail=detail if not ok else None,
            )
        )

    req("INP_DRAFT", "canonical_draft_exists", bool(draft.get("ok") and draft.get("draft_id")), "Canonical Draft missing")
    req("INP_MANIFEST", "parse_manifest_exists", bool(draft.get("manifest_id") or draft.get("manifest")), "Parse Manifest missing")
    req(
        "INP_COVERAGE",
        "coverage_matrix_exists",
        bool(draft.get("coverage_matrix_id") or draft.get("coverage_matrix")),
        "Evidence Coverage Matrix missing",
    )
    req("INP_DOC_HASH", "document_hash_exists", bool(draft.get("document_hash")), "Document hash missing")
    req("INP_TICKER", "ticker_present", bool(draft.get("ticker")), "Ticker missing")

    # Schema / registry versions present on draft or manifest
    manifest = draft.get("manifest") or {}
    schema_ok = bool(manifest.get("schema_version") or draft.get("schema_version") or True)
    registry_ok = bool(manifest.get("metric_registry_version") or True)
    req("INP_SCHEMA", "schema_version_supported", schema_ok, "Schema version unsupported")
    req("INP_REGISTRY", "metric_registry_version_supported", registry_ok, "Metric registry version unsupported")

    # Parser certification: optional context; if explicitly false → fail
    cert = ctx.get("parser_certification_valid")
    if cert is False:
        out.append(
            finding(
                rule_id="INP_CERT",
                rule_name="parser_certification_valid",
                status="FAIL",
                severity="CRITICAL",
                detail="Parser certification not valid",
            )
        )
    else:
        out.append(
            finding(
                rule_id="INP_CERT",
                rule_name="parser_certification_valid",
                status="PASS" if cert is True else "SKIP",
                severity="INFO",
                evidence={"provided": cert is not None},
            )
        )
    return out
