"""Unified Institutional Knowledge Stack facade — soft orchestration only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.institutional_knowledge_stack.schema import (
    ARCHITECTURE_STATUS,
    FREEZE_LOCKS,
    LAYER,
    PROGRAMME,
    STACK_LAYERS,
    STACK_VERSION,
)


def health() -> dict[str, Any]:
    layers = []
    for meta in STACK_LAYERS:
        layers.append({**meta, "status": _layer_status(meta["id"])})
    ready = sum(1 for L in layers if L.get("status") == "ok")
    return {
        "status": "ok" if ready >= 6 else "degraded",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": STACK_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "soft_wire_only": True,
        "not_a_reasoning_engine": True,
        "freeze_locks": FREEZE_LOCKS,
        "layers": layers,
        "layers_ready": ready,
        "layers_total": len(STACK_LAYERS),
        "principle": "Reality + Expectations — markets price expectations, not reality.",
        "api_prefix": "/v1/institutional-knowledge",
    }


def dashboard(*, ensure: bool = False) -> dict[str, Any]:
    if ensure:
        run_stack(ensure_only_missing=True)

    board: dict[str, Any] = {
        "north_star": "institutional_knowledge_stack_coverage",
        "version": STACK_VERSION,
        "programme": PROGRAMME,
        "reality": {},
        "expectations": {},
        "roadmap_next": None,
        "fabricated": False,
        "reasoning_changed": False,
    }

    # Universe
    try:
        from universe_intelligence.dashboard import universe_health

        u = universe_health(universe_id="NIFTY_500", ensure=False)
        cov = u.get("coverage") or u
        board["reality"]["universe"] = {
            "avg_ici": cov.get("avg_ici"),
            "institutional_coverage_pct": cov.get("institutional_coverage_pct"),
            "status": "ok",
        }
    except Exception as exc:
        board["reality"]["universe"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Company
    try:
        from knowledge_factory.company_intelligence.dashboard import company_intelligence_dashboard

        c = company_intelligence_dashboard(ensure=False)
        board["reality"]["company"] = {
            "coverage_pct": c.get("coverage_pct") or c.get("institutional_ready_pct"),
            "north_star": c.get("north_star"),
            "status": "ok",
        }
    except Exception as exc:
        board["reality"]["company"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Corporate events
    try:
        from knowledge_factory.corporate_events.dashboard import corporate_events_dashboard

        e = corporate_events_dashboard(ensure=False)
        board["reality"]["corporate_events"] = {
            "event_count": e.get("event_count") or e.get("events"),
            "status": "ok",
        }
    except Exception as exc:
        board["reality"]["corporate_events"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Government
    try:
        from knowledge_factory.government_intelligence.dashboard import government_dashboard

        g = government_dashboard(ensure=False)
        board["reality"]["government"] = {
            "coverage_pct": g.get("coverage_pct"),
            "policy_count": g.get("policy_count"),
            "status": "ok",
        }
    except Exception as exc:
        board["reality"]["government"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Industry
    try:
        from knowledge_factory.industry_intelligence.dashboards import industry_dashboard

        i = industry_dashboard(ensure=False)
        board["reality"]["industry"] = {
            "institutional_ready_pct": i.get("institutional_ready_pct"),
            "companies_mapped": i.get("companies_mapped"),
            "status": "ok",
        }
    except Exception as exc:
        board["reality"]["industry"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Relationships
    try:
        from knowledge_factory.economic_relationship_intelligence.dashboards import (
            relationship_dashboard,
        )

        r = relationship_dashboard(ensure=False)
        cov = r.get("economic_relationship_coverage") or {}
        board["reality"]["relationships"] = {
            "relationships": cov.get("relationships"),
            "commodities": cov.get("commodities"),
            "institutional_ready_pct": cov.get("institutional_ready_pct"),
            "status": "ok",
        }
    except Exception as exc:
        board["reality"]["relationships"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Alternative data
    try:
        from knowledge_factory.alternative_data_intelligence.dashboards import (
            alternative_data_dashboard,
        )

        a = alternative_data_dashboard(ensure=False)
        acov = a.get("alternative_data_coverage") or {}
        board["reality"]["alternative_data"] = {
            "datasets": acov.get("datasets"),
            "observations": acov.get("observations"),
            "economic_momentum": a.get("economic_momentum"),
            "institutional_ready_pct": acov.get("institutional_ready_pct"),
            "status": "ok",
        }
    except Exception as exc:
        board["reality"]["alternative_data"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Expectations
    try:
        from knowledge_factory.market_expectations_intelligence.dashboards import (
            expectations_dashboard,
        )

        x = expectations_dashboard(ensure=False)
        ecov = x.get("expectation_dashboard") or {}
        board["expectations"]["market"] = {
            "expectations": ecov.get("expectations"),
            "revisions": ecov.get("revisions"),
            "surprises": ecov.get("surprises"),
            "narratives": ecov.get("narratives"),
            "institutional_ready_pct": ecov.get("institutional_ready_pct"),
            "principle": x.get("principle"),
            "status": "ok",
        }
    except Exception as exc:
        board["expectations"]["market"] = {"status": "unavailable", "error": str(exc)[:120]}

    # Soft-read daily health roadmap
    try:
        from knowledge_factory.coverage import daily_health_scorecard

        dh = daily_health_scorecard()
        board["roadmap_next"] = dh.get("roadmap_next")
        board["daily_health_roadmap"] = dh.get("roadmap_next")
    except Exception:
        board["roadmap_next"] = "knowledge_stack_complete"

    reality_ok = sum(1 for v in board["reality"].values() if v.get("status") == "ok")
    exp_ok = sum(1 for v in board["expectations"].values() if v.get("status") == "ok")
    board["summary"] = {
        "reality_layers_ok": reality_ok,
        "expectation_layers_ok": exp_ok,
        "stack_complete": reality_ok >= 6 and exp_ok >= 1,
    }
    return board


def run_stack(*, ensure_only_missing: bool = False) -> dict[str, Any]:
    """Run all soft KF knowledge pipelines in stack order. Soft-wire only."""
    t0 = time.perf_counter()
    results: dict[str, Any] = {}

    steps = [
        ("universe", _run_universe),
        ("company", _run_company),
        ("corporate_events", _run_corporate_events),
        ("government", _run_government),
        ("industry", _run_industry),
        ("relationships", _run_relationships),
        ("alternative_data", _run_alternative_data),
        ("expectations", _run_expectations),
    ]
    for name, fn in steps:
        if ensure_only_missing and _layer_status(name) == "ok":
            results[name] = {"status": "skipped_already_ready"}
            continue
        try:
            results[name] = {"status": "ok", "report": fn()}
        except Exception as exc:
            results[name] = {"status": "error", "error": str(exc)[:200]}

    ok = sum(1 for v in results.values() if v.get("status") in ("ok", "skipped_already_ready"))
    return {
        "version": STACK_VERSION,
        "programme": PROGRAMME,
        "results": results,
        "layers_ok": ok,
        "layers_total": len(steps),
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "status": "ok" if ok >= 6 else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "soft_wire_only": True,
    }


def company_bundle(ticker: str) -> dict[str, Any]:
    """Soft-assemble reality + expectations for one company — knowledge only."""
    t = str(ticker or "").upper()
    bundle: dict[str, Any] = {
        "ticker": t,
        "version": STACK_VERSION,
        "fabricated": False,
        "reasoning": False,
        "layers": {},
    }

    try:
        from knowledge_factory.company_intelligence import store as ici_store
        from knowledge_factory.company_intelligence.pipeline import run_company_intelligence_pipeline

        if not ici_store.get(t):
            try:
                run_company_intelligence_pipeline(tickers=[t])
            except TypeError:
                run_company_intelligence_pipeline()
        bundle["layers"]["company"] = ici_store.get(t)
    except Exception as exc:
        bundle["layers"]["company"] = {"error": str(exc)[:120]}

    try:
        from knowledge_factory.corporate_events import store as icei_store

        bundle["layers"]["corporate_events"] = icei_store.get_timeline(t)
    except Exception as exc:
        bundle["layers"]["corporate_events"] = {"error": str(exc)[:120]}

    try:
        from knowledge_factory.industry_intelligence.production import company_industry

        bundle["layers"]["industry"] = company_industry(t)
    except Exception as exc:
        bundle["layers"]["industry"] = {"error": str(exc)[:120]}

    try:
        from knowledge_factory.economic_relationship_intelligence.production import company as rel_co

        bundle["layers"]["relationships"] = rel_co(t)
    except Exception as exc:
        bundle["layers"]["relationships"] = {"error": str(exc)[:120]}

    try:
        from knowledge_factory.alternative_data_intelligence.production import company as alt_co

        bundle["layers"]["alternative_data"] = alt_co(t)
    except Exception as exc:
        bundle["layers"]["alternative_data"] = {"error": str(exc)[:120]}

    try:
        from knowledge_factory.market_expectations_intelligence.production import company as exp_co
        from knowledge_factory.market_expectations_intelligence.production import gap

        bundle["layers"]["expectations"] = exp_co(t)
        bundle["layers"]["expectation_gap"] = gap(t)
    except Exception as exc:
        bundle["layers"]["expectations"] = {"error": str(exc)[:120]}

    try:
        from knowledge_factory.production import evidence_feed

        bundle["evidence_feed"] = evidence_feed(t)
    except Exception:
        bundle["evidence_feed"] = None

    return bundle


def _layer_status(layer_id: str) -> str:
    try:
        if layer_id == "universe":
            from universe_intelligence import store as u_store

            return "ok" if u_store.list_universes() else "empty"
        if layer_id == "company":
            from knowledge_factory.company_intelligence import store as s

            return "ok" if s.count() > 0 else "empty"
        if layer_id == "corporate_events":
            from knowledge_factory.corporate_events import store as s

            return "ok" if s.event_count() > 0 else "empty"
        if layer_id == "government":
            from knowledge_factory.government_intelligence import store as s

            return "ok" if s.policy_count() > 0 else "empty"
        if layer_id == "industry":
            from knowledge_factory.industry_intelligence import store as s

            return "ok" if s.industry_count() > 0 else "empty"
        if layer_id == "relationships":
            from knowledge_factory.economic_relationship_intelligence import store as s

            return "ok" if s.relationship_count() > 0 else "empty"
        if layer_id == "alternative_data":
            from knowledge_factory.alternative_data_intelligence import store as s

            return "ok" if s.dataset_count() > 0 else "empty"
        if layer_id == "expectations":
            from knowledge_factory.market_expectations_intelligence import store as s

            return "ok" if s.expectation_count() > 0 else "empty"
    except Exception:
        return "unavailable"
    return "unknown"


def _run_universe() -> dict[str, Any]:
    from universe_intelligence.pipeline import run_universe_intelligence_pipeline

    try:
        return run_universe_intelligence_pipeline(universe_id="NIFTY_500")
    except TypeError:
        return run_universe_intelligence_pipeline()


def _run_company() -> dict[str, Any]:
    from knowledge_factory.company_intelligence.pipeline import run_company_intelligence_pipeline

    return run_company_intelligence_pipeline()


def _run_corporate_events() -> dict[str, Any]:
    from knowledge_factory.corporate_events.pipeline import run_corporate_events_pipeline

    return run_corporate_events_pipeline()


def _run_government() -> dict[str, Any]:
    from knowledge_factory.government_intelligence.pipeline import run_government_intelligence_pipeline

    return run_government_intelligence_pipeline()


def _run_industry() -> dict[str, Any]:
    from knowledge_factory.industry_intelligence.pipeline import run_industry_intelligence_pipeline

    return run_industry_intelligence_pipeline()


def _run_relationships() -> dict[str, Any]:
    from knowledge_factory.economic_relationship_intelligence.pipeline import (
        run_economic_relationship_pipeline,
    )

    return run_economic_relationship_pipeline()


def _run_alternative_data() -> dict[str, Any]:
    from knowledge_factory.alternative_data_intelligence.pipeline import (
        run_alternative_data_pipeline,
    )

    return run_alternative_data_pipeline()


def _run_expectations() -> dict[str, Any]:
    from knowledge_factory.market_expectations_intelligence.pipeline import (
        run_market_expectations_pipeline,
    )

    return run_market_expectations_pipeline()
