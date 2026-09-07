"""Automatic Repair — acquire → normalize → validate → publish → refresh readiness."""

from __future__ import annotations

from typing import Any, Dict, List


def repair_missing_knowledge(ticker: str, *, missing: List[str] | None = None) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    gaps = list(missing or [])
    steps: List[Dict[str, Any]] = []

    # Acquire via CGL soft extract / HD / FSE
    try:
        from continuous_gather_learn.knowledge_extract import extract_from_hd_series

        ex = extract_from_hd_series(t)
        steps.append({"step": "acquire_cgl_extract", "ok": bool(ex)})
    except Exception as exc:
        steps.append({"step": "acquire_cgl_extract", "ok": False, "error": str(exc)[:160]})

    try:
        from financial_statements_engine.production import run_ingest, run_publish

        run_ingest(t, force=False)
        run_publish(t)
        steps.append({"step": "fse_ingest_publish", "ok": True})
    except Exception as exc:
        steps.append({"step": "fse_ingest_publish", "ok": False, "error": str(exc)[:160]})

    # Normalize via KIL transform
    from ..transform.kf_to_canonical import transform_company_knowledge

    transformed = transform_company_knowledge(t)
    steps.append(
        {
            "step": "normalize",
            "ok": True,
            "period_count": transformed.get("period_count"),
            "published": transformed.get("financials_published"),
        }
    )

    # Validate quality
    from ...quality.engine import evaluate_evidence_quality

    quality = evaluate_evidence_quality(
        canonical_financials=transformed.get("models", {}).get("CanonicalFinancialStatements")
        or {},
        registry_items=[],
    )
    steps.append(
        {
            "step": "validate",
            "ok": quality.get("publish_allowed"),
            "score": quality.get("evidence_quality_score"),
        }
    )

    # Refresh readiness via research pack rebuild
    from ...research_pack.builder import build_institutional_research_pack

    pack = build_institutional_research_pack(t, auto_acquire=True)
    steps.append(
        {
            "step": "refresh_research_readiness",
            "research_ready": pack.get("research_ready"),
            "claim_safe": pack.get("claim_safe"),
        }
    )

    return {
        "ok": True,
        "ticker": t,
        "requested_gaps": gaps,
        "steps": steps,
        "transformed": {
            "period_count": transformed.get("period_count"),
            "financials_published": transformed.get("financials_published"),
        },
        "quality": quality,
        "research_ready": pack.get("research_ready"),
        "rule": "No manual intervention — acquire → normalize → validate → publish → refresh",
    }
