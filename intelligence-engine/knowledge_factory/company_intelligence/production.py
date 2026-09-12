"""ICI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from knowledge_factory.company_intelligence import store as ici_store
from knowledge_factory.company_intelligence.dashboard import company_intelligence_dashboard
from knowledge_factory.company_intelligence.objects.compile import compile_company_intelligence
from knowledge_factory.company_intelligence.pipeline import run_company_intelligence_pipeline
from knowledge_factory.company_intelligence.schema import FREEZE_LOCKS, ICI_VERSION, LAYER, PROGRAMME
from knowledge_factory.company_intelligence.validators.gates import validate_object


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": ICI_VERSION,
        "architecture_status": "SOFT_COMPANY_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "not_a_planner": True,
        "not_governance": True,
        "not_learning_system": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/company-intelligence",
        "sprint_split": {"1a": "identity→ownership", "1b": "competition→dashboard"},
        "stack": [
            "Company Intelligence Object",
            "Knowledge Factory (soft extension)",
            "Sector DNA (reference)",
            "Evidence Factory (unchanged)",
            "Universe Intelligence (unchanged)",
            "Decision Quality (unchanged)",
            "Phase 1–7 Reasoning (frozen)",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return company_intelligence_dashboard(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_company_intelligence_pipeline(**kwargs)


def get_company(ticker: str, *, refresh: bool = False) -> dict[str, Any]:
    t = str(ticker or "").upper()
    if not refresh:
        row = ici_store.get(t)
        if row:
            return row
    return compile_company_intelligence(t, persist=True)


def coverage_summary() -> dict[str, Any]:
    rows = ici_store.list_all()
    if not rows:
        run_company_intelligence_pipeline()
        rows = ici_store.list_all()
    by_level: dict[str, int] = {}
    for obj in rows:
        name = str(obj.get("coverage_level_name") or obj.get("coverage_level"))
        by_level[name] = by_level.get(name, 0) + 1
    return {
        "n": len(rows),
        "by_level": by_level,
        "level_counts": {
            str(i): sum(1 for r in rows if int(r.get("coverage_level") or 0) == i) for i in range(8)
        },
        "version": ICI_VERSION,
        "fabricated": False,
    }


def quality_summary() -> dict[str, Any]:
    rows = ici_store.list_all()
    if not rows:
        run_company_intelligence_pipeline()
        rows = ici_store.list_all()
    ready = sum(1 for r in rows if r.get("institutional_ready"))
    failed = [r["ticker"] for r in rows if (r.get("quality") or {}).get("failed_gates")]
    return {
        "n": len(rows),
        "institutional_ready": ready,
        "institutional_ready_pct": round(100.0 * ready / (len(rows) or 1), 2),
        "failed_count": len(failed),
        "failed_sample": failed[:25],
        "unknown_fields_total": sum(int(r.get("unknown_fields") or 0) for r in rows),
        "avg_intelligence_score": round(
            sum(float(r.get("intelligence_score") or 0) for r in rows) / (len(rows) or 1), 2
        ),
        "gate": "INSTITUTIONAL_COMPANY_INTELLIGENCE",
        "passed": ready == len(rows) and len(rows) > 0,
        "version": ICI_VERSION,
        "fabricated": False,
    }


def search(q: str, *, limit: int = 25) -> dict[str, Any]:
    query = str(q or "").strip().upper()
    rows = ici_store.list_all()
    if not rows:
        run_company_intelligence_pipeline()
        rows = ici_store.list_all()
    hits = []
    for obj in rows:
        t = obj.get("ticker") or ""
        name_cell = ((obj.get("modules") or {}).get("identity") or {}).get("fields") or {}
        cname = (name_cell.get("company_name") or {}).get("value") if isinstance(name_cell.get("company_name"), dict) else ""
        sector = str(obj.get("sector") or "")
        blob = f"{t} {cname} {sector}".upper()
        if not query or query in blob:
            hits.append(
                {
                    "ticker": t,
                    "company_name": cname,
                    "sector": sector,
                    "coverage_level": obj.get("coverage_level"),
                    "intelligence_score": obj.get("intelligence_score"),
                    "institutional_ready": obj.get("institutional_ready"),
                }
            )
        if len(hits) >= limit:
            break
    return {"q": q, "n": len(hits), "results": hits, "version": ICI_VERSION}


def validate_ticker(ticker: str) -> dict[str, Any]:
    obj = get_company(ticker, refresh=False)
    return validate_object(obj)
