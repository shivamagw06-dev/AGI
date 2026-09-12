"""FSE-01 Financial Statements Engine — production façade."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.canonical import build_statement
from financial_statements_engine.derived import compute_derived, persist_derived
from financial_statements_engine.extraction.nse_xbrl import extract_from_earnings_pack, soft_build_pack
from financial_statements_engine.normalize import normalize_fields
from financial_statements_engine.observability import dashboard as obs_dashboard
from financial_statements_engine.observability import record_event
from financial_statements_engine.registry import registry_manifest
from financial_statements_engine.schema import (
    COVERAGE_BEFORE_DEPTH,
    ENGINE_CODE,
    ENGINE_NAME,
    GOLD_UNIVERSE,
    ISSUES_RECOMMENDATIONS,
    LAYERS,
    MILESTONE,
    MODIFIES_DECISION_ENGINE,
    PREDECESSOR_ENGINE,
    PROGRAMME,
    QUALITY_TARGETS,
    RECOMMENDATION_POLICY,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.util import now_iso
from financial_statements_engine.warehouse import get_published, publish_statement


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "role": "canonical_financial_warehouse",
        "layers": list(LAYERS),
        "predecessor_engine": PREDECESSOR_ENGINE,
        "gold_universe": list(GOLD_UNIVERSE),
        "coverage_before_depth": COVERAGE_BEFORE_DEPTH,
        "quality_targets": QUALITY_TARGETS,
        "registry": registry_manifest(),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "modifies_decision_engine": MODIFIES_DECISION_ENGINE,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_01_FINANCIAL_STATEMENTS_ENGINE.md",
    }


def dashboard() -> dict[str, Any]:
    body = obs_dashboard()
    body.update(
        {
            "status": "ok",
            "programme": PROGRAMME,
            "version": VERSION,
            "workstream_id": WORKSTREAM_ID,
            "issues_recommendations": False,
        }
    )
    return body


def get_statements(ticker: str) -> dict[str, Any]:
    t = ticker.upper().strip()
    published = get_published(t)
    return {
        "ok": published is not None,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "ticker": t,
        "published": published,
        "issues_recommendations": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "as_of": now_iso(),
    }


def ingest_and_publish(
    ticker: str,
    *,
    pack: dict[str, Any] | None = None,
    publish: bool = True,
    allow_flagged: bool = True,
    max_periods: int = 8,
) -> dict[str, Any]:
    """Run Extract → Normalize → Canonical → Validate → Version → Publish.

    M1+ path: uses P2.1 pack as extraction input when ``pack`` not supplied.
    """
    t = ticker.upper().strip()
    source_pack = pack if pack is not None else soft_build_pack(t)
    extracted = extract_from_earnings_pack(source_pack if isinstance(source_pack, dict) else {})
    periods = list(extracted.get("periods") or [])[: max(0, int(max_periods))]

    results: list[dict[str, Any]] = []
    for period in periods:
        fields = period.get("fields") or {}
        if not fields:
            continue
        norm = normalize_fields(fields)
        evidence_id = None
        refs = period.get("source_refs") or []
        if refs and isinstance(refs[0], dict):
            evidence_id = refs[0].get("evidence_id")
        # Synthetic evidence id for pack-derived rows lacking raw hash (migration)
        if not evidence_id:
            pe = period.get("period_end") or "unknown"
            evidence_id = f"pack:{t}:{pe}"

        # Attach evidence_id onto normalized metrics for TRACE_EVIDENCE
        metrics = {}
        for k, v in (norm.get("metrics") or {}).items():
            row = dict(v)
            row["evidence_id"] = evidence_id
            row["extractor"] = period.get("extractor") or "nse_indas_xbrl_v1"
            row["confidence"] = period.get("confidence")
            metrics[k] = row

        period_type = str(period.get("period_type") or "quarterly")
        period_end = str(period.get("period_end") or "")
        if not period_end:
            continue

        # Publish income / balance / cash as separate canonical docs when keys exist
        for statement_type, key_hint in (
            ("income_statement", "revenue"),
            ("balance_sheet", "total_assets"),
            ("cash_flow", "operating_cash_flow"),
        ):
            # Build even if hint missing — validator will withhold if core absent
            stmt = build_statement(
                ticker=t,
                statement_type=statement_type,
                period_type=period_type,
                period_end=period_end,
                metrics=metrics,
                evidence_id=evidence_id,
                fiscal_year=period.get("fiscal_year"),
                fiscal_period=period.get("fiscal_period"),
                extractor=period.get("extractor"),
            )
            if publish:
                pub = publish_statement(stmt, allow_flagged=allow_flagged)
                if pub.get("published") and statement_type == "income_statement":
                    derived = compute_derived(pub["statement"])
                    persist_derived(t, derived)
                results.append({"statement_type": statement_type, "period_end": period_end, **pub})
            else:
                results.append({"statement_type": statement_type, "period_end": period_end, "statement": stmt, "published": False})

    record_event(
        {
            "stage": "ingest_and_publish",
            "ticker": t,
            "periods": len(periods),
            "results": len(results),
            "ok": True,
        }
    )
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "ticker": t,
        "periods_seen": len(periods),
        "results": results,
        "published": get_published(t),
        "issues_recommendations": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "as_of": now_iso(),
    }


def coverage_report(universe: str = "gold") -> dict[str, Any]:
    tickers = list(GOLD_UNIVERSE) if universe in ("gold", "ic5") else list(GOLD_UNIVERSE)
    rows = []
    for t in tickers:
        pub = get_published(t)
        rows.append(
            {
                "ticker": t,
                "published": pub is not None,
                "statement_n": len((pub or {}).get("statements") or []),
            }
        )
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "universe": universe,
        "coverage_before_depth": COVERAGE_BEFORE_DEPTH,
        "n": len(rows),
        "published_n": sum(1 for r in rows if r["published"]),
        "rows": rows,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }
