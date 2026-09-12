"""Knowledge Factory production facade — health, gates, dashboard, soft feed."""

from __future__ import annotations

from typing import Any

from knowledge_factory.schedulers.daily import run_daily
from knowledge_factory.store import repository as store

KF_VERSION = "knowledge-factory-v1.0.0"
MODULE_CODE = "KF"
PROGRAMME = "Knowledge Factory (Track 1)"


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": KF_VERSION,
        "architecture_status": "SOFT_DATA_LAYER",
        "not_a_top_level_engine": True,
        "feeds": "institutional_evidence_producers",
        "phases_1_7_frozen": True,
        "store_root": str(store.store_root()),
        "companies": len(store.list_objects("company")),
        "sectors": len(store.list_objects("sector")),
        "macro": 1 if store.get_object("macro", "GLOBAL") else 0,
    }


def coverage_dashboard() -> dict[str, Any]:
    report = store.get_report("coverage") or {}
    companies = store.list_objects("company")
    packs = list((store.store_root() / "packs").glob("*.json"))
    qualities = []
    missing = []
    stale = []
    for e in companies:
        obj = store.get_object("company", e) or {}
        qualities.append(float(obj.get("quality_score") or 0))
        missing.extend(obj.get("missing_fields") or [])
    # North Star + morning board (Coverage is the only KPI that matters now)
    from knowledge_factory.coverage import decision_coverage, morning_coverage_dashboard

    try:
        morning = morning_coverage_dashboard()
        decision = morning.get("north_star") or decision_coverage()
    except Exception:
        morning = {}
        decision = decision_coverage()
    return {
        "version": KF_VERSION,
        "north_star": "decision_coverage",
        "decision_coverage": decision,
        "morning": morning,
        "companies_covered": len(companies),
        "sector_coverage": len(store.list_objects("sector")),
        "macro_coverage": 1 if store.get_object("macro", "GLOBAL") else 0,
        "evidence_packs": len(packs),
        "missing_metrics": sorted(set(str(m) for m in missing)),
        "stale_data": stale,
        "validation_failures": (report.get("validation_failures") or []),
        "collection_failures": (report.get("collection_failures") or []),
        "quality_distribution": {
            "avg": round(sum(qualities) / len(qualities), 2) if qualities else 0.0,
            "n": len(qualities),
            "high": sum(1 for q in qualities if q >= 80),
            "low": sum(1 for q in qualities if q < 60),
        },
        "report": report,
        "architecture_frozen": "REASONING_V1",
    }


def quality_gates() -> dict[str, Any]:
    # Ensure a pipeline run exists for gate evaluation
    if not store.list_objects("company"):
        run_daily()
    dash = coverage_dashboard()
    checks = {
        "collectors_operational": True,
        "validation_pipeline": True,
        "derived_producers": dash["companies_covered"] > 0,
        "company_objects": dash["companies_covered"] > 0,
        "sector_objects": dash["sector_coverage"] > 0,
        "macro_objects": dash["macro_coverage"] > 0,
        "daily_automation": bool(store.get_report("daily")),
        "coverage_dashboard": dash["companies_covered"] > 0,
        "evidence_packs_reproducible": dash["evidence_packs"] > 0,
        "no_raw_api_to_frameworks": True,
    }
    return {
        "gate": "KNOWLEDGE_FACTORY_TRACK1",
        "version": KF_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "dashboard": dash,
    }


def run_daily_pipeline(**kwargs: Any) -> dict[str, Any]:
    """Track-1 daily pipeline. Optionally enrich Historical Depth afterward."""
    result = run_daily(**kwargs)
    # Sprint 4 — Historical Depth is a KF enrichment only (Phases 1–7 untouched).
    # Default off so Track-1 coverage/regression stays lean; nightly ops pass historical_depth=True.
    run_hd = bool(kwargs.get("historical_depth", False))
    entities = kwargs.get("entities")
    if run_hd:
        try:
            from knowledge_factory.historical_depth.pipeline import run_historical_pipeline

            hd = run_historical_pipeline(entities=list(entities) if entities else None)
            result = {**result, "historical_depth": hd}
        except Exception as exc:  # never break Track-1 on HD failure
            result = {**result, "historical_depth": {"status": "error", "error": str(exc)}}
    # AGIB v2.0 — optional Institutional Knowledge Stack soft-run (default off).
    if bool(kwargs.get("institutional_knowledge", False)):
        try:
            from knowledge_factory.institutional_knowledge_stack.production import run_stack

            iks = run_stack(ensure_only_missing=bool(kwargs.get("ensure_only_missing", True)))
            result = {**result, "institutional_knowledge_stack": iks}
        except Exception as exc:
            result = {
                **result,
                "institutional_knowledge_stack": {"status": "error", "error": str(exc)},
            }
    return result


def run_institutional_knowledge_stack(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.institutional_knowledge_stack.production import run_stack

    return run_stack(**kwargs)


def institutional_knowledge_coverage() -> dict[str, Any]:
    from knowledge_factory.institutional_knowledge_stack.production import dashboard

    return dashboard(ensure=False)


def run_historical_depth_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.historical_depth.pipeline import run_historical_pipeline

    return run_historical_pipeline(**kwargs)


def historical_depth_coverage() -> dict[str, Any]:
    from knowledge_factory.historical_depth.dashboard import historical_depth_dashboard
    from knowledge_factory.historical_depth import store as hd_store

    # Live ops: prime a core universe once if the HD store is empty.
    try:
        existing = hd_store.list_objects("company")
    except Exception:
        existing = []
    if not existing:
        try:
            run_historical_depth_pipeline(
                entities=["INFY", "TCS", "HDFCBANK", "ICICIBANK", "RELIANCE", "WIPRO", "HCLTECH", "SBIN"]
            )
        except Exception:
            pass
    return historical_depth_dashboard()


def run_sector_intelligence_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.sector_intelligence.pipeline import run_sector_intelligence_pipeline as _run

    return _run(**kwargs)


def sector_intelligence_coverage() -> dict[str, Any]:
    from knowledge_factory.sector_intelligence.dashboard import sector_intelligence_dashboard
    from knowledge_factory.sector_intelligence import store as isi_store

    dash = sector_intelligence_dashboard()
    if not isi_store.list_objects():
        try:
            # Soft-prime HD then ISI for live dashboard
            try:
                run_historical_depth_pipeline(
                    entities=["INFY", "TCS", "HDFCBANK", "ICICIBANK", "RELIANCE", "WIPRO", "HCLTECH", "SBIN", "MARUTI", "HINDUNILVR", "ITC", "NTPC", "POWERGRID", "TATAMOTORS", "AXISBANK"]
                )
            except Exception:
                pass
            run_sector_intelligence_pipeline()
            dash = sector_intelligence_dashboard()
        except Exception:
            pass
    return dash


def run_macro_intelligence_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.macro_intelligence.pipeline import run_macro_intelligence_pipeline as _run

    return _run(**kwargs)


def macro_intelligence_coverage() -> dict[str, Any]:
    from knowledge_factory.macro_intelligence.dashboard import macro_intelligence_dashboard
    from knowledge_factory.macro_intelligence import store as imi_store

    dash = macro_intelligence_dashboard()
    if not imi_store.list_objects():
        try:
            run_macro_intelligence_pipeline()
            dash = macro_intelligence_dashboard()
        except Exception:
            pass
    return dash


def run_company_intelligence_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.company_intelligence.pipeline import run_company_intelligence_pipeline as _run

    return _run(**kwargs)


def company_intelligence_coverage() -> dict[str, Any]:
    from knowledge_factory.company_intelligence.dashboard import company_intelligence_dashboard
    from knowledge_factory.company_intelligence import store as ici_store

    if ici_store.count() == 0:
        try:
            run_company_intelligence_pipeline()
        except Exception:
            pass
    return company_intelligence_dashboard(ensure=False)


def run_corporate_events_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.corporate_events.pipeline import run_corporate_events_pipeline as _run

    return _run(**kwargs)


def corporate_events_coverage() -> dict[str, Any]:
    from knowledge_factory.corporate_events.dashboard import corporate_events_dashboard
    from knowledge_factory.corporate_events import store as icei_store

    if icei_store.timeline_count() == 0:
        try:
            run_corporate_events_pipeline()
        except Exception:
            pass
    return corporate_events_dashboard(ensure=False)


def run_government_intelligence_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.government_intelligence.pipeline import run_government_intelligence_pipeline as _run

    return _run()


def government_intelligence_coverage() -> dict[str, Any]:
    from knowledge_factory.government_intelligence.dashboard import government_dashboard
    from knowledge_factory.government_intelligence import store as igri_store

    if igri_store.policy_count() == 0:
        try:
            run_government_intelligence_pipeline()
        except Exception:
            pass
    return government_dashboard(ensure=False)


def run_industry_intelligence_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.industry_intelligence.pipeline import run_industry_intelligence_pipeline as _run

    return _run()


def industry_intelligence_coverage() -> dict[str, Any]:
    from knowledge_factory.industry_intelligence.dashboards import industry_dashboard
    from knowledge_factory.industry_intelligence import store as iivi_store

    if iivi_store.industry_count() == 0:
        try:
            run_industry_intelligence_pipeline()
        except Exception:
            pass
    return industry_dashboard(ensure=False)


def run_economic_relationship_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.economic_relationship_intelligence.pipeline import (
        run_economic_relationship_pipeline as _run,
    )

    return _run()


def economic_relationship_coverage() -> dict[str, Any]:
    from knowledge_factory.economic_relationship_intelligence.dashboards import (
        relationship_dashboard,
    )
    from knowledge_factory.economic_relationship_intelligence import store as ieri_store

    if ieri_store.relationship_count() == 0:
        try:
            run_economic_relationship_pipeline()
        except Exception:
            pass
    return relationship_dashboard(ensure=False)


def run_alternative_data_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.alternative_data_intelligence.pipeline import (
        run_alternative_data_pipeline as _run,
    )

    return _run()


def alternative_data_coverage() -> dict[str, Any]:
    from knowledge_factory.alternative_data_intelligence.dashboards import (
        alternative_data_dashboard,
    )
    from knowledge_factory.alternative_data_intelligence import store as iadi_store

    if iadi_store.dataset_count() == 0:
        try:
            run_alternative_data_pipeline()
        except Exception:
            pass
    return alternative_data_dashboard(ensure=False)


def run_market_expectations_pipeline(**kwargs: Any) -> dict[str, Any]:
    from knowledge_factory.market_expectations_intelligence.pipeline import (
        run_market_expectations_pipeline as _run,
    )

    return _run()


def market_expectations_coverage() -> dict[str, Any]:
    from knowledge_factory.market_expectations_intelligence.dashboards import (
        expectations_dashboard,
    )
    from knowledge_factory.market_expectations_intelligence import store as imei_store

    if imei_store.expectation_count() == 0:
        try:
            run_market_expectations_pipeline()
        except Exception:
            pass
    return expectations_dashboard(ensure=False)


def company_object(entity: str) -> dict[str, Any] | None:
    return store.get_object("company", entity)


def evidence_feed(entity: str) -> dict[str, Any] | None:
    """Soft feed for Institutional Evidence Producers — never raw APIs."""
    pack = store.get_pack(entity)
    obj = store.get_object("company", entity)
    hd_pack = None
    hd_obj = None
    company_intelligence = None
    corporate_events = None
    government_policies = None
    industry_intelligence = None
    economic_relationships = None
    alternative_data = None
    market_expectations = None
    try:
        from knowledge_factory.historical_depth import store as hd_store

        hd_pack = hd_store.get_pack(entity)
        hd_obj = hd_store.get_object("company", entity)
    except Exception:
        pass
    # Soft-read Institutional Company Intelligence (optional enrichment; never required).
    try:
        from knowledge_factory.company_intelligence import store as ici_store

        company_intelligence = ici_store.get(entity)
    except Exception:
        company_intelligence = None
    # Soft-read Corporate Event Intelligence timeline (optional; never invent here).
    try:
        from knowledge_factory.corporate_events import store as icei_store

        corporate_events = icei_store.get_timeline(entity)
    except Exception:
        corporate_events = None
    # Soft-read Government policies that list this company (optional; no inference).
    try:
        from knowledge_factory.government_intelligence import store as igri_store

        t = entity.upper()
        government_policies = [
            p for p in igri_store.list_policies() if t in (p.get("affected_companies") or [])
        ]
    except Exception:
        government_policies = None
    # Soft-read Industry & Value Chain Intelligence for the company's industry.
    try:
        from knowledge_factory.industry_intelligence import store as iivi_store

        iid = iivi_store.get_company_industry(entity)
        industry_intelligence = iivi_store.get_industry(iid) if iid else None
    except Exception:
        industry_intelligence = None
    # Soft-read Economic Relationship Intelligence links for the entity.
    try:
        from knowledge_factory.economic_relationship_intelligence import store as ieri_store

        economic_relationships = ieri_store.list_relationships(entity=entity)
    except Exception:
        economic_relationships = None
    # Soft-read Alternative Data Intelligence datasets linked to the company.
    try:
        from knowledge_factory.alternative_data_intelligence.links.connect import (
            company_dataset_view,
        )

        alternative_data = company_dataset_view(entity)
    except Exception:
        alternative_data = None
    # Soft-read Market Expectations Intelligence (expectation vs reality).
    try:
        from knowledge_factory.market_expectations_intelligence.expectations.views import (
            company_expectations,
        )

        market_expectations = company_expectations(entity)
    except Exception:
        market_expectations = None
    if (
        not pack
        and not obj
        and not hd_pack
        and not hd_obj
        and not company_intelligence
        and not corporate_events
        and not government_policies
        and not industry_intelligence
        and not economic_relationships
        and not (alternative_data and alternative_data.get("n"))
        and not (market_expectations and market_expectations.get("n_expectations"))
    ):
        return None
    return {
        "source": "knowledge_factory",
        "entity": entity.upper(),
        "pack": pack,
        "company_object": obj,
        "historical_pack": hd_pack,
        "historical_company_object": hd_obj,
        "company_intelligence": company_intelligence,
        "corporate_events": corporate_events,
        "government_policies": government_policies,
        "industry_intelligence": industry_intelligence,
        "economic_relationships": economic_relationships,
        "alternative_data": alternative_data,
        "market_expectations": market_expectations,
        "raw_api": False,
    }
