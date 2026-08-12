"""CID production bridge — soft adapters for locked engines (no redesign)."""

from __future__ import annotations

from typing import Any

from cid.coverage import compute_coverage
from cid.ingest import ensure_dossier, ingest_leo_evidence
from cid.schema import CID_VERSION
from cid.store import get_cid_store


TRACKED_TICKERS = (
    "HDFCBANK",
    "INFY",
    "RELIANCE",
    "ULTRACEMCO",
    "ASIANPAINT",
    "TATASTEEL",
    "SUNPHARMA",
    "POWERGRID",
)


def is_cid_enabled() -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), "cid", True))
    except Exception:
        return True


def get_dossier(ticker: str) -> dict[str, Any]:
    if not is_cid_enabled():
        return {"enabled": False, "cid_version": CID_VERSION, "bypassed": True}
    t = (ticker or "").upper()
    d = get_cid_store().get(t)
    if not d:
        d = ensure_dossier(t)
    return {**d, "enabled": True}


def generate_openai_dossier(ticker: str, *, refresh_evidence: bool = True) -> dict[str, Any]:
    """Build the factual dossier, then add an evidence-only OpenAI research layer."""
    t = (ticker or "").strip().upper()
    if not t:
        return {"ok": False, "error": "ticker_required"}
    dossier = get_or_build(t, query=f"Build a full institutional company dossier for {t}") if refresh_evidence else get_dossier(t)
    from cid.openai_dossier import generate

    return generate(t, dossier)


def get_or_build(
    ticker: str | None,
    *,
    query: str | None = None,
    leo_pkg: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    forecast_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Primary Ask AGI / CAE entry — always prefer living dossier over raw APIs."""
    if not is_cid_enabled():
        return {"enabled": False, "cid_version": CID_VERSION, "bypassed": True, "answer_policy": "cid_disabled"}

    t = (ticker or (leo_pkg or {}).get("ticker") or "").upper() or None
    if not t:
        return {
            "enabled": True,
            "cid_version": CID_VERSION,
            "ticker": None,
            "reason": "no_ticker",
            "answer_policy": "dossier_before_raw_apis",
        }

    # Prefer LEO-driven ingest when fresh evidence is present
    if isinstance(leo_pkg, dict) and leo_pkg.get("evidence_objects"):
        dossier = ingest_leo_evidence(
            t,
            leo_pkg.get("evidence_objects") or [],
            plan=leo_pkg.get("evidence_plan") or {"ticker": t, "query": query, "company": (leo_pkg.get("entity") or {}).get("company")},
            finance_academy=finance_academy
            if isinstance(finance_academy, dict)
            else (leo_pkg.get("finance_academy") if isinstance(leo_pkg.get("finance_academy"), dict) else None),
            sif_pkg=sif_pkg
            if isinstance(sif_pkg, dict)
            else (
                leo_pkg.get("sector_intelligence")
                if isinstance(leo_pkg.get("sector_intelligence"), dict)
                else None
            ),
            valuation_pack=valuation_pack,
            forecast_pack=forecast_pack,
        )
    else:
        dossier = ensure_dossier(t, query=query)
        if finance_academy or sif_pkg:
            dossier = ingest_leo_evidence(
                t,
                [],
                plan={"ticker": t, "query": query},
                finance_academy=finance_academy,
                sif_pkg=sif_pkg,
                valuation_pack=valuation_pack,
                forecast_pack=forecast_pack,
            )

    # YFP V1 — secondary Yahoo enrichment (fill empties only; never overwrite institutional data)
    try:
        from app.core.config import get_settings
        from yfp.enrich import merge_yahoo_into_dossier
        from yfp.production import enrich_ticker, is_cid_enrichment_enabled
        from cid.coverage import compute_coverage
        from cid.store import get_cid_store

        if is_cid_enrichment_enabled() and bool(getattr(get_settings(), "yahoo_provider", True)):
            # Never block Ask on Yahoo — strict ceiling; CMS/KIP evidence continues.
            # Use a private executor (not Ask's shared pool) to avoid nested-timeout deadlocks.
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

            from app.ui.timeouts import ask_slim_enabled

            if ask_slim_enabled():
                # ASK_SLIM: skip live Yahoo CID fan-out (META.NS storms were hanging Tier A).
                ypack = {"enabled": False, "bypassed": True, "reason": "ask_slim"}
            else:
                with ThreadPoolExecutor(max_workers=1, thread_name_prefix="cid-yfp") as ex:
                    fut = ex.submit(enrich_ticker, t)
                    try:
                        ypack = fut.result(timeout=6.0)
                    except FuturesTimeout:
                        ypack = {"enabled": False, "timeout": True}
                ypack = ypack if isinstance(ypack, dict) else {"enabled": False}
            if ypack.get("enabled") and (
                ypack.get("quote")
                or ypack.get("fundamentals")
                or ypack.get("financial_history")
                or ypack.get("valuation_snapshot")
            ):
                dossier = merge_yahoo_into_dossier(dossier, ypack)
                cov = compute_coverage(dossier)
                dossier.update(
                    {
                        "coverage": cov["coverage"],
                        "coverage_score": cov["coverage_score"],
                        "coverage_grade": cov["coverage_grade"],
                        "missing_evidence": cov["missing_evidence"],
                    }
                )
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # Academy Books — soft CID learning enrichment (concepts/frameworks/formulas; no verbatim text)
    try:
        from academy.books.production import soft_enrich_cid
        from cid.store import get_cid_store

        dossier = soft_enrich_cid(dossier, ticker=t)
        dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # DVC V1 — attach validated field metadata / consensus (soft; no LEO redesign)
    try:
        from app.core.config import get_settings
        from dvc.enrich import merge_dvc_into_dossier
        from dvc.production import is_dvc_enabled, package_for_ask_agi as dvc_package
        from cid.coverage import compute_coverage
        from cid.store import get_cid_store

        if is_dvc_enabled() and bool(getattr(get_settings(), "dvc_auto_attach_cid", True)):
            dvc_pack = dvc_package(t)
            if dvc_pack.get("enabled") and dvc_pack.get("validated_fields"):
                dossier = merge_dvc_into_dossier(dossier, dvc_pack)
                cov = compute_coverage(dossier)
                dossier.update(
                    {
                        "coverage": cov["coverage"],
                        "coverage_score": cov["coverage_score"],
                        "coverage_grade": cov["coverage_grade"],
                        "missing_evidence": cov["missing_evidence"],
                    }
                )
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # P2.3 Ownership Intelligence — NSE Master + XBRL (fill ownership evidence; never fabricate)
    try:
        from ownership_intelligence.enrich import merge_ownership_into_dossier
        from ownership_intelligence.production import analyse as ownership_analyse
        from cid.store import get_cid_store

        existing = dossier.get("ownership") if isinstance(dossier.get("ownership"), dict) else {}
        already = existing.get("fii") is not None or existing.get("promoter") is not None
        if not already:
            opack = ownership_analyse(t, xbrl_quarters=1, persist=False)
            if opack.get("ok"):
                dossier = merge_ownership_into_dossier(dossier, opack)
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # P2.1 Earnings / Financial Statements — NSE integrated + IND-AS XBRL
    try:
        from earnings_intelligence.enrich import merge_financials_into_dossier
        from earnings_intelligence.production import analyse as earnings_analyse
        from cid.coverage import compute_coverage
        from cid.store import get_cid_store

        fs = dossier.get("financial_statements") or {}
        inc = fs.get("income_statement") or {}
        already_fs = bool((inc.get("quarterly") or []) or (inc.get("annual") or []))
        fin = dossier.get("financials") if isinstance(dossier.get("financials"), dict) else {}
        already_fin = fin.get("revenue") is not None or float(fin.get("coverage_pct") or 0) >= 80
        if not already_fs and not already_fin:
            epack = earnings_analyse(t, quarterly_xbrl=4, annual_xbrl=2, persist=False)
            if epack.get("ok"):
                dossier = merge_financials_into_dossier(dossier, epack)
                cov = compute_coverage(dossier)
                dossier.update(
                    {
                        "coverage": cov["coverage"],
                        "coverage_score": cov["coverage_score"],
                        "coverage_grade": cov["coverage_grade"],
                        "missing_evidence": cov["missing_evidence"],
                    }
                )
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # P2.2 Valuation Intelligence — synthesise peers + multiples + history (no BUY/SELL)
    try:
        from valuation_intelligence.enrich import merge_valuation_into_dossier
        from valuation_intelligence.production import analyse as valuation_analyse
        from cid.coverage import compute_coverage
        from cid.store import get_cid_store

        existing_val = dossier.get("valuation") if isinstance(dossier.get("valuation"), dict) else {}
        already_val = existing_val.get("engine") == "valuation_intelligence" or (
            existing_val.get("pe") is not None
            and existing_val.get("peer_pe") is not None
            and existing_val.get("placeholder") is not True
        )
        vi = dossier.get("valuation_intelligence") if isinstance(dossier.get("valuation_intelligence"), dict) else {}
        already_vi = bool(vi.get("ok") and float(vi.get("coverage_pct") or 0) >= 40)
        if not already_val and not already_vi:
            vpack = valuation_analyse(t, max_peers=4, persist=False)
            if vpack.get("ok"):
                dossier = merge_valuation_into_dossier(dossier, vpack)
                cov = compute_coverage(dossier)
                dossier.update(
                    {
                        "coverage": cov["coverage"],
                        "coverage_score": cov["coverage_score"],
                        "coverage_grade": cov["coverage_grade"],
                        "missing_evidence": cov["missing_evidence"],
                    }
                )
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # P3.1 Knowledge Delta Engine — incremental CompanyMemory (never silent overwrite)
    try:
        from company_memory.enrich import merge_memory_into_dossier
        from company_memory.from_dossier import injected_from_dossier
        from knowledge_delta_engine.compile import incremental_compile
        from cid.store import get_cid_store

        already_mem = isinstance(dossier.get("company_memory"), dict) and dossier["company_memory"].get("ok")
        if not already_mem:
            from app.ui.timeouts import ask_slim_enabled

            injected = injected_from_dossier(dossier)
            mem = incremental_compile(
                t,
                injected=injected,
                persist=True,
                skip_live=True,
                # ASK_SLIM: avoid live Yahoo price fan-out on Ask (META.NS storms).
                allow_live_prices=not ask_slim_enabled(),
            )
            if not mem.get("ok"):
                # Fallback: full incremental compile once (cold memory)
                mem = incremental_compile(t, persist=True)
            if mem.get("ok"):
                dossier = merge_memory_into_dossier(dossier, mem)
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # P3.2 Investment Knowledge Graph — relationship context (Decision Engine still CID-only)
    try:
        from investment_knowledge_graph.build import build_company_graph
        from investment_knowledge_graph.enrich import merge_graph_into_dossier
        from cid.store import get_cid_store

        already_kg = (
            isinstance(dossier.get("investment_knowledge_graph"), dict)
            and dossier["investment_knowledge_graph"].get("ok")
        )
        if not already_kg:
            mem_for_graph = None
            if isinstance(dossier.get("memory"), dict):
                mem_for_graph = {
                    "ok": True,
                    "entity": t,
                    "ownership_history": (dossier.get("memory") or {}).get("ownership_history"),
                    "sector_history": (dossier.get("memory") or {}).get("sector_history"),
                    "event_timeline": (dossier.get("memory") or {}).get("event_timeline"),
                }
            graph = build_company_graph(t, memory=mem_for_graph)
            if graph.get("n_nodes"):
                dossier = merge_graph_into_dossier(dossier, graph)
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    # P4.5 Opportunity Intelligence — research prioritisation (never BUY/SELL; DE unchanged)
    try:
        from opportunity_intelligence.enrich import merge_opportunity_into_dossier
        from opportunity_intelligence.production import analyse as opportunity_analyse
        from cid.store import get_cid_store

        already_oie = (
            isinstance(dossier.get("opportunity_intelligence"), dict)
            and dossier["opportunity_intelligence"].get("ok")
        )
        if not already_oie:
            # Prefer memory already on dossier / compiled via delta path
            injected = None
            if isinstance(dossier.get("memory"), dict) and dossier.get("company_memory", {}).get("ok"):
                injected = {
                    "ok": True,
                    "entity": t,
                    "confidence": (dossier.get("company_memory") or {}).get("confidence"),
                    "compiled_at": (dossier.get("company_memory") or {}).get("compiled_at"),
                    "memory_version": (dossier.get("company_memory") or {}).get("memory_version"),
                    "memory_delta": (dossier.get("company_memory") or {}).get("memory_delta"),
                    "financial_history": (dossier.get("memory") or {}).get("financial_history"),
                    "ownership_history": (dossier.get("memory") or {}).get("ownership_history"),
                    "valuation_history": (dossier.get("memory") or {}).get("valuation_history"),
                    "corporate_history": (dossier.get("memory") or {}).get("corporate_history"),
                    "sector_history": (dossier.get("memory") or {}).get("sector_history"),
                    "event_timeline": (dossier.get("memory") or {}).get("event_timeline"),
                    "price_intelligence": (dossier.get("memory") or {}).get("price_intelligence"),
                    "risk_history": (dossier.get("memory") or {}).get("risk_history"),
                    "competitive_position": (dossier.get("memory") or {}).get("competitive_position"),
                    "business_model": (dossier.get("memory") or {}).get("business_model"),
                }
            oie = opportunity_analyse(
                t,
                injected_memory=injected,
                compile_if_missing=injected is None,
                persist_memory=False,
            )
            if oie.get("ok"):
                dossier = merge_opportunity_into_dossier(dossier, oie)
                dossier = get_cid_store().put(dossier)
    except Exception:
        pass

    return {
        **dossier,
        "enabled": True,
        "cid_version": CID_VERSION,
        "answer_policy": "dossier_before_raw_apis",
        "reasoning_hint": _reasoning_hint(dossier),
    }


def attach_for_engine(engine: str, ticker: str | None, **kwargs: Any) -> dict[str, Any]:
    pkg = get_or_build(ticker, **kwargs)
    return {
        "company_dossier": pkg,
        "attached": bool(pkg.get("enabled")) and bool(pkg.get("ticker")),
        "engine": engine,
    }


def package_for_ask_agi(
    query: str,
    *,
    ticker: str | None = None,
    leo_pkg: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return get_or_build(
        ticker,
        query=query,
        leo_pkg=leo_pkg,
        finance_academy=finance_academy,
        sif_pkg=sif_pkg,
    )


def timeline(ticker: str, *, limit: int = 100) -> dict[str, Any]:
    d = get_dossier(ticker)
    events = list(d.get("evidence_timeline") or [])[-limit:]
    events = list(reversed(events))
    return {
        "ticker": (ticker or "").upper(),
        "count": len(events),
        "events": events,
        "cid_version": CID_VERSION,
    }


def coverage(ticker: str) -> dict[str, Any]:
    d = get_dossier(ticker)
    cov = compute_coverage(d)
    return {
        "ticker": (ticker or "").upper(),
        "coverage_score": cov["coverage_score"],
        "coverage_grade": cov["coverage_grade"],
        "institutional_ready": cov["institutional_ready"],
        "categories": cov["coverage"],
        "missing_evidence": cov["missing_evidence"],
        "cid_version": CID_VERSION,
    }


def valuation_view(ticker: str) -> dict[str, Any]:
    d = get_dossier(ticker)
    return {
        "ticker": (ticker or "").upper(),
        "valuation": d.get("valuation") or {},
        "market_data": d.get("market_data") or {},
        "sector_framework": d.get("sector_framework") or {},
        "cid_version": CID_VERSION,
    }


def risk_view(ticker: str) -> dict[str, Any]:
    d = get_dossier(ticker)
    return {
        "ticker": (ticker or "").upper(),
        "risks": d.get("risks") or {},
        "catalysts": d.get("catalysts") or {},
        "cid_version": CID_VERSION,
    }


def forecast_view(ticker: str) -> dict[str, Any]:
    d = get_dossier(ticker)
    return {
        "ticker": (ticker or "").upper(),
        "forecasts": d.get("forecasts") or {},
        "cid_version": CID_VERSION,
    }


def documents_view(ticker: str) -> dict[str, Any]:
    d = get_dossier(ticker)
    return {
        "ticker": (ticker or "").upper(),
        "documents": d.get("documents") or {},
        "announcements": (d.get("announcements") or [])[-40:],
        "latest_filing": d.get("latest_filing"),
        "latest_presentation": d.get("latest_presentation"),
        "latest_announcement": d.get("latest_announcement"),
        "cid_version": CID_VERSION,
    }


def production_dashboard() -> dict[str, Any]:
    store = get_cid_store()
    # Ensure tracked universe has shells
    for t in TRACKED_TICKERS:
        if not store.get(t):
            ensure_dossier(t)
    rows = store.summary_rows(limit=100)
    grades = {}
    for r in rows:
        g = r.get("coverage_grade") or "Insufficient"
        grades[g] = grades.get(g, 0) + 1
    return {
        "programme": "CID",
        "cid_version": CID_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_cid_enabled(),
        "dossier_count": len(rows),
        "tracked_tickers": list(TRACKED_TICKERS),
        "grade_distribution": grades,
        "dossiers": rows,
        "answer_policy": "dossier_before_raw_apis",
        "not_an_engine": True,
    }


def warm_tracked(*, use_leo: bool = True) -> dict[str, Any]:
    """Validation helper — build dossiers for tracked tickers via LEO when requested."""
    packages = []
    for t in TRACKED_TICKERS:
        leo_pkg = None
        if use_leo:
            try:
                from leo.production import package_for_query

                leo_pkg = package_for_query(f"Should I buy {t}?", ticker=t, engine="cid_warm", record=False)
            except Exception:
                leo_pkg = None
        sif_pkg = (leo_pkg or {}).get("sector_intelligence") if isinstance(leo_pkg, dict) else None
        # Also pull SIF directly
        try:
            from sif.production import analyse_query

            sif_pkg = analyse_query(f"Should I buy {t}?", ticker=t, engine="cid", record=False) or sif_pkg
        except Exception:
            pass
        try:
            from academy.fapi.production import package_for_query as fapi_package

            fa = fapi_package(f"Should I buy {t}?", engine="cid", ticker=t, record=False)
        except Exception:
            fa = {}
        d = get_or_build(t, query=f"Should I buy {t}?", leo_pkg=leo_pkg, finance_academy=fa, sif_pkg=sif_pkg)
        packages.append(
            {
                "ticker": t,
                "coverage_score": d.get("coverage_score"),
                "coverage_grade": d.get("coverage_grade"),
                "sector_id": (d.get("sector_framework") or {}).get("sector_id"),
                "academy_concepts": len((d.get("finance_academy") or {}).get("active_concepts") or []),
                "timeline_events": len(d.get("evidence_timeline") or []),
                "documents": {
                    k: len(v or [])
                    for k, v in ((d.get("documents") or {}).items())
                },
                "sif_attached": bool((d.get("sector_framework") or {}).get("sector_id")),
                "academy_linked": bool((d.get("finance_academy") or {}).get("active_concepts")),
            }
        )
    return {
        "cid_version": CID_VERSION,
        "count": len(packages),
        "packages": packages,
        "pass": all(p["timeline_events"] > 0 and p["sif_attached"] for p in packages),
    }


def quality_gates() -> dict[str, Any]:
    warmed = warm_tracked(use_leo=True)
    checks = {
        "dossiers_created": all(p.get("ticker") for p in warmed["packages"]),
        "evidence_updates": all((p.get("timeline_events") or 0) > 0 for p in warmed["packages"]),
        "coverage_calculated": all(p.get("coverage_score") is not None for p in warmed["packages"]),
        "sif_attached": all(p.get("sif_attached") for p in warmed["packages"]),
        "academy_linked": all(p.get("academy_linked") for p in warmed["packages"]),
        "leo_updates_dossier": all((p.get("timeline_events") or 0) > 0 for p in warmed["packages"]),
    }
    return {
        "cid_version": CID_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "packages": warmed["packages"],
    }


def _reasoning_hint(dossier: dict[str, Any]) -> str:
    grade = dossier.get("coverage_grade") or "Insufficient"
    sector = (dossier.get("sector_framework") or {}).get("sector_name") or (dossier.get("identity") or {}).get("sector")
    kpis = ((dossier.get("sector_kpis") or {}).get("priority_metrics") or [])[:6]
    miss = dossier.get("missing_evidence") or []
    parts = [
        f"CID {dossier.get('ticker')}: {grade} (score {dossier.get('coverage_score')}).",
    ]
    if sector:
        parts.append(f"Sector framework: {sector}.")
    if kpis:
        parts.append("Priority KPIs: " + ", ".join(kpis) + ".")
    if miss:
        parts.append("Missing: " + ", ".join(miss[:6]) + ".")
    parts.append("Reason from this dossier first — do not rebuild company context from raw APIs.")
    return " ".join(parts)
