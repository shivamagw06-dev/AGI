"""Soft-read existing knowledge surfaces — never invent metrics."""

from __future__ import annotations

from typing import Any

from research_office import store


def _soft(fn, *args, **kwargs) -> dict[str, Any]:
    try:
        out = fn(*args, **kwargs)
        if out is None:
            return {"unavailable": True, "as_of": store.utc_now(), "fabricated": False}
        if isinstance(out, dict):
            return {**out, "fabricated": False}
        return {"payload": out, "fabricated": False}
    except Exception as exc:
        return {
            "unavailable": True,
            "error": str(exc)[:200],
            "as_of": store.utc_now(),
            "fabricated": False,
            "insufficient": True,
        }


def knowledge_versions() -> dict[str, str]:
    kv = "kf-track1"
    ev = "evidence-v1"
    try:
        from knowledge_factory.institutional_knowledge_stack.schema import STACK_VERSION

        kv = STACK_VERSION
    except Exception:
        pass
    try:
        from knowledge_factory.schedulers.daily import PIPELINE_VERSION

        ev = PIPELINE_VERSION
    except Exception:
        pass
    return {"knowledge_version": kv, "evidence_version": ev}


def read_iks_dashboard() -> dict[str, Any]:
    from knowledge_factory.institutional_knowledge_stack.production import dashboard

    return _soft(dashboard, ensure=False)


def read_government() -> dict[str, Any]:
    from knowledge_factory.government_intelligence.production import dashboard

    return _soft(dashboard)


def read_industry() -> dict[str, Any]:
    from knowledge_factory.industry_intelligence.production import dashboard

    return _soft(dashboard)


def read_corporate_events() -> dict[str, Any]:
    from knowledge_factory.corporate_events.production import dashboard

    return _soft(dashboard)


def read_alternative_data() -> dict[str, Any]:
    from knowledge_factory.alternative_data_intelligence.production import dashboard

    return _soft(dashboard)


def read_expectations() -> dict[str, Any]:
    from knowledge_factory.market_expectations_intelligence.production import dashboard

    return _soft(dashboard)


def read_company_intelligence() -> dict[str, Any]:
    from knowledge_factory.company_intelligence.production import dashboard

    return _soft(dashboard)


def read_coverage() -> dict[str, Any]:
    from knowledge_factory.coverage import morning_coverage_dashboard

    return _soft(morning_coverage_dashboard)


def read_macro() -> dict[str, Any]:
    try:
        from knowledge_factory.store import repository as kf_store

        return _soft(kf_store.get_object, "macro", "GLOBAL") or {
            "unavailable": True,
            "fabricated": False,
        }
    except Exception as exc:
        return {"unavailable": True, "error": str(exc)[:160], "fabricated": False}


def read_scheduler_context() -> dict[str, Any]:
    try:
        from institutional_scheduler.production import status, reports

        return {
            "status": status(),
            "reports": reports(),
            "fabricated": False,
        }
    except Exception as exc:
        return {"unavailable": True, "error": str(exc)[:160], "fabricated": False}


def read_company_bundle(ticker: str) -> dict[str, Any]:
    from knowledge_factory.institutional_knowledge_stack.production import company_bundle

    return _soft(company_bundle, ticker)


def read_evidence_feed(ticker: str) -> dict[str, Any]:
    from knowledge_factory.production import evidence_feed

    feed = _soft(evidence_feed, ticker)
    return feed if isinstance(feed, dict) else {"unavailable": True, "fabricated": False}


def read_best_evidence(
    ticker: str | None = None,
    *,
    question: str | None = None,
) -> dict[str, Any]:
    """Soft-wire IERE — ranked institutional evidence before publication generation."""
    try:
        from evidence_retrieval.production import company as iere_company
        from evidence_retrieval.production import search as iere_search

        if question:
            out = iere_search(question, ticker=ticker)
        elif ticker:
            out = iere_company(ticker)
        else:
            out = iere_search("What institutional evidence is available for the market morning brief?")
        return {
            "retrieval_id": out.get("retrieval_id"),
            "ranked_count": out.get("ranked_count"),
            "pack_ids": out.get("pack_ids") or [],
            "top_evidence": (out.get("ranked") or [])[:10],
            "citations": [
                r.get("citation") for r in (out.get("ranked") or [])[:10] if r.get("citation")
            ],
            "ask_envelope": out.get("ask_envelope"),
            "quality_gates": out.get("quality_gates"),
            "source": "evidence_retrieval",
            "fabricated": False,
            "reasoning_changed": False,
        }
    except Exception as exc:
        return {
            "unavailable": True,
            "error": str(exc)[:160],
            "as_of": store.utc_now(),
            "fabricated": False,
            "insufficient": True,
        }


def source_ref(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "source": "knowledge_factory",
        "collector": name,
        "provenance": True,
        "unavailable": bool(payload.get("unavailable")),
        "retrieved_at": store.utc_now(),
        "fabricated": False,
    }
