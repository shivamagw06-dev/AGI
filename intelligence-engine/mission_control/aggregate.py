"""Read-only soft aggregation for Mission Control — never mutates research or house views."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mission_control.flags import flags_dict, is_enabled
from mission_control.schema import (
    ARCHITECTURE_NODES,
    COPILOT_PROMPTS,
    MISSION_CONTROL_VERSION,
    PLATFORMS,
    PROGRAMME,
    PROGRAMME_SHORT,
)
from mission_control import store as mc_store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_norm(v: Any) -> str:
    s = str(getattr(v, "value", v) or "unknown").lower()
    if s in {"ok", "healthy", "health", "pass", "passed", "green"}:
        return "Healthy"
    if s in {"warning", "warn", "stale", "degraded", "yellow"}:
        return "Warning"
    if s in {"critical", "fail", "failed", "error", "red"}:
        return "Critical"
    if s in {"offline", "disabled", "down"}:
        return "Offline"
    if s in {"unknown", "none", ""}:
        return "Unknown"
    return s.title() if s else "Unknown"


def _soft(fn, default=None):
    try:
        return fn()
    except Exception:
        return default if default is not None else {}


def _soft_institutional_intelligence() -> dict[str, Any]:
    """Soft-read Sprints 1–7 KPIs for Mission Control. Never mutates KF/IDQ stores here."""
    out: dict[str, Any] = {
        "decision_coverage": {},
        "historical_depth": None,
        "sector_intelligence": None,
        "macro_intelligence": None,
        "decision_quality": None,
        "roadmap_next": None,
        "sources": [],
    }
    try:
        from knowledge_factory.coverage import decision_coverage, NIFTY_100, NIFTY_500, TARGET_20
        from institutional_reasoning.fundamentals.universe import NIFTY_50

        t20 = decision_coverage(TARGET_20)
        n50 = decision_coverage(NIFTY_50)
        n100 = decision_coverage(NIFTY_100)
        n500 = decision_coverage(NIFTY_500)
        idc_pct = n500.get("decision_coverage_pct")
        try:
            from knowledge_factory.institutional_depth import institutional_decision_coverage

            idc = institutional_decision_coverage(NIFTY_500)
            idc_pct = idc.get("institutional_decision_coverage_pct")
        except Exception:
            pass
        out["decision_coverage"] = {
            "target_20": t20.get("decision_coverage_pct"),
            "nifty_50": n50.get("decision_coverage_pct"),
            "nifty_100": n100.get("decision_coverage_pct"),
            "nifty_500": n500.get("decision_coverage_pct"),
            "institutional_decision_coverage": idc_pct,
        }
        out["sources"].append("knowledge_factory.coverage")
        out["roadmap_next"] = (
            "tier_3_midcap_thematic"
            if (n500.get("decision_coverage_pct") or 0) >= 100
            else "nifty_500"
        )
    except Exception:
        pass
    try:
        from universe_intelligence.dashboard import universe_health

        uh = universe_health(universe_id="NIFTY_500", ensure=False)
        out["universe_intelligence"] = {
            "avg_ici": (uh.get("coverage") or {}).get("avg_ici"),
            "institutional_coverage_pct": (uh.get("coverage") or {}).get("institutional_coverage_pct"),
            "failure_count": uh.get("failure_count"),
            "stale_count": uh.get("stale_count"),
            "north_star": uh.get("north_star"),
        }
        out["sources"].append("universe_intelligence")
        if (uh.get("coverage") or {}).get("institutional_coverage_pct") == 100.0:
            out["roadmap_next"] = "tier_3_midcap_thematic"
    except Exception:
        out["universe_intelligence"] = None
    try:
        from knowledge_factory.company_intelligence.dashboard import company_intelligence_dashboard

        ci = company_intelligence_dashboard(ensure=False)
        out["company_intelligence"] = {
            "institutional_company_coverage_pct": ci.get("institutional_company_coverage_pct"),
            "average_intelligence_score": ci.get("average_intelligence_score"),
            "unknown_fields": ci.get("unknown_fields"),
            "north_star": ci.get("north_star"),
            "layer_label": ci.get("layer_label"),
        }
        out["sources"].append("company_intelligence")
        if (ci.get("institutional_company_coverage_pct") or 0) >= 100:
            out["roadmap_next"] = "company_intelligence_depth_enrichment"
    except Exception:
        out["company_intelligence"] = None
    try:
        from knowledge_factory.corporate_events.dashboard import corporate_events_dashboard

        ce = corporate_events_dashboard(ensure=False)
        out["corporate_events"] = {
            "coverage_pct": ce.get("coverage_pct"),
            "corporate_events": ce.get("corporate_events"),
            "critical_events": ce.get("critical_events"),
            "timeline_completeness_avg": ce.get("timeline_completeness_avg"),
            "north_star": ce.get("north_star"),
        }
        out["sources"].append("corporate_events")
        if (ce.get("coverage_pct") or 0) >= 100:
            out["roadmap_next"] = "government_regulatory_intelligence"
    except Exception:
        out["corporate_events"] = None
    try:
        from knowledge_factory.government_intelligence.dashboard import government_dashboard

        gov = government_dashboard(ensure=False)
        out["government_intelligence"] = {
            "coverage_pct": gov.get("coverage_pct"),
            "policy_count": gov.get("policy_count"),
            "high_impact_policies": gov.get("high_impact_policies"),
            "replay_status": gov.get("replay_status"),
            "north_star": gov.get("north_star"),
        }
        out["sources"].append("government_intelligence")
        if (gov.get("coverage_pct") or 0) >= 100:
            out["roadmap_next"] = "industry_value_chain_intelligence"
    except Exception:
        out["government_intelligence"] = None
    try:
        from knowledge_factory.industry_intelligence.dashboards import industry_dashboard

        ind = industry_dashboard(ensure=False)
        out["industry_intelligence"] = {
            "institutional_ready_pct": ind.get("institutional_ready_pct"),
            "industry_coverage": ind.get("industry_coverage"),
            "industry_intelligence_score": ind.get("industry_intelligence_score"),
            "companies_mapped": ind.get("companies_mapped"),
            "north_star": ind.get("north_star"),
            "future_roadmap": ind.get("future_roadmap"),
        }
        out["sources"].append("industry_intelligence")
        if (ind.get("institutional_ready_pct") or 0) >= 100 and (ind.get("companies_mapped") or 0) >= 500:
            out["roadmap_next"] = "economic_relationship_intelligence"
    except Exception:
        out["industry_intelligence"] = None
    try:
        from knowledge_factory.economic_relationship_intelligence.dashboards import (
            relationship_dashboard,
        )

        rel = relationship_dashboard(ensure=False)
        cov = rel.get("economic_relationship_coverage") or {}
        out["economic_relationship_intelligence"] = {
            "relationships": cov.get("relationships"),
            "commodities": cov.get("commodities"),
            "institutional_ready_pct": cov.get("institutional_ready_pct"),
            "company_relationships": rel.get("company_relationships"),
            "north_star": rel.get("north_star"),
        }
        out["sources"].append("economic_relationship_intelligence")
        if (cov.get("institutional_ready_pct") or 0) >= 100 and (cov.get("relationships") or 0) >= 50:
            out["roadmap_next"] = "alternative_data_intelligence"
    except Exception:
        out["economic_relationship_intelligence"] = None
    try:
        from knowledge_factory.alternative_data_intelligence.dashboards import (
            alternative_data_dashboard,
        )

        alt = alternative_data_dashboard(ensure=False)
        acov = alt.get("alternative_data_coverage") or {}
        out["alternative_data_intelligence"] = {
            "datasets": acov.get("datasets"),
            "observations": acov.get("observations"),
            "institutional_ready_pct": acov.get("institutional_ready_pct"),
            "economic_momentum": alt.get("economic_momentum"),
            "north_star": alt.get("north_star"),
            "delivery_phase": alt.get("delivery_phase"),
        }
        out["sources"].append("alternative_data_intelligence")
        if (acov.get("institutional_ready_pct") or 0) >= 100 and (acov.get("datasets") or 0) >= 10:
            out["roadmap_next"] = "market_expectations_intelligence"
    except Exception:
        out["alternative_data_intelligence"] = None
    try:
        from knowledge_factory.market_expectations_intelligence.dashboards import (
            expectations_dashboard,
        )

        exp = expectations_dashboard(ensure=False)
        ecov = exp.get("expectation_dashboard") or {}
        out["market_expectations_intelligence"] = {
            "expectations": ecov.get("expectations"),
            "revisions": ecov.get("revisions"),
            "surprises": ecov.get("surprises"),
            "narratives": ecov.get("narratives"),
            "institutional_ready_pct": ecov.get("institutional_ready_pct"),
            "north_star": exp.get("north_star"),
            "delivery_phase": exp.get("delivery_phase"),
            "principle": exp.get("principle"),
        }
        out["sources"].append("market_expectations_intelligence")
        if (ecov.get("surprises") or 0) >= 1 and (ecov.get("narratives") or 0) >= 10:
            out["roadmap_next"] = "knowledge_stack_complete"
    except Exception:
        out["market_expectations_intelligence"] = None
    # Unified Institutional Knowledge Stack board (soft orchestration).
    try:
        from knowledge_factory.institutional_knowledge_stack.production import dashboard as iks_dash

        iks = iks_dash(ensure=False)
        out["institutional_knowledge_stack"] = {
            "summary": iks.get("summary"),
            "reality": {
                k: {"status": v.get("status")} for k, v in (iks.get("reality") or {}).items()
            },
            "expectations": {
                k: {"status": v.get("status")} for k, v in (iks.get("expectations") or {}).items()
            },
            "roadmap_next": iks.get("roadmap_next"),
            "north_star": iks.get("north_star"),
        }
        out["sources"].append("institutional_knowledge_stack")
        if (iks.get("summary") or {}).get("stack_complete"):
            out["roadmap_next"] = "knowledge_stack_complete"
    except Exception:
        out["institutional_knowledge_stack"] = None
    # AGIB v2.1 Institutional Scheduler — soft ops heartbeat.
    try:
        from institutional_scheduler.production import dashboard as sched_dash
        from institutional_scheduler.production import status as sched_status

        st = sched_status()
        dash = sched_dash()
        out["institutional_scheduler"] = {
            "state": st.get("state"),
            "system_ready": st.get("system_ready"),
            "current_workflow": st.get("current_workflow"),
            "current_run_id": st.get("current_run_id"),
            "ready_status": (dash.get("ready_status") or {}),
            "mission_control_ops": dash.get("mission_control_ops"),
            "north_star": dash.get("north_star"),
        }
        out["sources"].append("institutional_scheduler")
        out["system_ready"] = bool(st.get("system_ready"))
    except Exception:
        out["institutional_scheduler"] = None
    # Continuous Gather → Learn — autonomous historical collection + knowledge loop.
    try:
        from continuous_gather_learn.production import dashboard as cgl_dash
        from continuous_gather_learn.production import health as cgl_health

        ch = cgl_health()
        cd = cgl_dash()
        out["continuous_gather_learn"] = {
            "status": ch.get("status"),
            "enabled": ch.get("enabled"),
            "version": ch.get("version"),
            "current_slot": cd.get("current_slot"),
            "latest_run": cd.get("latest_run"),
            "metrics": cd.get("metrics"),
            "freshness": cd.get("freshness"),
            "knowledge_growth": cd.get("knowledge_growth"),
            "archived_learnings": cd.get("archived_learnings"),
            "background": cd.get("background"),
            "flags": cd.get("flags"),
            "loop": cd.get("loop"),
            "ask_isolated": True,
            "ml_retrain": False,
            "north_star": cd.get("north_star"),
            "historical_coverage": cd.get("historical_coverage"),
            "historical_coverage_pct": cd.get("historical_coverage_pct"),
            "hard_coverage_pct": cd.get("hard_coverage_pct"),
            "soft_coverage_pct": cd.get("soft_coverage_pct"),
            "average_history_years": cd.get("average_history_years"),
            "companies_fully_backfilled": cd.get("companies_fully_backfilled"),
            "covered_companies": cd.get("covered_companies"),
            "remaining_backlog": cd.get("remaining_backlog"),
            "total_companies": cd.get("total_companies"),
            "current_listed_universe": cd.get("current_listed_universe"),
            "queue_length": cd.get("queue_length"),
            "companies_processed_today": cd.get("companies_processed_today"),
            "companies_remaining": cd.get("companies_remaining"),
            "new_listings_count": cd.get("new_listings_count"),
            "delisted_count": cd.get("delisted_count"),
            "pending_ipos_count": cd.get("pending_ipos_count"),
            "pending_ipos": cd.get("pending_ipos"),
            "company_scorecards": cd.get("company_scorecards"),
            "knowledge_extracts_total": cd.get("knowledge_extracts_total"),
            "embeddings_total": cd.get("embeddings_total"),
            "backfill_mode": cd.get("backfill_mode"),
            "maintenance_only": cd.get("maintenance_only"),
            "backfill_completed_at": cd.get("backfill_completed_at"),
            "continues_until_complete": cd.get("continues_until_complete"),
            "coverage_finished": False,
            "queue_always_ready": True,
            "documents_downloaded": cd.get("documents_downloaded"),
            "annual_reports": cd.get("annual_reports"),
            "quarterly_results": cd.get("quarterly_results"),
            "investor_presentations": cd.get("investor_presentations"),
            "collector_success_rate": cd.get("collector_success_rate"),
            "estimated_completion_days": cd.get("estimated_completion_days"),
            "historical_growth_per_day": cd.get("historical_growth_per_day"),
            "ops": cd.get("ops"),
        }
        out["sources"].append("continuous_gather_learn")
    except Exception:
        out["continuous_gather_learn"] = None
    # AGIB v2.1 Ask Pipeline board (soft observability).
    try:
        from ask_pipeline.production import dashboard as ask_dash

        ad = ask_dash()
        out["ask_pipeline"] = {
            "questions_today": ad.get("questions_today"),
            "average_latency_ms": ad.get("average_latency_ms"),
            "pipeline_coverage": ad.get("pipeline_coverage"),
            "evidence_coverage_avg": ad.get("evidence_coverage_avg"),
            "decision_records": ad.get("decision_records"),
            "outcome_registered": ad.get("outcome_registered"),
            "replay_ready": ad.get("replay_ready"),
            "north_star": ad.get("north_star"),
        }
        out["sources"].append("ask_pipeline")
    except Exception:
        out["ask_pipeline"] = None
    # AGIB v2.2 Institutional Research Office — soft research desk board.
    try:
        from research_office.production import dashboard as ro_dash
        from research_office.production import health as ro_health

        rd = ro_dash()
        rh = ro_health()
        out["research_office"] = {
            "status": (rh.get("office_status") or {}).get("state"),
            "ready_for_users": rd.get("ready_for_users"),
            "morning_publications": len(rd.get("todays_publications") or []),
            "research_queue_follow_ups": len((rd.get("outstanding_reviews") or [])),
            "outstanding_research": len(rd.get("outstanding_reviews") or []),
            "missing_coverage": len(rd.get("missing_evidence") or []),
            "publication_health": rd.get("validation"),
            "north_star": rd.get("north_star"),
        }
        out["sources"].append("research_office")
    except Exception:
        out["research_office"] = None
    # AGIB v4.0 — Research Intelligence Hub (soft).
    try:
        from research_intelligence_hub.production import dashboard as rih_dash
        from research_intelligence_hub.production import health as rih_health

        hd = rih_dash()
        hh = rih_health()
        out["research_intelligence_hub"] = {
            "status": hh.get("status"),
            "version": hh.get("version"),
            "programme_short": hh.get("programme_short"),
            "ask_triggers_collection": False,
            "is_intelligence_hub": True,
            "primary_knowledge_object": hh.get("primary_knowledge_object"),
            "hub_count": hd.get("hub_count"),
            "link_coverage": hd.get("link_coverage"),
            "current_hub": hd.get("current_hub"),
            "ingestion_idle": hd.get("ingestion_idle"),
            "phase": "4.0",
        }
        out["sources"].append("research_intelligence_hub")
    except Exception:
        out["research_intelligence_hub"] = None
    # AGIB v3.0 LIDI — live institutional data soft board.
    try:
        from live_data.production import dashboard as lidi_dash
        from live_data.production import health as lidi_health
        from live_data.production import status as lidi_status

        ls = lidi_status()
        ld = lidi_dash()
        lh = lidi_health()
        out["live_institutional_data"] = {
            "state": ls.get("state"),
            "collectors_operational": ls.get("collectors_operational"),
            "collectors_total": ls.get("collectors_total"),
            "validation_failures": ld.get("validation_failures"),
            "fallback_usage": ld.get("fallback_usage"),
            "missing_data": ld.get("missing_data"),
            "fixture_collectors_disabled": ls.get("fixture_collectors_disabled"),
            "north_star": ld.get("north_star"),
            "health": lh.get("status"),
        }
        out["sources"].append("live_institutional_data")
    except Exception:
        out["live_institutional_data"] = None
    # Phase 9 Forecast Provider Integration — India-first soft board.
    try:
        from forecast_provider_integration.production import dashboard as fpi_dash
        from forecast_provider_integration.production import health as fpi_mod_health

        fd = fpi_dash()
        fh = fpi_mod_health()
        out["forecast_provider_integration"] = {
            "status": fh.get("status"),
            "primary_live_market": fh.get("primary_live_market"),
            "primary_research": fh.get("primary_research"),
            "groww": fd.get("groww_connection_status"),
            "yahoo": fd.get("yahoo_finance_status"),
            "nse": fd.get("nse_collector_status"),
            "bse": fd.get("bse_collector_status"),
            "company_ir": fd.get("company_ir_collector_status"),
            "snapshot_freshness": fd.get("snapshot_freshness"),
            "failover_events": len(fd.get("provider_failover_events") or []),
            "forecast_direct_provider_calls": False,
            "controlled_refresh": fh.get("controlled_refresh"),
        }
        out["sources"].append("forecast_provider_integration")
    except Exception:
        out["forecast_provider_integration"] = None
    # Phase 10 Sprint 10.1 — Continuous Macroeconomic Knowledge Platform (soft).
    try:
        from continuous_macro_knowledge.production import dashboard as cmkp_dash
        from continuous_macro_knowledge.production import health as cmkp_health

        cd = cmkp_dash()
        ch = cmkp_health()
        cov = cd.get("knowledge_coverage") or {}
        out["continuous_macro_knowledge"] = {
            "status": ch.get("status"),
            "version": ch.get("version"),
            "ask_triggers_collection": False,
            "published_objects": cov.get("published_objects"),
            "unique_indicators": cov.get("unique_indicators"),
            "learning_events": cov.get("learning_events"),
            "collectors": len(cd.get("collector_health") or {}),
            "missing_indicators": len(cd.get("missing_indicators") or []),
            "ingestion_idle": cd.get("ingestion_idle"),
            "phase": "10.1",
        }
        out["sources"].append("continuous_macro_knowledge")
    except Exception:
        out["continuous_macro_knowledge"] = None
    # Phase 10 Sprint 10.2 — Historical Macroeconomic Intelligence (soft).
    try:
        from historical_macro_intelligence.production import dashboard as hmip_dash
        from historical_macro_intelligence.production import health as hmip_health

        hd = hmip_dash()
        hh = hmip_health()
        cov = hd.get("historical_coverage") or {}
        out["historical_macro_intelligence"] = {
            "status": hh.get("status"),
            "version": hh.get("version"),
            "ask_triggers_collection": False,
            "immutable_store": True,
            "total_observations": cov.get("total_observations"),
            "unique_indicators": cov.get("unique_indicators"),
            "years_available": cov.get("years_available"),
            "timelines": (hd.get("timeline_completeness") or {}).get("timelines"),
            "average_completeness_pct": (hd.get("timeline_completeness") or {}).get(
                "average_completeness_pct"
            ),
            "ingestion_idle": hd.get("ingestion_idle"),
            "phase": "10.2",
        }
        out["sources"].append("historical_macro_intelligence")
    except Exception:
        out["historical_macro_intelligence"] = None
    # Phase 10 Sprint 10.3 — Macroeconomic Relationship Intelligence (soft).
    try:
        from macroeconomic_relationship_intelligence.production import dashboard as mri_dash
        from macroeconomic_relationship_intelligence.production import health as mri_health

        md = mri_dash()
        mh = mri_health()
        out["macroeconomic_relationship_intelligence"] = {
            "status": mh.get("status"),
            "version": mh.get("version"),
            "ask_triggers_collection": False,
            "total_relationships": md.get("total_relationships"),
            "high_confidence": md.get("high_confidence"),
            "confidence_distribution": md.get("relationship_confidence_distribution"),
            "coverage": md.get("coverage_by_indicator_sector_company"),
            "stale": len(md.get("stale_relationships") or []),
            "ingestion_idle": md.get("ingestion_idle"),
            "phase": "10.3",
        }
        out["sources"].append("macroeconomic_relationship_intelligence")
    except Exception:
        out["macroeconomic_relationship_intelligence"] = None
    # Phase 10 Sprint 10.4 — Historical Macro Analogue Intelligence (soft).
    try:
        from historical_macro_analogue_intelligence.production import dashboard as hmai_dash
        from historical_macro_analogue_intelligence.production import health as hmai_health

        ad = hmai_dash()
        ah = hmai_health()
        cov = ad.get("historical_coverage") or {}
        out["historical_macro_analogue_intelligence"] = {
            "status": ah.get("status"),
            "version": ah.get("version"),
            "ask_triggers_collection": False,
            "current_regime": (ad.get("current_macro_regime") or {}).get("period"),
            "top_matches": len(ad.get("top_analogue_matches") or []),
            "similarity_distribution": ad.get("similarity_distribution"),
            "confidence_distribution": ad.get("confidence_distribution"),
            "historical_coverage": cov,
            "analogue_freshness": ad.get("analogue_freshness"),
            "ingestion_idle": ad.get("ingestion_idle"),
            "phase": "10.4",
        }
        out["sources"].append("historical_macro_analogue_intelligence")
    except Exception:
        out["historical_macro_analogue_intelligence"] = None
    # Phase 10 Sprint 10.5 — Macroeconomic Forecast Intelligence (soft).
    try:
        from macroeconomic_forecast_intelligence.production import dashboard as mfi_dash
        from macroeconomic_forecast_intelligence.production import health as mfi_health

        fd = mfi_dash()
        fh = mfi_health()
        out["macroeconomic_forecast_intelligence"] = {
            "status": fh.get("status"),
            "version": fh.get("version"),
            "ask_triggers_collection": False,
            "predicts_single_path": False,
            "probability_distribution": fd.get("probability_distribution"),
            "confidence_pct": (fd.get("confidence") or {}).get("overall_pct"),
            "scenarios": len(fd.get("bull_base_bear_scenarios") or []),
            "sector_impacts": len(fd.get("sector_impact_matrix") or {}),
            "company_impacts": len(fd.get("company_impact_matrix") or {}),
            "forecast_history_n": (fd.get("forecast_history") or {}).get("n"),
            "ingestion_idle": fd.get("ingestion_idle"),
            "phase": "10.5",
        }
        out["sources"].append("macroeconomic_forecast_intelligence")
    except Exception:
        out["macroeconomic_forecast_intelligence"] = None
    # Phase 11 Sprint 11.1 — Continuous Sector Knowledge Platform (soft).
    try:
        from continuous_sector_knowledge.production import dashboard as cskp_dash
        from continuous_sector_knowledge.production import health as cskp_health

        sd = cskp_dash()
        sh = cskp_health()
        health = sd.get("sector_health") or {}
        cov = sd.get("knowledge_coverage") or {}
        out["continuous_sector_knowledge"] = {
            "status": sh.get("status"),
            "version": sh.get("version"),
            "ask_triggers_collection": False,
            "ask_never_constructs": True,
            "published_sectors": health.get("published"),
            "universe": health.get("universe"),
            "coverage_pct": health.get("coverage_pct"),
            "learning_events": cov.get("learning_events"),
            "company_coverage_total": cov.get("company_coverage_total"),
            "ingestion_idle": sd.get("ingestion_idle"),
            "phase": "11.1",
        }
        out["sources"].append("continuous_sector_knowledge")
    except Exception:
        out["continuous_sector_knowledge"] = None
    # Phase 11 Sprint 11.2 — Historical Sector Intelligence (soft).
    try:
        from historical_sector_intelligence.production import dashboard as hsip_dash
        from historical_sector_intelligence.production import health as hsip_health

        hd = hsip_dash()
        hh = hsip_health()
        cov = hd.get("historical_coverage") or {}
        out["historical_sector_intelligence"] = {
            "status": hh.get("status"),
            "version": hh.get("version"),
            "ask_triggers_collection": False,
            "immutable_store": True,
            "total_observations": cov.get("total_observations"),
            "unique_sectors": cov.get("unique_sectors"),
            "years_available": cov.get("years_available"),
            "timelines": (hd.get("timeline_completeness") or {}).get("timelines"),
            "average_completeness_pct": (hd.get("timeline_completeness") or {}).get(
                "average_completeness_pct"
            ),
            "ingestion_idle": hd.get("ingestion_idle"),
            "phase": "11.2",
        }
        out["sources"].append("historical_sector_intelligence")
    except Exception:
        out["historical_sector_intelligence"] = None
    # Phase 11 Sprint 11.3 — Sector Relationship Intelligence (soft).
    try:
        from sector_relationship_intelligence.production import dashboard as sri_dash
        from sector_relationship_intelligence.production import health as sri_health

        sd = sri_dash()
        sh = sri_health()
        out["sector_relationship_intelligence"] = {
            "status": sh.get("status"),
            "version": sh.get("version"),
            "ask_triggers_collection": False,
            "evidence_backed_only": True,
            "total_relationships": sd.get("total_relationships"),
            "active_relationships": sd.get("active_relationships"),
            "confidence_distribution": sd.get("confidence_distribution"),
            "high_confidence": sd.get("high_confidence"),
            "by_kind": sd.get("by_kind"),
            "validation_failures": len(sd.get("validation_failures") or []),
            "ingestion_idle": sd.get("ingestion_idle"),
            "phase": "11.3",
        }
        out["sources"].append("sector_relationship_intelligence")
    except Exception:
        out["sector_relationship_intelligence"] = None
    # Phase 11 Sprint 11.4 — Historical Sector Analogue Intelligence (soft).
    try:
        from historical_sector_analogue_intelligence.production import dashboard as hsai_dash
        from historical_sector_analogue_intelligence.production import health as hsai_health

        ad = hsai_dash()
        ah = hsai_health()
        cov = ad.get("historical_coverage") or {}
        out["historical_sector_analogue_intelligence"] = {
            "status": ah.get("status"),
            "version": ah.get("version"),
            "ask_triggers_collection": False,
            "current_regime": (ad.get("current_sector_regime") or {}).get("period"),
            "current_sector": (ad.get("current_sector_regime") or {}).get("sector"),
            "top_matches": len(ad.get("top_analogue_matches") or []),
            "similarity_distribution": ad.get("similarity_distribution"),
            "confidence_distribution": ad.get("confidence_distribution"),
            "coverage_by_sector": ad.get("coverage_by_sector"),
            "historical_coverage": cov,
            "analogue_freshness": ad.get("analogue_freshness"),
            "ingestion_idle": ad.get("ingestion_idle"),
            "phase": "11.4",
        }
        out["sources"].append("historical_sector_analogue_intelligence")
    except Exception:
        out["historical_sector_analogue_intelligence"] = None
    # Phase 11 Sprint 11.5 — Sector Forecast Intelligence (soft).
    try:
        from sector_forecast_intelligence.production import dashboard as sfi_dash
        from sector_forecast_intelligence.production import health as sfi_health

        fd = sfi_dash()
        fh = sfi_health()
        out["sector_forecast_intelligence"] = {
            "status": fh.get("status"),
            "version": fh.get("version"),
            "ask_triggers_collection": False,
            "predicts_single_path": False,
            "inherits_macro_from": fh.get("inherits_macro_from"),
            "probability_distribution": fd.get("probability_distribution"),
            "confidence_pct": (fd.get("confidence") or {}).get("overall_pct"),
            "scenarios": len(fd.get("bull_base_bear_scenarios") or []),
            "company_impacts": len(fd.get("company_impact_summaries") or {}),
            "forecast_history_n": (fd.get("forecast_revisions") or {}).get("n"),
            "ingestion_idle": fd.get("ingestion_idle"),
            "phase": "11.5",
        }
        out["sources"].append("sector_forecast_intelligence")
    except Exception:
        out["sector_forecast_intelligence"] = None
    # Phase 12 Sprint 12.1 — Continuous Market Knowledge Platform (soft).
    try:
        from continuous_market_knowledge.production import dashboard as cmktp_dash
        from continuous_market_knowledge.production import health as cmktp_health

        md = cmktp_dash()
        mh = cmktp_health()
        out["continuous_market_knowledge"] = {
            "status": mh.get("status"),
            "version": mh.get("version"),
            "ask_triggers_collection": False,
            "not_a_market_data_service": True,
            "current_market_regime": md.get("current_market_regime"),
            "market_health_score": md.get("market_health_score"),
            "risk_sentiment": md.get("risk_sentiment"),
            "domains_published": (md.get("publication_status") or {}).get("published_domains"),
            "ingestion_idle": md.get("ingestion_idle"),
            "phase": "12.1",
        }
        out["sources"].append("continuous_market_knowledge")
    except Exception:
        out["continuous_market_knowledge"] = None
    # Phase 12 Sprint 12.2 — Historical Market Intelligence Platform (soft).
    try:
        from historical_market_intelligence.production import dashboard as hmkip_dash
        from historical_market_intelligence.production import health as hmkip_health

        hd = hmkip_dash()
        hh = hmkip_health()
        out["historical_market_intelligence"] = {
            "status": hh.get("status"),
            "version": hh.get("version"),
            "ask_triggers_collection": False,
            "immutable_store": True,
            "historical_coverage": hd.get("historical_coverage"),
            "timeline_completeness": (hd.get("timeline_completeness") or {}).get(
                "average_completeness_pct"
            ),
            "years_available": hd.get("years_available"),
            "ingestion_idle": hd.get("ingestion_idle"),
            "phase": "12.2",
        }
        out["sources"].append("historical_market_intelligence")
    except Exception:
        out["historical_market_intelligence"] = None
    # Phase 12 Sprint 12.3 — Market Relationship Intelligence (soft).
    try:
        from market_relationship_intelligence.production import dashboard as mkri_dash
        from market_relationship_intelligence.production import health as mkri_health

        md = mkri_dash()
        mh = mkri_health()
        out["market_relationship_intelligence"] = {
            "status": mh.get("status"),
            "version": mh.get("version"),
            "programme_short": mh.get("programme_short"),
            "ask_triggers_collection": False,
            "total_relationships": md.get("total_relationships"),
            "active_relationships": md.get("active_relationships"),
            "confidence_distribution": md.get("confidence_distribution"),
            "graph_health": md.get("graph_health"),
            "ingestion_idle": md.get("ingestion_idle"),
            "phase": "12.3",
        }
        out["sources"].append("market_relationship_intelligence")
    except Exception:
        out["market_relationship_intelligence"] = None
    # Phase 12 Sprint 12.4 — Historical Market Analogue Intelligence (soft).
    try:
        from historical_market_analogue_intelligence.production import dashboard as hmkai_dash
        from historical_market_analogue_intelligence.production import health as hmkai_health

        ad = hmkai_dash()
        ah = hmkai_health()
        out["historical_market_analogue_intelligence"] = {
            "status": ah.get("status"),
            "version": ah.get("version"),
            "programme_short": ah.get("programme_short"),
            "ask_triggers_collection": False,
            "current_market_regime": ad.get("current_market_regime"),
            "top_matches": len(ad.get("top_analogue_matches") or []),
            "similarity_distribution": ad.get("similarity_distribution"),
            "confidence_distribution": ad.get("confidence_distribution"),
            "ingestion_idle": ad.get("ingestion_idle"),
            "phase": "12.4",
        }
        out["sources"].append("historical_market_analogue_intelligence")
    except Exception:
        out["historical_market_analogue_intelligence"] = None
    # Phase 12 Sprint 12.5 — Market Forecast Intelligence (soft).
    # Programme short MKFI avoids collision with Macroeconomic Forecast Intelligence (MFI).
    try:
        from market_forecast_intelligence.production import dashboard as mkfi_dash
        from market_forecast_intelligence.production import health as mkfi_health

        fd = mkfi_dash()
        fh = mkfi_health()
        out["market_forecast_intelligence"] = {
            "status": fh.get("status"),
            "version": fh.get("version"),
            "programme_short": fh.get("programme_short"),
            "ask_triggers_collection": False,
            "predicts_single_path": False,
            "inherits_macro_from": fh.get("inherits_macro_from"),
            "probability_distribution": fd.get("probability_distribution"),
            "confidence_pct": (fd.get("confidence") or {}).get("overall_pct"),
            "scenarios": len(fd.get("bull_base_bear_scenarios") or []),
            "forecast_horizons": fd.get("forecast_horizons"),
            "sector_leadership": fd.get("sector_leadership_forecast"),
            "invalidation_alerts": len(fd.get("invalidation_alerts") or []),
            "forecast_history_n": (fd.get("forecast_revisions") or {}).get("n"),
            "ingestion_idle": fd.get("ingestion_idle"),
            "phase": "12.5",
        }
        out["sources"].append("market_forecast_intelligence")
    except Exception:
        out["market_forecast_intelligence"] = None
    # AGIB v3.0 LIDI Track 2 — collector certification board (soft).
    try:
        from live_data.production_verify import certification as lidi_cert
        from live_data.production_verify import health_dashboard as lidi_health_dash
        from live_data.production_verify import report_status as lidi_report_status

        cert = lidi_cert()
        hd = lidi_health_dash()
        rs = lidi_report_status()
        out["live_collector_activation"] = {
            "version": cert.get("version"),
            "certification_summary": cert.get("summary"),
            "dashboard_rows": len(hd.get("rows") or []),
            "readiness_score": (rs.get("readiness") or {}).get("score"),
            "last_verification_run_id": rs.get("last_run_id"),
            "north_star": hd.get("north_star"),
            "all_certified": (cert.get("summary") or {}).get("all_certified"),
        }
        out["sources"].append("live_collector_activation")
    except Exception:
        out["live_collector_activation"] = None
    # AGIB v3.1 IDI — institutional documents soft board.
    try:
        from knowledge_factory.institutional_documents.production import dashboard as idi_dash
        from knowledge_factory.institutional_documents.production import health as idi_health

        idh = idi_health()
        idd = idi_dash()
        out["institutional_documents"] = {
            "status": idh.get("status"),
            "version": idh.get("version"),
            "documents": idd.get("documents"),
            "companies_updated": len(idd.get("companies_updated") or []),
            "knowledge_objects_created": idd.get("knowledge_objects_created"),
            "validation_failures": idd.get("validation_failures"),
            "replay_status": idd.get("replay_status"),
            "north_star": idd.get("north_star"),
        }
        out["sources"].append("institutional_documents")
    except Exception:
        out["institutional_documents"] = None
    # AGIB v3.2 IERE — institutional evidence retrieval soft board.
    try:
        from evidence_retrieval.production import dashboard as iere_dash
        from evidence_retrieval.production import health as iere_health

        ih = iere_health()
        idash = iere_dash()
        out["evidence_retrieval"] = {
            "status": ih.get("status"),
            "version": ih.get("version"),
            "evidence_coverage": idash.get("evidence_coverage"),
            "evidence_freshness": idash.get("evidence_freshness"),
            "retrieval_latency_ms": idash.get("retrieval_latency_ms"),
            "citation_coverage": idash.get("citation_coverage"),
            "replay_health": idash.get("replay_health"),
            "knowledge_completeness": idash.get("knowledge_completeness"),
            "evidence_confidence": idash.get("evidence_confidence"),
            "north_star": idash.get("north_star"),
        }
        out["sources"].append("evidence_retrieval")
    except Exception:
        out["evidence_retrieval"] = None
    # AGIB v3.4 Track C — IFSE soft board
    try:
        from framework_selection.production import dashboard as ifse_dash
        from framework_selection.production import health as ifse_health

        fh = ifse_health()
        fd = ifse_dash()
        out["framework_selection"] = {
            "status": fh.get("status"),
            "version": fh.get("ifse_version"),
            "selection_count": fd.get("selection_count"),
            "wrong_framework_rate": fd.get("wrong_framework_rate"),
            "multi_framework_usage": fd.get("multi_framework_usage"),
            "confidence_distribution": fd.get("confidence_distribution"),
            "framework_coverage": fd.get("framework_coverage"),
            "framework_accuracy": fd.get("framework_accuracy"),
        }
        out["sources"].append("framework_selection")
    except Exception:
        out["framework_selection"] = None
    # AGIB v3.4 Track D — ICE soft board
    try:
        from institutional_communication.production import dashboard as ice_dash
        from institutional_communication.production import health as ice_health

        ih = ice_health()
        idash = ice_dash()
        out["institutional_communication"] = {
            "status": ih.get("status"),
            "version": ih.get("ice_version"),
            "communication_style": idash.get("communication_style"),
            "template_used": idash.get("template_used"),
            "framework_visibility": idash.get("framework_visibility"),
            "citation_density": idash.get("citation_density"),
            "narrative_completeness": idash.get("narrative_completeness"),
            "confidence_quality": idash.get("confidence_quality"),
            "generic_template_rate": idash.get("generic_template_rate"),
        }
        out["sources"].append("institutional_communication")
    except Exception:
        out["institutional_communication"] = None
    # AGIB v3.5 — IAP soft board
    try:
        from institutional_playbooks.production import dashboard as iap_dash
        from institutional_playbooks.production import health as iap_health

        ph = iap_health()
        pdash = iap_dash()
        out["institutional_playbooks"] = {
            "status": ph.get("status"),
            "version": ph.get("iap_version"),
            "registry_n": pdash.get("registry_n"),
            "category_counts": pdash.get("category_counts"),
            "target_met": pdash.get("target_met"),
            "recent_n": pdash.get("recent_n"),
            "guides_reasoning": True,
        }
        out["sources"].append("institutional_playbooks")
    except Exception:
        out["institutional_playbooks"] = None
    # AGIB v3.6 Phase 2 — IEG soft board
    try:
        from institutional_evidence_graph.production import dashboard as ieg_dash
        from institutional_evidence_graph.production import health as ieg_health

        eh = ieg_health()
        edash = ieg_dash()
        out["institutional_evidence_graph"] = {
            "status": eh.get("status"),
            "version": eh.get("ieg_version"),
            "n_domains": edash.get("n_domains"),
            "avg_domain_coverage_pct": edash.get("avg_domain_coverage_pct"),
            "recent_n": edash.get("recent_n"),
            "guides_evidence": True,
        }
        out["sources"].append("institutional_evidence_graph")
    except Exception:
        out["institutional_evidence_graph"] = None
    # AGIB v3.6 Phase 2 Sprint 2.2 — IMAI soft board
    try:
        from institutional_analog_intelligence.production import board as imai_board
        from institutional_analog_intelligence.production import status as imai_status

        mh = imai_status()
        mdash = imai_board()
        out["institutional_analog_intelligence"] = {
            "status": mh.get("status"),
            "version": mh.get("version"),
            "memory_count": mh.get("memory_count"),
            "memory_hits": mdash.get("memory_hits"),
            "analog_accuracy": mdash.get("analog_accuracy"),
            "regime_coverage": mdash.get("regime_coverage"),
            "historical_coverage": mdash.get("historical_coverage"),
            "replay_coverage": mdash.get("replay_coverage"),
            "guides_memory": True,
            "distinct_from_ilm": True,
        }
        out["sources"].append("institutional_analog_intelligence")
    except Exception:
        out["institutional_analog_intelligence"] = None
    # AGIB Phase 3 Sprint 3.1 — IEL soft board
    try:
        from institutional_evaluation_lab.production import board as iel_board
        from institutional_evaluation_lab.production import status as iel_status

        ih = iel_status()
        idash = iel_board()
        latest = idash.get("latest_run") or {}
        out["institutional_evaluation_lab"] = {
            "status": ih.get("status"),
            "version": ih.get("version"),
            "catalogue_all": (ih.get("catalogue") or {}).get("all"),
            "meets_1000_plus": (ih.get("catalogue") or {}).get("meets_1000_plus"),
            "latest_pass_pct": latest.get("pass_pct"),
            "latest_mean_score": latest.get("mean_score"),
            "quality_targets": ih.get("quality_targets"),
            "measurement_only": True,
        }
        out["sources"].append("institutional_evaluation_lab")
    except Exception:
        out["institutional_evaluation_lab"] = None
    # AGI Institutional Intelligence Examination (IIEX) — CIO soft board
    try:
        from institutional_intelligence_examination.production import dashboard as iiex_dash
        from institutional_intelligence_examination.production import health as iiex_health

        ihx = iiex_health()
        idx = iiex_dash()
        out["institutional_intelligence_examination"] = {
            "status": ihx.get("status"),
            "module_code": ihx.get("module_code"),
            "version": ihx.get("version"),
            "phase": idx.get("phase"),
            "questions": ihx.get("questions"),
            "pass_marks": ihx.get("pass_marks"),
            "normalized_total": ihx.get("normalized_total"),
            "latest_run_id": idx.get("latest_run_id"),
            "latest_normalized_500": idx.get("latest_normalized_500"),
            "latest_certification": idx.get("latest_certification"),
            "latest_passed": idx.get("latest_passed"),
            "purpose": "CIO Investment Committee Assessment — AGIB platform only",
            "providers_queried": [],
        }
        out["sources"].append("institutional_intelligence_examination")
    except Exception:
        out["institutional_intelligence_examination"] = None
    # AGIB Phase 3 Sprint 3.2 — RCI soft board
    try:
        from root_cause_intelligence.production import board as rci_board
        from root_cause_intelligence.production import status as rci_status

        rh = rci_status()
        rdash = rci_board()
        out["root_cause_intelligence"] = {
            "status": rh.get("status"),
            "version": rh.get("version"),
            "n_failures": rdash.get("n_failures"),
            "n_clusters": rdash.get("n_clusters"),
            "iel_pass_pct": rdash.get("iel_pass_pct"),
            "top_cluster": ((rdash.get("top_10") or [{}])[0]).get("impact_statement"),
            "recommended_pr_count": len(rdash.get("recommended_prs") or []),
            "gaps": rdash.get("gaps"),
            "measurement_driven": True,
        }
        out["sources"].append("root_cause_intelligence")
    except Exception:
        out["root_cause_intelligence"] = None
    # Patch Intelligence — human-in-the-loop briefs
    try:
        from patch_intelligence.production import status as pi_status
        from root_cause_intelligence import store as rci_store

        ph = pi_status()
        latest = rci_store.latest() or {}
        pi = latest.get("patch_intelligence") or {}
        out["patch_intelligence"] = {
            "status": ph.get("status"),
            "version": ph.get("version"),
            "n_briefs": pi.get("n_briefs"),
            "highest_roi": (pi.get("highest_roi") or {}).get("recommended_title"),
            "never_writes_code_automatically": True,
        }
        out["sources"].append("patch_intelligence")
    except Exception:
        out["patch_intelligence"] = None
    # AGI Phase 3 Sprint 3.5 — Temporal Integrity & Replay Certification
    try:
        from temporal_integrity.production import dashboard as tirc_dashboard
        from temporal_integrity.production import status as tirc_status

        th = tirc_status()
        td = tirc_dashboard()
        out["temporal_integrity"] = {
            "company": th.get("company"),
            "status": th.get("status"),
            "version": th.get("version"),
            "replay_health": td.get("replay_health"),
            "certification_status": td.get("certification_status"),
            "future_leakage_count": td.get("future_leakage_count"),
            "replay_accuracy_pct": td.get("replay_accuracy_pct"),
            "objects_rejected": td.get("objects_rejected"),
            "institutional_guarantee": td.get("institutional_guarantee"),
        }
        out["sources"].append("temporal_integrity")
    except Exception:
        out["temporal_integrity"] = None
    # AGI Observability — LangSmith tracing status (read-only)
    try:
        from observability.production import dashboard as obs_dashboard

        od = obs_dashboard()
        out["observability"] = {
            "provider": "langsmith",
            "enabled": od.get("enabled"),
            "project": od.get("project"),
            "api_key_present": od.get("api_key_present"),
            "sdk_available": od.get("sdk_available"),
            "traced_stages": od.get("n_traced_stages"),
            "observability_only": True,
        }
        out["sources"].append("observability")
    except Exception:
        out["observability"] = None
    # AGI Phase 4 Sprint 4.1 — Institutional Evidence Weighting Engine
    try:
        from institutional_evidence_weighting.production import dashboard as iew_dashboard
        from institutional_evidence_weighting.production import status as iew_status

        ih = iew_status()
        idash = iew_dashboard()
        out["institutional_evidence_weighting"] = {
            "company": ih.get("company"),
            "status": ih.get("status"),
            "version": ih.get("version"),
            "weight_version": idash.get("weight_version"),
            "average_weight": idash.get("average_weight"),
            "dominant_sources": idash.get("dominant_sources"),
            "n_recent_runs": idash.get("n_recent_runs"),
            "replay_status": idash.get("replay_status"),
            "llm_used": False,
        }
        out["sources"].append("institutional_evidence_weighting")
    except Exception:
        out["institutional_evidence_weighting"] = None
    # AGI Phase 4 Sprint 4.2 — Institutional Hypothesis Generation Engine
    try:
        from institutional_hypothesis_generation.production import dashboard as ihg_dashboard
        from institutional_hypothesis_generation.production import status as ihg_status

        hh = ihg_status()
        hd = ihg_dashboard()
        out["institutional_hypothesis_generation"] = {
            "company": hh.get("company"),
            "status": hh.get("status"),
            "version": hh.get("version"),
            "hypothesis_version": hd.get("hypothesis_version"),
            "average_hypotheses": hd.get("average_hypotheses"),
            "rejected_hypotheses": hd.get("rejected_hypotheses"),
            "winning_hypothesis": hd.get("winning_hypothesis"),
            "hypothesis_confidence": hd.get("hypothesis_confidence"),
            "evidence_support": hd.get("evidence_support"),
            "conflict_score": hd.get("conflict_score"),
            "plural": hd.get("plural"),
            "forced_single_winner": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_hypothesis_generation")
    except Exception:
        out["institutional_hypothesis_generation"] = None
    # AGI Phase 4 Sprint 4.3 — Institutional Hypothesis Evaluation Engine
    try:
        from institutional_hypothesis_evaluation.production import dashboard as ihe_dashboard
        from institutional_hypothesis_evaluation.production import status as ihe_status

        eh = ihe_status()
        ed = ihe_dashboard()
        out["institutional_hypothesis_evaluation"] = {
            "company": eh.get("company"),
            "status": eh.get("status"),
            "version": eh.get("version"),
            "evaluation_version": ed.get("evaluation_version"),
            "preferred_hypotheses": ed.get("preferred_hypotheses"),
            "rejected_hypotheses": ed.get("rejected_hypotheses"),
            "average_support": ed.get("average_support"),
            "average_conflict": ed.get("average_conflict"),
            "coverage": ed.get("coverage"),
            "missing_evidence_frequency": ed.get("missing_evidence_frequency"),
            "outcome": ed.get("outcome"),
            "plural": ed.get("plural"),
            "forced_single_winner": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_hypothesis_evaluation")
    except Exception:
        out["institutional_hypothesis_evaluation"] = None
    # AGI Phase 4 Sprint 4.4 — Institutional Committee Reasoning (ICR)
    try:
        from institutional_committee_reasoning.production import dashboard as icr_dashboard
        from institutional_committee_reasoning.production import status as icr_status

        ch = icr_status()
        cd = icr_dashboard()
        out["institutional_committee_reasoning"] = {
            "company": ch.get("company"),
            "status": ch.get("status"),
            "version": ch.get("version"),
            "committee_version": cd.get("committee_version"),
            "bull_base_bear_distribution": cd.get("bull_base_bear_distribution"),
            "average_confidence": cd.get("average_confidence"),
            "probability_distribution": cd.get("probability_distribution"),
            "unresolved_disagreements": cd.get("unresolved_disagreements"),
            "missing_evidence": cd.get("missing_evidence"),
            "dominant_assumptions": cd.get("dominant_assumptions"),
            "historical_analogue_usage": cd.get("historical_analogue_usage"),
            "preferred_case": cd.get("preferred_case"),
            "voting_engine": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_committee_reasoning")
    except Exception:
        out["institutional_committee_reasoning"] = None
    # AGI Phase 4 Sprint 4.5 — Institutional Confidence Calibration (ICC)
    try:
        from institutional_confidence_calibration.production import dashboard as icc_dashboard
        from institutional_confidence_calibration.production import status as icc_status

        fh = icc_status()
        fd = icc_dashboard()
        out["institutional_confidence_calibration"] = {
            "company": fh.get("company"),
            "status": fh.get("status"),
            "version": fh.get("version"),
            "confidence_version": fd.get("confidence_version"),
            "average_confidence": fd.get("average_confidence"),
            "confidence_distribution": fd.get("confidence_distribution"),
            "top_uncertainty_drivers": fd.get("top_uncertainty_drivers"),
            "evidence_penalties": fd.get("evidence_penalties"),
            "committee_agreement": fd.get("committee_agreement"),
            "missing_evidence": fd.get("missing_evidence"),
            "historical_analogue_quality": fd.get("historical_analogue_quality"),
            "framework_consistency": fd.get("framework_consistency"),
            "latest_confidence": fd.get("latest_confidence"),
            "latest_reason": fd.get("latest_reason"),
            "llm_used": False,
            "manually_assigned": False,
            "phase4_complete": True,
        }
        out["sources"].append("institutional_confidence_calibration")
    except Exception:
        out["institutional_confidence_calibration"] = None
    # AGI v4.0 Phase 5 Sprint 5.1 — Institutional Investment Thesis Engine
    try:
        from institutional_investment_thesis.production import dashboard as ite_dashboard
        from institutional_investment_thesis.production import status as ite_status

        th = ite_status()
        td = ite_dashboard()
        out["institutional_investment_thesis"] = {
            "company": th.get("company"),
            "status": th.get("status"),
            "version": th.get("version"),
            "release": th.get("release"),
            "n_theses": td.get("n_theses"),
            "n_active": td.get("n_active"),
            "n_watch": td.get("n_watch"),
            "lifecycle_distribution": td.get("lifecycle_distribution"),
            "decision_distribution": td.get("decision_distribution"),
            "average_confidence_active": td.get("average_confidence_active"),
            "waiting_for_earnings_review": td.get("waiting_for_earnings_review"),
            "confidence_dropped_gt_10": td.get("confidence_dropped_gt_10"),
            "buy_sell": False,
            "judgment_stack_modified": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_investment_thesis")
    except Exception:
        out["institutional_investment_thesis"] = None
    # AGI v4.0 Phase 5 Sprint 5.2 — Institutional Decision Office
    try:
        from institutional_decision_office.production import dashboard as ido_dashboard
        from institutional_decision_office.production import status as ido_status

        dh = ido_status()
        dd = ido_dashboard()
        out["institutional_decision_office"] = {
            "company": dh.get("company"),
            "status": dh.get("status"),
            "version": dh.get("version"),
            "release": dh.get("release"),
            "n_decisions": dd.get("n_decisions"),
            "decision_distribution": dd.get("decision_distribution"),
            "lifecycle_distribution": dd.get("lifecycle_distribution"),
            "n_wait": dd.get("n_wait"),
            "n_monitor": dd.get("n_monitor"),
            "n_approve": dd.get("n_approve"),
            "n_escalate": dd.get("n_escalate"),
            "review_after_earnings": dd.get("review_after_earnings"),
            "orders": False,
            "buy_sell": False,
            "execution": False,
            "judgment_stack_modified": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_decision_office")
    except Exception:
        out["institutional_decision_office"] = None
    # AGI v4.0 Phase 5 Sprint 5.3 — Institutional Portfolio Office
    try:
        from institutional_portfolio_office.production import dashboard as ipo_dashboard
        from institutional_portfolio_office.production import status as ipo_status

        ph = ipo_status()
        pd = ipo_dashboard()
        out["institutional_portfolio_office"] = {
            "company": ph.get("company"),
            "status": ph.get("status"),
            "version": ph.get("version"),
            "release": ph.get("release"),
            "n_ideas": pd.get("n_ideas"),
            "role_distribution": pd.get("role_distribution"),
            "sector_distribution": pd.get("sector_distribution"),
            "status_distribution": pd.get("status_distribution"),
            "it_services_relative_ranking": pd.get("it_services_relative_ranking"),
            "positions": False,
            "orders": False,
            "execution": False,
            "judgment_stack_modified": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_portfolio_office")
    except Exception:
        out["institutional_portfolio_office"] = None
    # AGI v4.0 Phase 5 Sprint 5.4 — Institutional Monitoring Office
    try:
        from institutional_monitoring_office.production import dashboard as imo_dashboard
        from institutional_monitoring_office.production import status as imo_status

        mh = imo_status()
        md = imo_dashboard()
        out["institutional_monitoring_office"] = {
            "company": mh.get("company"),
            "status": mh.get("status"),
            "version": mh.get("version"),
            "release": mh.get("release"),
            "n_events": md.get("n_events"),
            "requires_review": md.get("requires_review"),
            "ideas_covered": md.get("ideas_covered"),
            "by_severity": md.get("by_severity"),
            "by_recommended_action": md.get("by_recommended_action"),
            "domains_monitored": md.get("domains_monitored"),
            "mutates_thesis": False,
            "positions": False,
            "orders": False,
            "execution": False,
            "judgment_stack_modified": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_monitoring_office")
    except Exception:
        out["institutional_monitoring_office"] = None
    # AGI v4.0 Phase 5 Sprint 5.5 — Institutional Learning Office (final Office)
    try:
        from institutional_learning_office.production import dashboard as ilo_dashboard
        from institutional_learning_office.production import status as ilo_status

        lh = ilo_status()
        ld = ilo_dashboard()
        out["institutional_learning_office"] = {
            "company": lh.get("company"),
            "status": lh.get("status"),
            "version": lh.get("version"),
            "release": lh.get("release"),
            "final_office_module": True,
            "n_learnings": ld.get("n_learnings"),
            "by_category": ld.get("by_category"),
            "by_outcome": ld.get("by_outcome"),
            "theses_covered": ld.get("theses_covered"),
            "knowledge_factory_updated": False,
            "process_memory_only": True,
            "mutates_thesis": False,
            "positions": False,
            "orders": False,
            "execution": False,
            "judgment_stack_modified": False,
            "llm_used": False,
        }
        out["sources"].append("institutional_learning_office")
    except Exception:
        out["institutional_learning_office"] = None
    try:
        from knowledge_factory.production import historical_depth_coverage

        hd = historical_depth_coverage()
        out["historical_depth"] = {
            "average_history_years": hd.get("average_history_years"),
            "companies_gt_20y_pct": hd.get("companies_gt_20y_pct"),
            "point_in_time_integrity": hd.get("point_in_time_integrity"),
        }
        out["sources"].append("historical_depth")
    except Exception:
        pass
    try:
        from knowledge_factory.production import sector_intelligence_coverage

        isi = sector_intelligence_coverage()
        out["sector_intelligence"] = {
            "sector_coverage_pct": isi.get("sector_coverage_pct"),
            "playbook_coverage_pct": isi.get("playbook_coverage_pct"),
            "status": isi.get("status"),
        }
        out["sources"].append("sector_intelligence")
    except Exception:
        pass
    try:
        from knowledge_factory.production import macro_intelligence_coverage

        imi = macro_intelligence_coverage()
        kpi = imi.get("kpi") or imi
        out["macro_intelligence"] = {
            "coverage": kpi.get("coverage"),
            "status": imi.get("status"),
            "regime_coverage": kpi.get("regime_coverage"),
        }
        out["sources"].append("macro_intelligence")
    except Exception:
        pass
    try:
        from decision_quality.production import dashboard as idq_dashboard

        idq = idq_dashboard()
        kpi = idq.get("kpi") or {}
        out["decision_quality"] = {
            "coverage": kpi.get("coverage") or kpi.get("institutional_decision_quality"),
            "status": idq.get("status"),
            "hall_fame": (kpi.get("counts") or {}).get("hall_fame"),
            "hall_shame": (kpi.get("counts") or {}).get("hall_shame"),
        }
        out["sources"].append("decision_quality")
    except Exception:
        pass
    # FSE + FDO Phase 1 — Financial Statements Engine ops (soft-wire only).
    try:
        from financial_statements_engine.fdo.production import dashboard as fdo_dash
        from financial_statements_engine.fdo.production import health as fdo_health

        fh = fdo_health()
        fd = fdo_dash("gold")
        growth = fd.get("raw_evidence_growth") or {}
        out["financial_data_operations"] = {
            "status": fh.get("status"),
            "workstream_id": fh.get("workstream_id") or fd.get("workstream_id"),
            "version": fh.get("version") or fd.get("version"),
            "phase": fh.get("phase") or fd.get("phase"),
            "coverage_pct": fd.get("coverage_pct"),
            "completeness_pct": fd.get("completeness_pct"),
            "workflow_throughput": fd.get("workflow_throughput"),
            "queue_depth": fd.get("queue_depth"),
            "dlq_size": fd.get("dlq_size"),
            "average_workflow_duration_ms": fd.get("average_workflow_duration_ms"),
            "raw_evidence_files": growth.get("files"),
            "raw_storage_mb": growth.get("storage_mb"),
            "annual_filings": growth.get("annual_filings"),
            "quarterly_filings": growth.get("quarterly_filings"),
            "top_missing_companies": (fd.get("top_missing_companies") or [])[:5],
            "alerts_n": len(fd.get("alerts") or []),
            "redesigns_engines": False,
            "bypasses_fse": False,
            "issues_recommendations": False,
        }
        out["sources"].append("financial_data_operations")
    except Exception:
        out["financial_data_operations"] = None
    try:
        from financial_statements_engine.production import health as fse_health

        fseh = fse_health()
        out["financial_statements_engine"] = {
            "status": fseh.get("status"),
            "version": fseh.get("version"),
            "programme": fseh.get("programme"),
            "soft_wire": True,
        }
        out["sources"].append("financial_statements_engine")
    except Exception:
        out["financial_statements_engine"] = None
    try:
        from financial_statements_engine.collection.production import source_coverage

        sc = source_coverage()
        out["fse_source_coverage"] = {
            "status": sc.get("status") or "ok",
            "sources_n": sc.get("n") or len(sc.get("sources") or []),
            "summary": sc.get("summary"),
        }
        out["sources"].append("fse_source_coverage")
    except Exception:
        out["fse_source_coverage"] = None
    # FIRE-01 — Financial Narrative & Trend Engine (soft board; no BUY/SELL).
    try:
        from financial_intelligence.production import soft_slice_mission_control

        out["financial_intelligence"] = soft_slice_mission_control()
        out["sources"].append("financial_intelligence")
    except Exception:
        out["financial_intelligence"] = None
    # FIRE-02 — Relationship & Driver Analysis (soft board; additive).
    try:
        from financial_intelligence.drivers.production import soft_slice_mission_control as fire02_soft

        out["financial_drivers"] = fire02_soft()
        out["sources"].append("financial_drivers")
    except Exception:
        out["financial_drivers"] = None
    # FKB-01 — Institutional Financial Knowledge Base (definitions only).
    try:
        from financial_knowledge.production import soft_slice_mission_control as fkb_soft

        out["financial_knowledge"] = fkb_soft()
        out["sources"].append("financial_knowledge")
    except Exception:
        out["financial_knowledge"] = None
    # FIRE-03 — Business & Management Intelligence (soft board; additive).
    try:
        from business_intelligence.production import soft_slice_mission_control as fire03_soft

        out["business_intelligence"] = fire03_soft()
        out["sources"].append("business_intelligence")
    except Exception:
        out["business_intelligence"] = None
    # FIRE-04 — Evidence Fusion Engine (soft board; additive).
    try:
        from evidence_fusion.production import soft_slice_mission_control as fire04_soft

        out["evidence_fusion"] = fire04_soft()
        out["sources"].append("evidence_fusion")
    except Exception:
        out["evidence_fusion"] = None
    # FIRE-05 — Management Execution & Temporal Evidence (soft board; additive).
    try:
        from management_execution.production import soft_slice_mission_control as fire05_soft

        out["management_execution"] = fire05_soft()
        out["sources"].append("management_execution")
    except Exception:
        out["management_execution"] = None
    # FIRE-06 — Business Quality Engine (soft board; additive).
    try:
        from business_quality.production import soft_slice_mission_control as fire06_soft

        out["business_quality"] = fire06_soft()
        out["sources"].append("business_quality")
    except Exception:
        out["business_quality"] = None
    # IO-01 — Institutional Investment Office IRP orchestration (soft board; additive).
    try:
        from investment_office.production import soft_slice_mission_control as io01_soft

        out["investment_office_irp"] = io01_soft()
        out["sources"].append("investment_office_irp")
    except Exception:
        out["investment_office_irp"] = None
    # CIO-01 — Comparative Intelligence Office (soft board; additive).
    try:
        from comparative_intelligence.production import soft_slice_mission_control as cio01_soft

        out["comparative_intelligence"] = cio01_soft()
        out["sources"].append("comparative_intelligence")
    except Exception:
        out["comparative_intelligence"] = None
    # Office SDK — shared application contract (soft board; additive).
    try:
        from office_sdk.production import soft_slice_mission_control as office_sdk_soft

        out["office_sdk"] = office_sdk_soft()
        out["sources"].append("office_sdk")
    except Exception:
        out["office_sdk"] = None
    # PO-01 — Portfolio Office (soft board; additive).
    try:
        from portfolio_office.production import soft_slice_mission_control as po01_soft

        out["portfolio_office"] = po01_soft()
        out["sources"].append("portfolio_office")
    except Exception:
        out["portfolio_office"] = None
    # PEB-01 — Platform Event Bus (soft board; additive).
    try:
        from platform_event_bus.production import soft_slice_mission_control as peb01_soft

        out["platform_event_bus"] = peb01_soft()
        out["sources"].append("platform_event_bus")
    except Exception:
        out["platform_event_bus"] = None
    # WO-01 — Watchlist Office (soft board; additive).
    try:
        from watchlist_office.production import soft_slice_mission_control as wo01_soft

        out["watchlist_office"] = wo01_soft()
        out["sources"].append("watchlist_office")
    except Exception:
        out["watchlist_office"] = None
    # CW-01 — Company Workspace UX (soft board; presentation only; additive).
    try:
        from company_workspace.production import soft_slice_mission_control as cw01_soft

        out["company_workspace"] = cw01_soft()
        out["sources"].append("company_workspace")
    except Exception:
        out["company_workspace"] = None
    # IST-01 — Institutional Stress Tests (orchestration exams; additive).
    try:
        from institutional_stress_tests.production import soft_slice_mission_control as ist_soft

        out["institutional_stress_tests"] = ist_soft()
        out["sources"].append("institutional_stress_tests")
    except Exception:
        out["institutional_stress_tests"] = None
    # IBS-01 — AGI Institutional Benchmark Suite (permanent; additive).
    try:
        from institutional_benchmarks.production import soft_slice_mission_control as ibs_soft

        out["institutional_benchmarks"] = ibs_soft()
        out["sources"].append("institutional_benchmarks")
    except Exception:
        out["institutional_benchmarks"] = None
    # E2E-01 — Institutional Product Experience Validation (not an engine; additive).
    try:
        from product_experience_validation.production import soft_slice_mission_control as e2e_soft

        out["product_experience_validation"] = e2e_soft()
        out["sources"].append("product_experience_validation")
    except Exception:
        out["product_experience_validation"] = None
    # RH-01 — AGI Release Health (single release gate; additive).
    try:
        from release_health.production import soft_slice_mission_control as rh_soft

        out["release_health"] = rh_soft()
        out["sources"].append("release_health")
    except Exception:
        out["release_health"] = None

    # IRE-01 — Institutional Reporting Engine (deterministic; no LLM).
    try:
        from institutional_reporting.production import soft_slice_mission_control as ire_soft

        out["institutional_reporting"] = ire_soft()
        out["sources"].append("institutional_reporting")
    except Exception:
        out["institutional_reporting"] = None

    # IDS-01 — Institutional Decision System (owns recommendation).
    try:
        from institutional_decision.production import soft_slice_mission_control as ids_soft

        out["institutional_decision"] = ids_soft()
        out["sources"].append("institutional_decision")
    except Exception:
        out["institutional_decision"] = None

    # IDS-02 — Decision Calibration & Explainability.
    try:
        from institutional_calibration.production import soft_slice_mission_control as cal_soft

        out["institutional_calibration"] = cal_soft()
        out["sources"].append("institutional_calibration")
    except Exception:
        out["institutional_calibration"] = None

    # KG-01 — Institutional Knowledge Graph (single-company).
    try:
        from institutional_graph.production import soft_slice_mission_control as kg_soft

        out["institutional_graph"] = kg_soft()
        out["sources"].append("institutional_graph")
    except Exception:
        out["institutional_graph"] = None

    # FG-01 — Forecast & Scenario Graph.
    try:
        from institutional_forecasting.production import soft_slice_mission_control as fg_soft

        out["institutional_forecasting"] = fg_soft()
        out["sources"].append("institutional_forecasting")
    except Exception:
        out["institutional_forecasting"] = None

    # IO-01 — Institutional Observation Engine (Observation Center).
    try:
        from institutional_observation.production import soft_slice_mission_control as obs_soft

        out["institutional_observation"] = obs_soft()
        out["sources"].append("institutional_observation")
    except Exception:
        out["institutional_observation"] = None

    # PKG-01 / Phase 4.1 PO-01 — Portfolio Knowledge Graph.
    try:
        from institutional_portfolio.production import soft_slice_mission_control as pkg_soft

        out["institutional_portfolio"] = pkg_soft()
        out["sources"].append("institutional_portfolio")
    except Exception:
        out["institutional_portfolio"] = None

    # PRE-01 — Institutional Portfolio Risk Engine (Risk Center).
    try:
        from institutional_portfolio_risk.production import soft_slice_mission_control as pre_soft

        out["institutional_portfolio_risk"] = pre_soft()
        out["sources"].append("institutional_portfolio_risk")
    except Exception:
        out["institutional_portfolio_risk"] = None

    # PCE-01 — Institutional Policy & Constraint Engine (Policy Center).
    try:
        from institutional_policy.production import soft_slice_mission_control as pce_soft

        out["institutional_policy"] = pce_soft()
        out["sources"].append("institutional_policy")
    except Exception:
        out["institutional_policy"] = None

    # CIO-01 — Institutional Portfolio Decision System (Portfolio Command Center).
    try:
        from institutional_portfolio_decision.production import soft_slice_mission_control as cio_soft

        out["institutional_portfolio_decision"] = cio_soft()
        out["sources"].append("institutional_portfolio_decision")
    except Exception:
        out["institutional_portfolio_decision"] = None

    # ICE-01 — Investment Committee Engine (Committee Center).
    try:
        from institutional_committee.production import soft_slice_mission_control as ice_soft

        out["institutional_committee"] = ice_soft()
        out["sources"].append("institutional_committee")
    except Exception:
        out["institutional_committee"] = None

    # UAG-01 — Universal Ask AGI Orchestrator (Orchestration Center).
    try:
        from institutional_orchestrator.production import soft_slice_mission_control as uag_soft

        out["institutional_orchestrator"] = uag_soft()
        out["sources"].append("institutional_orchestrator")
    except Exception:
        out["institutional_orchestrator"] = None

    # RW-01 — Institutional Research Workspace (Workspace Health).
    try:
        from institutional_workspace.production import soft_slice_mission_control as rw_soft

        out["institutional_workspace"] = rw_soft()
        out["sources"].append("institutional_workspace")
    except Exception:
        out["institutional_workspace"] = None

    # CCI-01 — Cross-Company Intelligence (Relationship Center).
    try:
        from institutional_cross_company.production import soft_slice_mission_control as cci_soft

        out["institutional_cross_company"] = cci_soft()
        out["sources"].append("institutional_cross_company")
    except Exception:
        out["institutional_cross_company"] = None

    # PUB-01 — Publishing & Distribution (Publication Center).
    try:
        from institutional_publishing.production import soft_slice_mission_control as pub_soft

        out["institutional_publishing"] = pub_soft()
        out["sources"].append("institutional_publishing")
    except Exception:
        out["institutional_publishing"] = None

    # MPC-01 — Multi-Portfolio & Client Platform (Platform Operations Center).
    try:
        from institutional_multi_portfolio.production import soft_slice_mission_control as mpc_soft

        out["institutional_multi_portfolio"] = mpc_soft()
        out["sources"].append("institutional_multi_portfolio")
    except Exception:
        out["institutional_multi_portfolio"] = None

    # PRP-01 — Performance & Scale (Performance Center).
    try:
        from institutional_performance.production import soft_slice_mission_control as prp_soft

        out["institutional_performance"] = prp_soft()
        out["sources"].append("institutional_performance")
    except Exception:
        out["institutional_performance"] = None

    # PRP-02 — Security & Governance (Security Center).
    try:
        from institutional_security.production import soft_slice_mission_control as sec_soft

        out["institutional_security"] = sec_soft()
        out["sources"].append("institutional_security")
    except Exception:
        out["institutional_security"] = None

    # PRP-03 — Observability & Operations (Operations Center).
    try:
        from institutional_observability.production import soft_slice_mission_control as obs_soft

        out["institutional_observability"] = obs_soft()
        out["sources"].append("institutional_observability")
    except Exception:
        out["institutional_observability"] = None

    # RC-01 — Architecture Conformance (Architecture Center).
    try:
        from institutional_architecture.production import soft_slice_mission_control as rc_soft

        out["institutional_architecture"] = rc_soft()
        out["sources"].append("institutional_architecture")
    except Exception:
        out["institutional_architecture"] = None

    # L-01 — Launch Phase (Launch Center).
    try:
        from institutional_launch.production import soft_slice_mission_control as launch_soft

        out["institutional_launch"] = launch_soft()
        out["sources"].append("institutional_launch")
    except Exception:
        out["institutional_launch"] = None

    # PAT-01 — Production Acceptance Test (Acceptance Center).
    try:
        from institutional_acceptance.production import soft_slice_mission_control as pat_soft

        out["institutional_acceptance"] = pat_soft()
        out["sources"].append("institutional_acceptance")
    except Exception:
        out["institutional_acceptance"] = None

    # IEP-01 — Institutional Evidence Platform (Evidence Center).
    try:
        from institutional_evidence.production import soft_slice_mission_control as iep_soft

        out["institutional_evidence"] = iep_soft()
        out["sources"].append("institutional_evidence")
    except Exception:
        out["institutional_evidence"] = None

    # KIL-01 — Knowledge Health (CGL → KIL → IEP).
    try:
        from institutional_evidence.production import soft_slice_knowledge_health as kil_soft

        out["knowledge_health"] = kil_soft()
        out["sources"].append("knowledge_health")
    except Exception:
        out["knowledge_health"] = None

    # ICF-01 — Institutional Coverage Factory (companies → ICC).
    try:
        from institutional_coverage_factory.production import soft_slice_mission_control as icf_soft

        out["institutional_coverage_factory"] = icf_soft()
        out["sources"].append("institutional_coverage_factory")
    except Exception:
        out["institutional_coverage_factory"] = None

    # KOC-01 — Knowledge Operations Center (admin control room).
    try:
        from knowledge_operations.production import soft_slice_mission_control as koc_soft

        out["knowledge_operations"] = koc_soft()
        out["sources"].append("knowledge_operations")
    except Exception:
        out["knowledge_operations"] = None

    return out


def _platform_card(name: str, *, status: str = "Unknown", **extra: Any) -> dict[str, Any]:
    return {
        "name": name,
        "current_status": _status_norm(status),
        "last_run": extra.get("last_run"),
        "last_success": extra.get("last_success"),
        "last_failure": extra.get("last_failure"),
        "runtime": extra.get("runtime"),
        "average_response_time": extra.get("average_response_time"),
        "coverage": extra.get("coverage"),
        "knowledge_count": extra.get("knowledge_count"),
        "error_count": extra.get("error_count") or 0,
        "warnings": extra.get("warnings") or 0,
        "dependencies": extra.get("dependencies") or [],
        "health_score": extra.get("health_score"),
        "details": extra.get("details") or {},
        "read_only": True,
    }


def build_mission_control(*, ioc_service: Any | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {
            "enabled": False,
            "programme": PROGRAMME,
            "version": MISSION_CONTROL_VERSION,
            "bypassed": True,
            "read_only": True,
        }

    # Soft pulls — never raise into the cockpit
    ioc = {}
    if ioc_service is not None:
        try:
            from app.aws.adapters import dump, soft

            ioc = dump(soft(ioc_service.dashboard)) or {}
        except Exception:
            ioc = _soft(lambda: ioc_service.dashboard().model_dump(mode="json") if hasattr(ioc_service.dashboard(), "model_dump") else {})
    if not ioc:
        ioc = _soft(lambda: __import__("app.ioc.service", fromlist=["IocService"]).IocService().dashboard().model_dump(mode="json"))

    cms = _soft(lambda: __import__("company_monitor.production", fromlist=["dashboard"]).dashboard())
    io = _soft(lambda: __import__("investment_office.production", fromlist=["dashboard"]).dashboard())
    ca = _soft(lambda: __import__("company_analysis.production", fromlist=["dashboard"]).dashboard())
    books = _soft(lambda: __import__("academy.books.production", fromlist=["dashboard"]).dashboard())
    try:
        from company_monitor import store as cms_store

        cms_changes = list(cms_store.list_changes(limit=40) or [])
        cms_alerts = list(cms_store.list_alerts(40) or [])
        cms_reviews = list(cms_store.list_reviews(40) or [])
    except Exception:
        cms_changes, cms_alerts, cms_reviews = [], [], []

    dvc = _soft(lambda: __import__("dvc.production", fromlist=["production_dashboard"]).production_dashboard())
    if not dvc:
        dvc = _soft(lambda: __import__("dvc.production", fromlist=["dashboard"]).dashboard())
    ecp = _soft(lambda: __import__("ecp.production", fromlist=["production_dashboard"]).production_dashboard())
    if not ecp:
        ecp = _soft(lambda: __import__("ecp.production", fromlist=["dashboard"]).dashboard())

    leo_h = _soft(lambda: __import__("leo.production", fromlist=["health"]).health() if hasattr(__import__("leo.production", fromlist=["health"]), "health") else {})
    if not leo_h:
        leo_h = _soft(lambda: {"status": "soft", "programme": "LEO"})

    cid_h = _soft(lambda: __import__("cid.production", fromlist=["is_cid_enabled"]).is_cid_enabled())
    sif_h = _soft(lambda: __import__("sif.production", fromlist=["quality_gates"]).quality_gates())

    overall_ioc = _status_norm(ioc.get("overall_health") or ioc.get("status") or ioc.get("overall"))
    coverage = (io.get("coverage_dashboard") or cms.get("coverage") or {})
    knowledge = io.get("knowledge_growth") or {
        "books_learned": books.get("books_successfully_ingested"),
        "concepts_added": books.get("concept_count"),
        "frameworks_added": books.get("framework_count"),
        "companies_updated": (cms.get("metrics") or {}).get("companies_monitored"),
    }

    # SECTION 1 — Executive Status
    exec_status = {
        "agi_status": overall_ioc if overall_ioc != "Unknown" else ("Healthy" if is_enabled() else "Offline"),
        "research_grade": coverage.get("research_grade") or "B",
        "knowledge_grade": coverage.get("knowledge_grade") or "B",
        "data_grade": str(coverage.get("data_grade") or overall_ioc or "ok"),
        "coverage": coverage.get("coverage_pct") or (cms.get("coverage") or {}).get("financial_channel_pct") or 55,
        "system_confidence": None,
        "companies_covered": (cms.get("metrics") or {}).get("companies_monitored") or len(cms.get("companies_monitored") or []),
        "companies_monitored": (cms.get("metrics") or {}).get("companies_monitored") or 0,
        "questions_answered_today": None,
        "last_successful_learning": books.get("latest_ingestion_report", {}).get("books_version")
        if isinstance(books.get("latest_ingestion_report"), dict)
        else None,
        "last_deployment": None,
        "last_health_check": _now(),
        "sources": ["ioc", "investment_office", "company_monitor", "academy.books"],
    }

    # Soft Institutional Stack (FIL→FDI→MII→EIL→PIL) — additive platform cards
    stack_irs = _soft(
        lambda: __import__(
            "institutional_stack.production", fromlist=["soft_slice_for_mission_control"]
        ).soft_slice_for_mission_control()
    )
    stack_dash = _soft(
        lambda: __import__("institutional_stack.production", fromlist=["dashboard"]).dashboard()
    )
    stack_slice = (stack_irs or {}).get("institutional_stack") or {}
    stack_layers = (stack_dash or {}).get("layer_health") or {}

    # SECTION 2 — Platform Status
    ioc_platforms = ioc.get("platform_status") or {}
    platforms = [
        _platform_card("Knowledge Foundation", status=ioc_platforms.get("kip") or "soft", dependencies=["KIP"], health_score=70),
        _platform_card("CID", status="Healthy" if cid_h else "Warning", dependencies=["LEO", "SIF"], knowledge_count=None),
        _platform_card(
            "Academy",
            status="Healthy" if books.get("enabled", True) else "Offline",
            knowledge_count=books.get("concept_count"),
            coverage=books.get("coverage"),
            dependencies=["FAPI", "Books"],
            health_score=85 if books.get("concept_count") else 60,
        ),
        _platform_card("Financial Intelligence", status="soft", dependencies=["CID", "YFP", "DVC"]),
        _platform_card(
            "Company Analysis",
            status="Healthy" if ca.get("enabled", True) else "Offline",
            knowledge_count=(ca.get("metrics") or {}).get("reports"),
            dependencies=["CID", "Academy", "SIF"],
        ),
        _platform_card(
            "Company Monitor",
            status="Healthy" if cms.get("enabled", True) else "Offline",
            knowledge_count=(cms.get("metrics") or {}).get("change_events"),
            error_count=(cms.get("metrics") or {}).get("critical_alerts") or 0,
            dependencies=["LEO", "CID", "Company Analysis"],
        ),
        _platform_card(
            "Investment Office",
            status="Healthy" if io.get("enabled", True) else "Offline",
            dependencies=["CMS", "CA", "IOC", "Academy"],
            health_score=80,
        ),
        _platform_card("KIP", status=ioc_platforms.get("kip") or "soft", dependencies=["store"]),
        _platform_card("RSP", status=ioc_platforms.get("rsp") or "soft"),
        _platform_card("RMS", status=ioc_platforms.get("rms") or "soft"),
        _platform_card("IOC", status=overall_ioc, dependencies=["engines", "providers"]),
        _platform_card("DVC", status="Healthy" if (dvc.get("enabled") is not False) else "Offline", details=dvc.get("metrics") or dvc),
        _platform_card("ECP", status="Healthy" if (ecp.get("enabled") is not False) else "Offline", details=ecp.get("metrics") or ecp),
        _platform_card("Ask AGI", status="soft", dependencies=["IRP", "CAE", "IO", "CMS"]),
        _platform_card(
            "Filing Intelligence",
            status="Healthy" if (stack_layers.get("filing_intelligence") or {}).get("enabled", True) else "Offline",
            dependencies=["Official Filings"],
            details=stack_layers.get("filing_intelligence") or {},
        ),
        _platform_card(
            "Filing Diff",
            status="Healthy" if (stack_layers.get("filing_diff") or {}).get("enabled", True) else "Offline",
            dependencies=["FIL"],
            details=stack_layers.get("filing_diff") or {},
        ),
        _platform_card(
            "Management Intelligence",
            status="Healthy" if (stack_layers.get("management_intelligence") or {}).get("enabled", True) else "Offline",
            dependencies=["FIL", "FDI"],
            details=stack_layers.get("management_intelligence") or {},
        ),
        _platform_card(
            "Accounting Intelligence",
            status="Healthy" if (stack_layers.get("accounting_intelligence") or {}).get("enabled", True) else "Offline",
            dependencies=["FIL", "FDI", "MII"],
            details=stack_layers.get("accounting_intelligence") or {},
        ),
        _platform_card(
            "Portfolio Intelligence",
            status="Healthy" if (stack_layers.get("portfolio_intelligence") or {}).get("enabled", True) else "Offline",
            dependencies=["Investment Committee", "MII", "ACI"],
            details=stack_layers.get("portfolio_intelligence") or {},
        ),
        _platform_card(
            "Peer Intelligence",
            status="Healthy" if (stack_layers.get("peer_intelligence") or {}).get("enabled", True) else "Offline",
            dependencies=["FIL"],
            details=stack_layers.get("peer_intelligence") or {},
        ),
        _platform_card(
            "Evidence Intelligence",
            status="Healthy" if (stack_layers.get("evidence_intelligence") or {}).get("enabled", True) else "Offline",
            dependencies=["FIL", "PIL"],
            details=stack_layers.get("evidence_intelligence") or {},
        ),
        _platform_card(
            "Institutional Stack",
            status="Healthy" if stack_slice.get("enabled", True) else "Offline",
            dependencies=["FIL", "FDI", "MII", "ACI", "PIO", "EIL", "PIL"],
            knowledge_count=stack_slice.get("seed_documents"),
            details=stack_slice,
        ),
    ]

    # SECTION 3 — Engine Status
    engine_status = ioc.get("engine_status") or {}
    engines = []
    for name in ("LEO", "IRP", "RSP", "KIP", "DVC", "ECP", "Financial Intelligence", "Company Analysis", "Company Monitor", "Investment Office"):
        key = name.lower().replace(" ", "_")
        st = engine_status.get(key) or engine_status.get(name.lower())
        if name == "LEO":
            st = st or leo_h.get("status") or "soft"
        if name == "Company Monitor":
            st = "Healthy" if cms.get("enabled", True) else "Disabled"
        if name == "Company Analysis":
            st = "Healthy" if ca.get("enabled", True) else "Disabled"
        if name == "Investment Office":
            st = "Healthy" if io.get("enabled", True) else "Disabled"
        engines.append(
            {
                "name": name,
                "status": _status_norm(st or "soft"),
                "last_execution": None,
                "execution_time": None,
                "queue": None,
                "failures": 0,
                "retries": 0,
                "memory_usage": None,
                "cpu_usage": None,
                "read_only": True,
            }
        )

    # SECTION 4 — API / Provider Status
    providers = []
    for p in ioc.get("provider_health") or ioc.get("providers") or []:
        if not isinstance(p, dict):
            # pydantic dump may already be dict
            try:
                p = p.model_dump(mode="json") if hasattr(p, "model_dump") else {"provider_id": str(p), "status": "unknown"}
            except Exception:
                p = {"provider_id": str(p), "status": "unknown"}
        configured = p.get("configured")
        # Missing keys are "Not configured", not a live outage.
        if configured is False:
            st = "Not configured"
        else:
            st = _status_norm(p.get("status"))
        colour = (
            "Green"
            if st == "Healthy"
            else "Yellow"
            if st in {"Warning", "Unknown", "Not Configured", "Not configured"}
            else "Red"
        )
        providers.append(
            {
                "name": p.get("provider_id") or p.get("name") or "provider",
                "status": st,
                "colour": colour,
                "latency": p.get("latency"),
                "requests_today": None,
                "success_rate": None,
                "failure_rate": None,
                "last_error": p.get("last_error"),
                "rate_limit": None,
                "quota_usage": None,
                "remaining_quota": None,
                "last_successful_request": None,
                "average_response_time": None,
                "provider_confidence": "configured" if configured else "missing_key" if configured is False else "unknown",
                "circuit_state": p.get("circuit_state"),
                "capabilities": p.get("capabilities") or [],
                "configured": configured,
                "note": None if configured is not False else "API key not set on intelligence engine",
            }
        )
    # Ensure named providers appear even if IOC sparse.
    # Includes Groww + other .env market/macro/news APIs so Mission Control
    # surfaces the full external dependency catalogue (soft placeholders until probed).
    known = {p["name"].lower() for p in providers}
    # Soft overlay: Forecast Provider Integration (India-first) health
    fpi_rows: list[dict[str, Any]] = []
    try:
        from forecast_provider_integration.production import provider_health as fpi_health

        fpi = fpi_health()
        for row in fpi.get("providers") or []:
            name = str(row.get("provider") or "").lower()
            label_map = {
                "groww": "Groww",
                "yahoo": "Yahoo Finance",
                "nse": "NSE",
                "bse": "BSE",
                "company_ir": "Company IR",
            }
            label = label_map.get(name, name.title())
            st = _status_norm(row.get("status"))
            colour = "Green" if st == "Healthy" else "Yellow" if st in {"Warning", "Degraded"} else "Red"
            fpi_rows.append(
                {
                    "name": label,
                    "status": st if st != "Degraded" else "Warning",
                    "colour": colour if st != "Degraded" else "Yellow",
                    "latency": row.get("latency_ms") or row.get("websocket_latency_ms"),
                    "last_error": None,
                    "provider_confidence": "configured" if row.get("configured") else "seeded",
                    "capabilities": [row.get("role")] if row.get("role") else [],
                    "note": row.get("detail"),
                    "snapshot_freshness_sec": row.get("snapshot_freshness_sec"),
                    "source": "forecast_provider_integration",
                }
            )
    except Exception:
        fpi_rows = []

    for row in fpi_rows:
        lname = row["name"].lower()
        # Replace placeholder / update existing
        replaced = False
        for i, p in enumerate(providers):
            if p["name"].lower() == lname or (
                lname == "yahoo finance" and "yahoo" in p["name"].lower()
            ):
                providers[i] = {**p, **row}
                replaced = True
                break
        if not replaced:
            providers.append(row)
            known.add(lname)

    for label in (
        "Groww",
        "Yahoo Finance",
        "NSE",
        "BSE",
        "Company IR",
        "Indian API",
        "Finnhub",
        "FMP",
        "Alpha Vantage",
        "FRED",
        "Twelve Data",
        "Polygon",
        "NewsAPI",
        "Perplexity",
        "OpenAI",
        "Supabase",
        "Resend",
        "SendGrid",
        "RBI Data",
        "ExchangeRate",
        "Render",
        "Hostinger",
        "SMTP",
        "Email",
        "GitHub",
        "Scheduler",
        "Redis",
    ):
        if label.lower() not in known:
            providers.append(
                {
                    "name": label,
                    "status": "Unknown",
                    "colour": "Yellow",
                    "latency": None,
                    "last_error": None,
                    "provider_confidence": "not_probed",
                    "note": "Soft placeholder — IOC / Node provider probe when configured",
                }
            )
            known.add(label.lower())

    # SECTION 5 — Knowledge Growth
    # research_learned / last_5_days_* are soft-enriched by Node from CMS learn events.
    knowledge_growth = {
        "windows": ["Last Hour", "Last 24 Hours", "Last 5 Days", "Last 7 Days"],
        "research_learned": None,
        "companies_updated": knowledge.get("companies_updated"),
        "books_learned": knowledge.get("books_learned") or books.get("books_successfully_ingested"),
        "concepts_added": knowledge.get("concepts_added") or books.get("concept_count"),
        "frameworks_added": knowledge.get("frameworks_added") or books.get("framework_count"),
        "formulas_added": knowledge.get("formulas_added") or books.get("formula_count"),
        "financial_statements_updated": None,
        "valuation_updates": None,
        "research_notes": None,
        "cid_updates": None,
        "knowledge_foundation_updates": None,
        "prediction_evaluations": None,
        "house_view_reviews": len(cms_reviews),
        "last_5_days_summary": None,
        "last_5_days_highlights": [],
        "last_5_days": [],
        "sources": [
            "academy.books",
            "company_monitor",
            "investment_office",
            "cms_article_learning",
            "research_intelligence_hub",
            "financial_data_operations",
        ],
    }

    # SECTION 6 — Coverage (+ soft Institutional Intelligence from Sprints 1–7)
    institutional = _soft_institutional_intelligence()
    rih_board = institutional.get("research_intelligence_hub") or {}
    if rih_board.get("hub_count") is not None:
        knowledge_growth["research_notes"] = rih_board.get("hub_count")
    fdo_board = institutional.get("financial_data_operations") or {}
    if fdo_board.get("raw_evidence_files") is not None:
        knowledge_growth["financial_statements_updated"] = fdo_board.get("raw_evidence_files")
    dc = institutional.get("decision_coverage") or {}
    coverage_dash = {
        "overall_coverage": dc.get("nifty_100") or coverage.get("coverage_pct") or exec_status["coverage"],
        "nifty_50": dc.get("nifty_50"),
        "nifty_next_50": None,
        "nifty_100": dc.get("nifty_100"),
        "nifty_500": dc.get("nifty_500"),
        "target_20": dc.get("target_20"),
        "us_coverage": None,
        "sector_coverage": (institutional.get("sector_intelligence") or {}).get("sector_coverage_pct")
        or coverage.get("sector_coverage"),
        "company_coverage": exec_status["companies_covered"],
        "research_coverage": coverage.get("research_coverage"),
        "academy_coverage": coverage.get("academy_coverage"),
        "financial_coverage": coverage.get("financial_coverage") or (cms.get("coverage") or {}).get("financial_channel_pct"),
        "valuation_coverage": coverage.get("valuation_coverage"),
        "prediction_coverage": None,
        "historical_depth": institutional.get("historical_depth"),
        "macro_intelligence": institutional.get("macro_intelligence"),
        "decision_quality": institutional.get("decision_quality"),
        "roadmap_next": institutional.get("roadmap_next"),
        "below_threshold": coverage.get("below_threshold") or cms_reviews[:10],
        "sources": [
            "investment_office",
            "company_monitor",
            "knowledge_factory.coverage",
            "historical_depth",
            "sector_intelligence",
            "macro_intelligence",
            "decision_quality",
            "evidence_retrieval",
        ],
        "institutional_intelligence": institutional,
        "evidence_retrieval": institutional.get("evidence_retrieval"),
    }

    # SECTION 7 — Company Monitor
    company_monitor = {
        "companies_monitored": (cms.get("metrics") or {}).get("companies_monitored") or 0,
        "critical_alerts": len([a for a in cms_alerts if a.get("significance") == "Critical"]),
        "high_alerts": len([a for a in cms_alerts if a.get("significance") == "High"]),
        "medium_alerts": len([a for a in cms_alerts if a.get("significance") == "Medium"]),
        "low_alerts": len([a for a in cms_alerts if a.get("significance") == "Low"]),
        "companies_needing_review": len(cms_reviews),
        "companies_updated_today": len(cms.get("companies_monitored") or []),
        "latest_company_changes": cms_changes[:20],
        "latest_earnings_processed": [c for c in cms_changes if "revenue" in str(c.get("change_type") or "")][:10],
        "latest_filings_processed": [],
        "sources": ["company_monitor"],
    }

    # SECTION 8 — Research Pipeline
    research_pipeline = {
        **(ioc.get("research_pipeline") or {}),
        "research_drafts": list(ioc.get("publication_queue") or [])[:20],
        "internal_review": [],
        "compliance_review": [],
        "approved": [],
        "publishing_today": (io.get("research_pipeline") or {}).get("publishing_today") or [],
        "published_today": (io.get("research_pipeline") or {}).get("recently_published") or [],
        "failed_publishing": [],
        "research_queue": io.get("todays_research_queue") or [],
        "sources": ["ioc", "rms", "investment_office"],
    }

    # SECTION 9 — Predictions
    pred = io.get("prediction_review") or {}
    prediction_intelligence = {
        "predictions_created": len(pred.get("predictions_due") or []),
        "predictions_due": pred.get("predictions_due") or [],
        "predictions_correct": pred.get("predictions_correct") or [],
        "predictions_incorrect": pred.get("predictions_incorrect") or [],
        "prediction_accuracy": pred.get("prediction_accuracy"),
        "confidence_trend": pred.get("confidence_changes") or [],
        "house_view_reviews": pred.get("house_view_reviews_required") or cms_reviews,
        "sources": ["investment_office", "company_monitor"],
    }

    # SECTION 10 — Data Quality
    data_quality = {
        "research_grade": exec_status["research_grade"],
        "knowledge_grade": exec_status["knowledge_grade"],
        "market_data_grade": _status_norm((ioc.get("data_freshness") or {}).get("market_data")),
        "financial_statement_grade": None,
        "valuation_grade": None,
        "sector_intelligence_grade": "pass" if (sif_h or {}).get("passed") else "soft",
        "academy_grade": "B" if books.get("concept_count") else "C",
        "evidence_quality": None,
        "average_confidence": None,
        "missing_data": coverage_dash.get("below_threshold") or [],
        "dvc": dvc.get("metrics") or dvc,
        "ecp": ecp.get("metrics") or ecp,
        "sources": ["ioc", "dvc", "ecp", "sif", "academy"],
    }

    # SECTION 11 — Company Analysis
    ca_reports = ca.get("latest_reports") or []
    company_analysis = {
        "companies_analysed": (ca.get("metrics") or {}).get("reports") or len(ca_reports),
        "financial_intelligence_complete": None,
        "business_quality_complete": sum(1 for r in ca_reports if r.get("business_quality_score") is not None),
        "valuation_complete": None,
        "sector_intelligence_complete": None,
        "bull_base_bear_generated": None,
        "recommendation_readiness": [r.get("gate") for r in ca_reports][:12],
        "companies_missing_analysis": [],
        "latest_reports": ca_reports[:12],
        "sources": ["company_analysis"],
    }

    # SECTION 12 — Academy
    academy = {
        "books": books.get("books_successfully_ingested") or len(books.get("books") or []),
        "courses": None,
        "concepts": books.get("concept_count"),
        "frameworks": books.get("framework_count"),
        "formulas": books.get("formula_count"),
        "knowledge_objects": (books.get("concept_count") or 0)
        + (books.get("framework_count") or 0)
        + (books.get("formula_count") or 0),
        "graph_nodes": books.get("concept_count"),
        "graph_relationships": books.get("graph_edges"),
        "recently_learned": [
            b.get("title")
            for b in (books.get("books") or [])
            if (b or {}).get("source_format") != "seed"
        ][:12],
        "most_used_concepts": books.get("most_used_concepts") or [],
        "most_referenced_frameworks": [],
        "sources": ["academy.books"],
    }

    # SECTION 13 — CID
    cid = {
        "company_dossiers": "soft",
        "updated_today": None,
        "coverage": "see CID admin",
        "average_confidence": None,
        "documents": None,
        "timelines": None,
        "financial_histories": None,
        "valuation_histories": None,
        "knowledge_links": None,
        "companies_missing_cid": [],
        "enabled": bool(cid_h),
        "sources": ["cid"],
    }

    # SECTION 14 — System Health
    system_health = {
        "frontend": "soft",
        "backend": "soft",
        "fastapi": overall_ioc,
        "database": "soft",
        "authentication": "soft",
        "email": "soft",
        "scheduler": "soft",
        "storage": "soft",
        "background_jobs": "soft",
        "queue": (ioc.get("pipeline_status") or {}),
        "cache": "soft",
        "memory": None,
        "cpu": None,
        "disk": None,
        "network": None,
        "ioc": ioc,
        "components": ioc.get("components") or [],
        "sources": ["ioc"],
        "note": "Deep infra metrics soft — IOC is system-of-record for ops probes",
    }

    # SECTION 15 — Live Event Stream
    events = []
    for c in cms_changes[:15]:
        events.append(
            {
                "at": c.get("detected_at") or _now(),
                "type": "company_change",
                "message": f"{c.get('ticker')}: {c.get('detail') or c.get('change_type')}",
                "significance": c.get("significance"),
                "ref": c,
            }
        )
    if books.get("concept_count"):
        events.append(
            {
                "at": _now(),
                "type": "academy",
                "message": f"Academy knowledge objects: {books.get('concept_count')} concepts / {books.get('framework_count')} frameworks",
            }
        )
    for r in cms_reviews[:5]:
        events.append(
            {
                "at": r.get("suggested_at") or _now(),
                "type": "house_view_review",
                "message": f"{r.get('ticker')}: House View review suggested",
                "ref": r,
            }
        )
    for fail in (ioc.get("latest_failures") or [])[:8]:
        if isinstance(fail, dict):
            events.append(
                {
                    "at": fail.get("checked_at") or _now(),
                    "type": "ioc_failure",
                    "message": f"{fail.get('component')}: {fail.get('status')}",
                    "ref": fail,
                }
            )
    events.sort(key=lambda e: str(e.get("at") or ""), reverse=True)

    # SECTION 16 — Executive Copilot
    unhealthy_apis = [p for p in providers if p.get("status") in {"Critical", "Offline", "Warning"}]
    attention = io.get("companies_requiring_attention") or []
    answers = {
        COPILOT_PROMPTS[0]: f"{len(ioc.get('latest_failures') or [])} IOC failure/warning components; CMS critical={company_monitor['critical_alerts']}.",
        COPILOT_PROMPTS[1]: f"{len(unhealthy_apis)} providers not Healthy (incl. soft unknowns).",
        COPILOT_PROMPTS[2]: f"{len(attention)} companies on IO attention list; {company_monitor['companies_needing_review']} HV reviews.",
        COPILOT_PROMPTS[3]: f"Books learned={knowledge_growth['books_learned']}; concepts={knowledge_growth['concepts_added']}; HV reviews={knowledge_growth['house_view_reviews']}.",
        COPILOT_PROMPTS[4]: "See Platform Status error_count / IOC latest_failures for highest-error surfaces.",
        COPILOT_PROMPTS[5]: f"Research queue length={len(research_pipeline.get('research_queue') or [])}.",
        COPILOT_PROMPTS[6]: "Research Grade is aggregated from IO coverage — investigate RMS queues and published counts.",
        COPILOT_PROMPTS[7]: "Inspect provider latency / circuit_state in API Status (IOC provider probes).",
        COPILOT_PROMPTS[8]: f"AGI status={exec_status['agi_status']}; coverage={exec_status['coverage']}%; monitored={exec_status['companies_monitored']}; events={len(events)}.",
    }
    copilot = {"prompts": list(COPILOT_PROMPTS), "answers": answers, "read_only": True}

    # SECTION 17 — Architecture Map
    node_status = {
        "Providers": _status_norm(overall_ioc),
        "MarketDataClient": _status_norm((ioc.get("platform_status") or {}).get("market_data")),
        "DVC": _platform_card("DVC", status="Healthy" if dvc else "Unknown")["current_status"],
        "ECP": _platform_card("ECP", status="Healthy" if ecp else "Unknown")["current_status"],
        "LEO": _status_norm(leo_h.get("status") or "soft"),
        "CID": "Healthy" if cid_h else "Warning",
        "Knowledge Foundation": _status_norm((ioc.get("platform_status") or {}).get("kip")),
        "Evidence Retrieval": (
            "Healthy"
            if (institutional.get("evidence_retrieval") or {}).get("status") == "ok"
            else "Warning"
            if institutional.get("evidence_retrieval")
            else "Unknown"
        ),
        "Macro Intelligence": (
            "Healthy"
            if (institutional.get("macroeconomic_forecast_intelligence") or {}).get("status") == "ok"
            or (institutional.get("continuous_macro_knowledge") or {}).get("status") == "ok"
            else "Warning"
            if institutional.get("macroeconomic_forecast_intelligence")
            or institutional.get("continuous_macro_knowledge")
            else "Unknown"
        ),
        "Sector Intelligence": (
            "Healthy"
            if (institutional.get("sector_forecast_intelligence") or {}).get("status") == "ok"
            else "Warning"
            if institutional.get("sector_forecast_intelligence")
            else "Unknown"
        ),
        "Market Intelligence": (
            "Healthy"
            if (institutional.get("market_forecast_intelligence") or {}).get("status") == "ok"
            or (institutional.get("continuous_market_knowledge") or {}).get("status") == "ok"
            else "Warning"
            if institutional.get("market_forecast_intelligence")
            or institutional.get("continuous_market_knowledge")
            else "Unknown"
        ),
        "Research Intelligence Hub": (
            "Healthy"
            if (institutional.get("research_intelligence_hub") or {}).get("status") == "ok"
            else "Warning"
            if institutional.get("research_intelligence_hub")
            else "Unknown"
        ),
        "Institutional Intelligence Examination": (
            "Healthy"
            if (institutional.get("institutional_intelligence_examination") or {}).get("status") == "ok"
            else "Warning"
            if institutional.get("institutional_intelligence_examination")
            else "Unknown"
        ),
        "Academy": "Healthy" if books.get("enabled", True) else "Offline",
        "Financial Intelligence": "soft",
        "Company Analysis": "Healthy" if ca.get("enabled", True) else "Offline",
        "Company Monitor": "Healthy" if cms.get("enabled", True) else "Offline",
        "Investment Office": "Healthy" if io.get("enabled", True) else "Offline",
        "IRP": "soft",
        "Ask AGI": "soft",
    }
    def _node_id(label: str) -> str:
        return label.lower().replace(" ", "_").replace("/", "_")

    architecture_map = {
        "nodes": [
            {
                "id": _node_id(n),
                "label": n,
                "status": node_status.get(n, "Unknown"),
                "colour": "Green"
                if node_status.get(n) == "Healthy"
                else "Yellow"
                if node_status.get(n) in {"Warning", "Unknown", "soft", "Soft"}
                else "Red",
                "health": node_status.get(n, "Unknown"),
                "dependencies": [],
                "performance": None,
                "coverage": None,
                "logs": [],
            }
            for n in ARCHITECTURE_NODES
        ],
        "edges": [
            {
                "from": _node_id(ARCHITECTURE_NODES[i]),
                "to": _node_id(ARCHITECTURE_NODES[i + 1]),
            }
            for i in range(len(ARCHITECTURE_NODES) - 1)
        ],
        "read_only": True,
    }

    # SECTION 18 — Alerts Centre
    ack = mc_store.acknowledged_ids()
    alerts = []
    for a in cms_alerts:
        aid = f"cms:{a.get('ticker')}:{a.get('change_type')}:{a.get('detected_at')}"
        alerts.append(
            {
                "id": aid,
                "category": "Critical Alerts" if a.get("significance") == "Critical" else "System Alerts",
                "message": a.get("detail") or a.get("change_type"),
                "ticker": a.get("ticker"),
                "significance": a.get("significance"),
                "acknowledged": aid in ack,
            }
        )
    for r in cms_reviews:
        aid = f"hvr:{r.get('ticker')}:{r.get('suggested_at')}"
        alerts.append(
            {
                "id": aid,
                "category": "Prediction Alerts",
                "message": r.get("action") or "House View review",
                "ticker": r.get("ticker"),
                "acknowledged": aid in ack,
            }
        )
    for fail in (ioc.get("alerts") or [])[:20]:
        if isinstance(fail, dict):
            aid = f"ioc:{fail.get('id') or fail.get('component') or fail.get('message')}"
            alerts.append(
                {
                    "id": aid,
                    "category": "API Alerts",
                    "message": fail.get("message") or fail.get("title") or str(fail)[:160],
                    "acknowledged": aid in ack,
                }
            )

    # SECTION 19 — Deployment Centre
    deployment = {
        "current_version": MISSION_CONTROL_VERSION,
        "git_commit": None,
        "current_branch": None,
        "last_deployment": None,
        "deployment_duration": None,
        "rollback_available": None,
        "environment": "development",
        "note": "Populate from deploy metadata when available — read-only",
        "sources": ["mission_control"],
    }
    try:
        import subprocess

        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, timeout=2).strip()
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, timeout=2).strip()
        deployment["current_branch"] = branch
        deployment["git_commit"] = commit
    except Exception:
        pass

    # SECTION 20 — Performance Analytics (soft placeholders + whatever IOC has)
    performance = {
        "average_api_response": None,
        "average_ask_agi_response": None,
        "average_research_generation_time": None,
        "average_company_analysis_time": None,
        "average_cid_refresh_time": None,
        "average_learning_time": None,
        "daily_questions": None,
        "daily_learning": knowledge_growth.get("concepts_added"),
        "daily_research": len(research_pipeline.get("published_today") or []),
        "charts": {"hours_24": [], "days_7": [], "days_30": []},
        "sources": ["ioc", "soft"],
        "note": "Detailed perf series reserved — no fabricated charts",
    }

    desk = {
        "enabled": True,
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": MISSION_CONTROL_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "read_only": True,
        "never_modifies_research": True,
        "never_changes_house_views": True,
        "never_changes_recommendations": True,
        "not_an_engine": True,
        "not_client_facing": True,
        "flags": flags_dict(),
        "generated_at": _now(),
        "platforms_catalog": list(PLATFORMS),
        "executive_status": exec_status,
        "platform_status": platforms,
        "engine_status": engines,
        "api_status": providers,
        "knowledge_growth": knowledge_growth,
        "coverage_dashboard": coverage_dash,
        "company_monitor": company_monitor,
        "research_pipeline": research_pipeline,
        "prediction_intelligence": prediction_intelligence,
        "data_quality": data_quality,
        "company_analysis": company_analysis,
        "academy": academy,
        "cid": cid,
        "system_health": system_health,
        "live_event_stream": events[:40],
        "executive_copilot": copilot,
        "architecture_map": architecture_map,
        "alerts_centre": alerts[:60],
        "deployment_centre": deployment,
        "performance_analytics": performance,
        "continuous_gather_learn": (institutional or {}).get("continuous_gather_learn"),
        "answer_policy": "mission_control_read_only_diagnostics",
    }
    return desk
