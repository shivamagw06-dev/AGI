"""PNE pipeline — Raw Evidence → Parse Manifest → Coverage Matrix → Canonical drafts.

FSE-04.1: every successful parse emits an immutable Parse Manifest.
FSE-04.2: every successful parse emits an immutable Evidence Coverage Matrix.
Never publishes to Financial Warehouse (FSE-05).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from financial_statements_engine.cfdm.company import build_company
from financial_statements_engine.cfdm.fact import build_fact, facts_fingerprint
from financial_statements_engine.cfdm.period import build_period
from financial_statements_engine.cfdm.statement import build_statement
from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.metric_registry.schema import REGISTRY_VERSION
from financial_statements_engine.parsing.currency import normalize_currency
from financial_statements_engine.parsing.duplicates import detect_duplicates
from financial_statements_engine.parsing.identify import identify_document
from financial_statements_engine.parsing.normalize_stage import map_metrics
from financial_statements_engine.parsing.period import recognise_period
from financial_statements_engine.parsing.quality.confidence import compute_confidence, structural_confidence
from financial_statements_engine.parsing.quality.hierarchy import build_statement_tree, hierarchy_preserved
from financial_statements_engine.parsing.quality.lineage import build_lineage_root, fact_lineage
from financial_statements_engine.parsing.quality.manifest import (
    build_manifest,
    document_hash,
    new_draft_id,
    store_manifest,
)
from financial_statements_engine.parsing.coverage.assemble import assemble_coverage
from financial_statements_engine.parsing.quality.unknown_queue import enqueue_many
from financial_statements_engine.parsing.quarantine import quarantine_document
from financial_statements_engine.parsing.registry import select_parser
from financial_statements_engine.parsing.schema import VERSION, WRITES_WAREHOUSE
from financial_statements_engine.parsing.structure import detect_structure
from financial_statements_engine.parsing.units import normalize_unit_fields
from financial_statements_engine.schema_evolution.schema import VERSION as SCHEMA_EVOLUTION_VERSION
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def _fingerprint(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _emit(event_v1: str, legacy: str | None, payload: dict[str, Any]) -> None:
    publish(event_v1, payload)
    if legacy:
        publish(legacy, payload)


def parse_document(
    *,
    ticker: str,
    data: bytes,
    evidence_id: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run full PNE pipeline. Always produces Parse Manifest on success."""
    assert WRITES_WAREHOUSE is False
    meta = dict(meta or {})
    t = ticker.upper().strip()
    t0 = time.perf_counter()
    doc_hash = document_hash(data)
    draft_id = new_draft_id()
    replay_of = meta.get("replay_of")

    _emit("parse.started.v1", "parse.started", {"ticker": t, "evidence_id": evidence_id, "draft_id": draft_id})

    identity = identify_document(data, meta=meta)
    parser = select_parser(
        document_type=identity["document_type"],
        exchange=identity.get("exchange"),
        reporting_standard=identity.get("reporting_standard"),
    )
    if parser is None:
        q = quarantine_document(ticker=t, evidence_id=evidence_id, reason="unsupported_format", detail=identity)
        _emit(
            "parse.quarantined.v1",
            "parse.quarantined",
            {"ticker": t, "evidence_id": evidence_id, "reason": "unsupported_format"},
        )
        return {"ok": False, "quarantined": True, "quarantine": q, "writes_warehouse": False}

    extracted = parser.parse(data, meta={**meta, **identity})
    if extracted.get("quarantine") or (
        not extracted.get("ok") and "unsupported_format" in (extracted.get("errors") or [])
    ):
        q = quarantine_document(
            ticker=t,
            evidence_id=evidence_id,
            reason="unsupported_format",
            detail={"parser": extracted.get("parser_id"), "errors": extracted.get("errors")},
        )
        _emit(
            "parse.quarantined.v1",
            "parse.quarantined",
            {"ticker": t, "evidence_id": evidence_id, "reason": "unsupported_format"},
        )
        return {"ok": False, "quarantined": True, "quarantine": q, "extracted": extracted, "writes_warehouse": False}

    if not extracted.get("ok"):
        _emit(
            "parse.failed.v1",
            "parse.failed",
            {
                "ticker": t,
                "evidence_id": evidence_id,
                "errors": extracted.get("errors"),
                "detail": extracted.get("error_detail"),
            },
        )
        return {"ok": False, "extracted": extracted, "writes_warehouse": False}

    fields = extracted.get("fields") or {}
    structure = detect_structure(fields, extracted.get("sections"))
    units = normalize_unit_fields(fields)
    currency = normalize_currency(units["fields"], hint=meta.get("currency") or identity.get("currency"))
    period_info = recognise_period(meta)
    mapped = map_metrics(
        currency["fields"],
        as_of=meta.get("period_end") or meta.get("filing_date"),
        reporting_standard=identity.get("reporting_standard") or "IND_AS",
        extraction_confidence=float(extracted.get("extraction_confidence") or 0.0),
    )
    dupes = detect_duplicates(mapped["metrics"])
    hierarchy = build_statement_tree(
        fields,
        sections=structure.get("sections"),
        mapped_metrics=mapped.get("metrics"),
    )

    # Multi-stage confidence
    norm_vals = [
        float(v.get("normalization_confidence") or 0.0)
        for v in (mapped.get("metrics") or {}).values()
        if isinstance(v, dict)
    ]
    norm_conf = sum(norm_vals) / len(norm_vals) if norm_vals else 0.0
    # penalize unknowns
    unk_n = len(mapped.get("unknown_fields") or {})
    tot = unk_n + len(mapped.get("metrics") or {})
    if tot:
        norm_conf *= len(mapped.get("metrics") or {}) / tot
    struct_conf = structural_confidence(structure.get("sections"), hierarchy_preserved(hierarchy))
    confidence = compute_confidence(
        extraction=float(extracted.get("extraction_confidence") or 0.0),
        normalization=norm_conf,
        structural=struct_conf,
    )

    company = build_company(
        exchange=str(identity.get("exchange") or "NSE"),
        ticker=t,
        reporting_standard=str(identity.get("reporting_standard") or "IND_AS"),
    )
    lineage = build_lineage_root(
        evidence_id=evidence_id,
        document_hash=doc_hash,
        ticker=t,
        manifest_id="pending",
        draft_id=draft_id,
    )

    drafts: list[dict[str, Any]] = []
    fact_rows: list[dict[str, Any]] = []
    if period_info.get("period_end") and period_info.get("period_kind"):
        period = build_period(
            company_id=company["company_id"],
            period_end=str(period_info["period_end"]),
            period_kind=str(period_info["period_kind"]),
            consolidation_type=str(period_info.get("consolidation_type") or "unknown"),
            statement_scope=str(period_info.get("statement_scope") or "as_reported"),
            fiscal_year=period_info.get("fiscal_year"),
            quarter=period_info.get("quarter"),
        )
        by_stmt: dict[str, dict[str, Any]] = {}
        for metric, row in (mapped["metrics"] or {}).items():
            stmt_type = (row.get("metric_record") or {}).get("statement_type") or "income_statement"
            by_stmt.setdefault(stmt_type, {})[metric] = row

        for stmt_type, metrics in sorted(by_stmt.items()):
            facts = []
            for metric, row in sorted(metrics.items()):
                fact = build_fact(
                    company_id=company["company_id"],
                    period_id=period["period_id"],
                    statement_type=stmt_type,
                    metric=metric,
                    reported_value=row.get("reported_value"),
                    normalized_value=row.get("normalized_value"),
                    currency=currency["canonical_currency"],
                    unit=row.get("scale") or row.get("unit_scale"),
                    scale=str(row.get("scale") or row.get("unit_scale") or "crores"),
                    source=str(meta.get("source") or "nse_xbrl"),
                    evidence_id=evidence_id,
                    confidence=float(row.get("overall_confidence") or confidence["overall"]),
                    status="draft",
                    consolidation_type=str(period_info.get("consolidation_type") or "unknown"),
                    parser_version=str(extracted.get("parser_version")),
                    collector_version=str(meta.get("collector_version") or "fse-02"),
                )
                fact["trace"] = {
                    "source_field": row.get("source_field"),
                    "page": row.get("page"),
                    "table_id": row.get("table_id"),
                    "row_id": row.get("row_id"),
                    "column_id": row.get("column_id"),
                    "parser_id": extracted.get("parser_id"),
                    "parser_version": extracted.get("parser_version"),
                    "pne_version": VERSION,
                    "metric_registry_version": REGISTRY_VERSION,
                    "schema_evolution_version": SCHEMA_EVOLUTION_VERSION,
                }
                fact["lineage"] = fact_lineage(
                    lineage_root_id=lineage["lineage_root_id"],
                    section=stmt_type,
                    source_field=row.get("source_field"),
                    metric=metric,
                    evidence_id=evidence_id,
                    table_id=row.get("table_id"),
                    row_id=row.get("row_id"),
                    column_id=row.get("column_id"),
                )
                fact["lineage"]["path"][-1]["ref"] = draft_id
                facts.append(fact)
                fact_rows.append(fact)
            stmt = build_statement(
                period_id=period["period_id"],
                company_id=company["company_id"],
                statement_type=stmt_type,
                status="draft",
                fact_ids=[f["fact_id"] for f in facts],
                currency=currency["canonical_currency"],
            )
            drafts.append({"statement": stmt, "facts": facts})
    else:
        period = None

    # Fingerprint is document/parser deterministic — excludes evidence_id / wall-clock / draft ids
    deterministic_core = {
        "ticker": t,
        "document_type": identity["document_type"],
        "document_hash": doc_hash,
        "parser_id": extracted.get("parser_id"),
        "parser_version": extracted.get("parser_version"),
        "pne_version": VERSION,
        "metric_registry_version": REGISTRY_VERSION,
        "schema_evolution_version": SCHEMA_EVOLUTION_VERSION,
        "metrics": {
            k: {
                "reported_value": v.get("reported_value"),
                "normalized_value": v.get("normalized_value"),
                "scale": v.get("scale") or v.get("unit_scale"),
                "source_field": v.get("source_field"),
            }
            for k, v in sorted((mapped.get("metrics") or {}).items())
        },
        "unknown_fields": sorted((mapped.get("unknown_fields") or {}).keys()),
        "period": {
            "period_end": period_info.get("period_end"),
            "period_kind": period_info.get("period_kind"),
            "consolidation_type": period_info.get("consolidation_type"),
        },
        "currency": currency["canonical_currency"],
        "hierarchy_fingerprint": hierarchy.get("hierarchy_fingerprint"),
    }
    fp = _fingerprint(deterministic_core)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Scales summary
    scales = [
        str(v.get("scale") or v.get("unit_scale"))
        for v in (mapped.get("metrics") or {}).values()
        if isinstance(v, dict)
    ]
    unit_detected = max(set(scales), key=scales.count) if scales else None

    manifest = build_manifest(
        draft_id=draft_id,
        document_hash=doc_hash,
        company_id=company["company_id"],
        ticker=t,
        parser_name=str(extracted.get("parser_id")),
        parser_version=str(extracted.get("parser_version")),
        schema_version=SCHEMA_EVOLUTION_VERSION,
        metric_registry_version=REGISTRY_VERSION,
        pne_version=VERSION,
        processing_time_ms=elapsed_ms,
        document_type=identity["document_type"],
        source=meta.get("source"),
        reporting_period={
            "period_end": period_info.get("period_end"),
            "period_kind": period_info.get("period_kind"),
            "consolidation_type": period_info.get("consolidation_type"),
        },
        currency_detected=currency["canonical_currency"],
        unit_detected=unit_detected,
        sections_found=list(structure.get("sections") or []),
        metrics_extracted=sorted((mapped.get("metrics") or {}).keys()),
        metrics_unknown=sorted((mapped.get("unknown_fields") or {}).keys()),
        warnings=list(dupes.get("duplicate_flags") or []),
        errors=[],
        confidence=confidence,
        hierarchy_fingerprint=hierarchy.get("hierarchy_fingerprint"),
        deterministic_fingerprint=fp,
        lineage_root_id=lineage["lineage_root_id"],
        replay_of=replay_of,
    )
    # Fix lineage root with real manifest id
    lineage["nodes"][1]["ref"] = manifest["manifest_id"]
    manifest_path = store_manifest(manifest)

    # Unknown metric review queue
    unknown_labels = sorted((mapped.get("unknown_fields") or {}).keys())
    queued = enqueue_many(
        unknown_labels,
        ticker=t,
        evidence_id=evidence_id,
        manifest_id=manifest["manifest_id"],
        context={"document_type": identity["document_type"]},
    )

    # FSE-04.2 Evidence Coverage Matrix (observational — never edits data / never blocks)
    coverage = assemble_coverage(
        ticker=t,
        company_id=company["company_id"],
        evidence_id=evidence_id,
        draft_id=draft_id,
        manifest_id=manifest["manifest_id"],
        document_hash=doc_hash,
        document_type=identity["document_type"],
        parser_name=str(extracted.get("parser_id")),
        parser_version=str(extracted.get("parser_version")),
        pne_version=VERSION,
        metric_registry_version=REGISTRY_VERSION,
        processing_time_ms=elapsed_ms,
        sections_found=list(structure.get("sections") or []),
        metrics_extracted=mapped.get("metrics"),
        unknown_fields=mapped.get("unknown_fields"),
        confidence=confidence,
        period_info=period_info,
        industry=meta.get("industry"),
        queued_unknowns=queued,
    )

    result = {
        "ok": True,
        "ticker": t,
        "evidence_id": evidence_id,
        "draft_id": draft_id,
        "document_hash": doc_hash,
        "identity": identity,
        "parser_id": extracted.get("parser_id"),
        "parser_version": extracted.get("parser_version"),
        "structure": structure,
        "hierarchy": hierarchy,
        "hierarchy_fingerprint": hierarchy.get("hierarchy_fingerprint"),
        "confidence": confidence,
        "period": period_info,
        "currency": {
            "original_currency": currency["original_currency"],
            "canonical_currency": currency["canonical_currency"],
            "fx_applied": False,
        },
        "mapped": {
            "metrics": mapped["metrics"],
            "unknown_fields": mapped["unknown_fields"],
            "uses_parser_local_synonyms": False,
        },
        "duplicates": dupes,
        "company": company,
        "reporting_period": period,
        "drafts": drafts,
        "manifest": manifest,
        "manifest_id": manifest["manifest_id"],
        "manifest_path": str(manifest_path),
        "coverage_matrix": coverage["matrix"],
        "coverage_matrix_id": coverage["matrix_id"],
        "coverage_matrix_path": coverage["matrix_path"],
        "coverage_scorecard": coverage["scorecard"],
        "missing_metric_report": coverage["missing_metric_report"],
        "unknown_label_report": coverage["unknown_label_report"],
        "coverage_diff": coverage.get("coverage_diff"),
        "lineage": lineage,
        "unknown_metrics_queued": [q["queue_id"] for q in queued],
        "facts_fingerprint": facts_fingerprint(fact_rows) if fact_rows else None,
        "deterministic_fingerprint": fp,
        "writes_warehouse": False,
        "validates_accounting": False,
        "calculates_derived": False,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }

    # Persist draft by unique draft_id — never overwrite historical drafts
    draft_dir = ensure_dirs() / "parsing" / "drafts" / t
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / f"{draft_id.replace(':', '_')}.json"
    if draft_path.exists():
        raise FileExistsError(f"draft_immutable_violation: {draft_id}")
    write_json_atomic(draft_path, result)
    # latest pointer only
    write_json_atomic(
        draft_dir / "latest.json",
        {"draft_id": draft_id, "manifest_id": manifest["manifest_id"], "path": str(draft_path), "updated_at": now_iso()},
    )
    result["draft_path"] = str(draft_path)

    payload = {
        "ticker": t,
        "evidence_id": evidence_id,
        "manifest_id": manifest["manifest_id"],
        "draft_id": draft_id,
        "coverage_matrix_id": coverage["matrix_id"],
        "coverage_percentage": coverage["scorecard"].get("coverage_percentage"),
        "deterministic_fingerprint": fp,
        "metric_n": len(mapped.get("metrics") or {}),
        "unknown_n": len(mapped.get("unknown_fields") or {}),
        "draft_path": str(draft_path),
        "confidence": confidence,
    }
    _emit("parse.completed.v1", "parse.completed", payload)
    publish("draft.created.v1", {"draft_id": draft_id, "manifest_id": manifest["manifest_id"], "ticker": t})
    if replay_of:
        publish("draft.updated.v1", {"draft_id": draft_id, "replay_of": replay_of, "ticker": t})
    return result
