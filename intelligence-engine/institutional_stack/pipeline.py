"""Orchestrate FIL → FDI → MII → EIL/PIL soft refresh. No engine redesign."""

from __future__ import annotations

from typing import Any

from institutional_stack.flags import is_enabled
from institutional_stack.schema import DEFAULT_BOOTSTRAP_TICKERS, LAYERS, STACK_VERSION


def ensure_filings_seeded() -> dict[str, Any]:
    """Ensure FIL corpus is loaded into memory (idempotent)."""
    try:
        from filing_intelligence.ingestion.store import all_documents

        docs = all_documents()
        return {"seeded": True, "document_count": len(docs)}
    except Exception as exc:
        return {"seeded": False, "error": str(exc)[:160]}


def refresh_ticker(ticker: str) -> dict[str, Any]:
    """Run FIL → FDI → MII analyse for one ticker; soft-touch PIL/EIL dashboards."""
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND"}
    t = aliases.get(t, t)
    out: dict[str, Any] = {
        "ticker": t,
        "stack_version": STACK_VERSION,
        "layers": {},
        "errors": [],
    }
    if not t:
        out["errors"].append("ticker_required")
        return out

    # FIL
    try:
        from filing_intelligence.production import analyse as fil_analyse

        fil = fil_analyse(t)
        out["layers"]["filing_intelligence"] = {
            "found": bool(fil.get("found")),
            "document_count": len(fil.get("documents") or fil.get("timeline") or [])
            if isinstance(fil.get("documents") or fil.get("timeline"), list)
            else fil.get("document_count"),
            "enabled": fil.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"fil:{str(exc)[:120]}")

    # FDI
    try:
        from filing_diff.production import analyse as fdi_analyse

        fdi = fdi_analyse(t)
        out["layers"]["filing_diff"] = {
            "found": bool(fdi.get("found")),
            "material_changes": len(fdi.get("material_changes") or fdi.get("changes") or []),
            "enabled": fdi.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"fdi:{str(exc)[:120]}")

    # MII
    try:
        from management_intelligence.production import analyse as mii_analyse

        mii = mii_analyse(t)
        conf = mii.get("confidence") or {}
        dna = mii.get("dna") or {}
        out["layers"]["management_intelligence"] = {
            "found": bool(mii.get("found")),
            "confidence": conf.get("confidence") if isinstance(conf, dict) else conf,
            "dna": dna.get("primary") if isinstance(dna, dict) else dna,
            "enabled": mii.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"mii:{str(exc)[:120]}")

    # ACI
    try:
        from accounting_intelligence.production import analyse as aci_analyse

        aci = aci_analyse(t)
        conf = aci.get("confidence") or {}
        behaviour = aci.get("behaviour") or {}
        report = aci.get("report") or {}
        out["layers"]["accounting_intelligence"] = {
            "found": bool(aci.get("found")),
            "confidence": conf.get("confidence") if isinstance(conf, dict) else conf,
            "behaviour": behaviour.get("primary") if isinstance(behaviour, dict) else behaviour,
            "accounting_quality_score": report.get("accounting_quality_score"),
            "enabled": aci.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"aci:{str(exc)[:120]}")

    # PIO — lightweight soft slice (avoid recursive stack refresh)
    try:
        from portfolio_intelligence.production import soft_slice_for_analyst as pio_slice

        pio = (pio_slice(t, analyst="committee") or {}).get("portfolio_intelligence") or {}
        out["layers"]["portfolio_intelligence"] = {
            "found": bool(pio.get("enabled")),
            "portfolio_id": pio.get("portfolio_id"),
            "health_grade": pio.get("health_grade"),
            "portfolio_quality": pio.get("portfolio_quality"),
            "net_effect": (pio.get("impact") or {}).get("net_portfolio_effect"),
            "enabled": pio.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"pio:{str(exc)[:120]}")

    # CIG — causal why soft slice
    try:
        from causal_graph.production import soft_slice_for_analyst as cig_slice

        cig = (cig_slice(t, analyst="committee") or {}).get("causal_intelligence") or {}
        out["layers"]["causal_intelligence"] = {
            "found": bool(cig.get("found")),
            "confidence": cig.get("confidence"),
            "upstream_drivers": cig.get("upstream_drivers"),
            "enabled": cig.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"cig:{str(exc)[:120]}")

    # FIE — forecast scenarios soft slice
    try:
        from forecast_intelligence.production import soft_slice_for_analyst as fie_slice

        fie = (fie_slice(t, analyst="committee") or {}).get("forecast_intelligence") or {}
        out["layers"]["forecast_intelligence"] = {
            "found": bool(fie.get("found")),
            "most_likely": fie.get("most_likely"),
            "confidence": fie.get("confidence"),
            "enabled": fie.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"fie:{str(exc)[:120]}")

    # IKG — knowledge graph soft slice
    try:
        from knowledge_graph.production import soft_slice_for_analyst as ikg_slice

        ikg = (ikg_slice(t, analyst="committee") or {}).get("knowledge_graph") or {}
        out["layers"]["knowledge_graph"] = {
            "found": bool(ikg.get("found")),
            "relationship_count": ikg.get("relationship_count"),
            "confidence": ikg.get("confidence"),
            "canonical_id": ikg.get("canonical_id"),
            "enabled": ikg.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"ikg:{str(exc)[:120]}")

    # ILM — institutional learning & memory soft slice
    try:
        from institutional_memory.production import soft_slice_for_analyst as ilm_slice

        ilm = (ilm_slice(t, analyst="committee") or {}).get("institutional_memory") or {}
        out["layers"]["institutional_memory"] = {
            "found": bool(ilm.get("found")),
            "lesson_count": ilm.get("lesson_count"),
            "mistake_count": ilm.get("mistake_count"),
            "thinking_improved": ilm.get("thinking_improved"),
            "enabled": ilm.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"ilm:{str(exc)[:120]}")

    # SSL — simulation & strategy lab soft slice
    try:
        from simulation_lab.production import soft_slice_for_analyst as ssl_slice

        ssl = (ssl_slice(t, analyst="committee") or {}).get("simulation_lab") or {}
        out["layers"]["simulation_lab"] = {
            "found": bool(ssl.get("found")),
            "expected_return": ssl.get("expected_return"),
            "confidence": ssl.get("confidence"),
            "scenario_id": ssl.get("scenario_id"),
            "enabled": ssl.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"ssl:{str(exc)[:120]}")

    # IDE V2 — constitutional decision orchestrator soft slice
    try:
        from decision_engine_v2.production import soft_slice_for_analyst as idev2_slice

        idev2 = (idev2_slice(t, analyst="committee") or {}).get("decision_engine_v2") or {}
        out["layers"]["decision_engine_v2"] = {
            "found": bool(idev2.get("found")),
            "recommendation_status": idev2.get("recommendation_status"),
            "confidence": idev2.get("confidence"),
            "audit_id": idev2.get("audit_id"),
            "enabled": idev2.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"idev2:{str(exc)[:120]}")

    # PIL soft refresh (overlay from FIL)
    try:
        from peer_intelligence.production import company as pil_company

        pil = pil_company(t)
        out["layers"]["peer_intelligence"] = {
            "found": bool(pil.get("found") or pil.get("enabled")),
            "enabled": pil.get("enabled", True),
        }
    except Exception as exc:
        out["errors"].append(f"pil:{str(exc)[:120]}")

    # EIL soft touch
    try:
        from academy.evidence.production import dashboard as eil_dashboard

        eil = eil_dashboard()
        out["layers"]["evidence_intelligence"] = {
            "enabled": eil.get("enabled", True),
            "version": eil.get("version") or eil.get("eil_version"),
        }
    except Exception as exc:
        out["errors"].append(f"eil:{str(exc)[:120]}")

    out["ok"] = len(out["errors"]) == 0
    return out


def ingest_and_refresh(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept a filing payload, persist via FIL, then chain FDI/MII refresh."""
    ensure_filings_seeded()
    from filing_intelligence.production import ingest as fil_ingest

    result = fil_ingest(payload)
    ticker = str(payload.get("ticker") or result.get("ticker") or "").upper()
    chain: dict[str, Any] = {}
    if result.get("accepted") and ticker and is_enabled():
        chain = refresh_ticker(ticker)
    return {
        "ingest": result,
        "chain": chain,
        "stack_version": STACK_VERSION,
        "auto_chain": bool(chain),
    }


def bootstrap(tickers: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Seed FIL corpus and refresh default institutional tickers."""
    seed = ensure_filings_seeded()
    targets = list(tickers or DEFAULT_BOOTSTRAP_TICKERS)
    refreshed = [refresh_ticker(t) for t in targets]
    return {
        "stack_version": STACK_VERSION,
        "seed": seed,
        "tickers": targets,
        "refreshed": refreshed,
        "layers": list(LAYERS),
        "ok": seed.get("seeded") and all(r.get("ok") for r in refreshed),
    }


def company_pack(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    """Assemble soft slices from all institutional layers for one ticker."""
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND"}
    t = aliases.get(t, t)
    pack: dict[str, Any] = {
        "enabled": is_enabled(),
        "stack_version": STACK_VERSION,
        "ticker": t,
        "pipeline": [
            "Official Filings",
            "FIL",
            "FDI",
            "MII",
            "ACI",
            "EIL",
            "PIL",
            "CIG",
            "IKG",
            "FIE",
            "ILM",
            "SSL",
            "PIO",
            "IDE_V2",
        ],
        "layers": {},
    }
    if not t or not is_enabled():
        return pack

    # FIL
    try:
        from filing_intelligence.production import soft_slice_for_analyst as fil_slice

        pack["layers"].update(fil_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["filing_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # FDI
    try:
        from filing_diff.production import soft_slice_for_analyst as fdi_slice

        pack["layers"].update(fdi_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["filing_diff"] = {"enabled": False, "error": str(exc)[:120]}

    # MII
    try:
        from management_intelligence.production import soft_slice_for_analyst as mii_slice

        pack["layers"].update(mii_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["management_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # ACI
    try:
        from accounting_intelligence.production import soft_slice_for_analyst as aci_slice

        pack["layers"].update(aci_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["accounting_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # PIO
    try:
        from portfolio_intelligence.production import soft_slice_for_analyst as pio_slice

        pack["layers"].update(pio_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["portfolio_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # PIL
    try:
        from peer_intelligence.production import soft_slice_for_analyst as pil_slice

        pack["layers"].update(pil_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["peer_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # CIG
    try:
        from causal_graph.production import soft_slice_for_analyst as cig_slice

        pack["layers"].update(cig_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["causal_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # FIE
    try:
        from forecast_intelligence.production import soft_slice_for_analyst as fie_slice

        pack["layers"].update(fie_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["forecast_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # IKG
    try:
        from knowledge_graph.production import soft_slice_for_analyst as ikg_slice

        pack["layers"].update(ikg_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["knowledge_graph"] = {"enabled": False, "error": str(exc)[:120]}

    # ILM
    try:
        from institutional_memory.production import soft_slice_for_analyst as ilm_slice

        pack["layers"].update(ilm_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["institutional_memory"] = {"enabled": False, "error": str(exc)[:120]}

    # SSL
    try:
        from simulation_lab.production import soft_slice_for_analyst as ssl_slice

        pack["layers"].update(ssl_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["simulation_lab"] = {"enabled": False, "error": str(exc)[:120]}

    # IDE V2 (after PIO/SSL soft facts — constitutional package before CIO surfaces)
    try:
        from decision_engine_v2.production import soft_slice_for_analyst as idev2_slice

        pack["layers"].update(idev2_slice(t, analyst=analyst) or {})
    except Exception as exc:
        pack["layers"]["decision_engine_v2"] = {"enabled": False, "error": str(exc)[:120]}

    # EIL (company-agnostic support slice)
    try:
        from academy.evidence.production import soft_slice_for_irs

        eil = soft_slice_for_irs() or {}
        if eil:
            pack["layers"]["evidence_intelligence"] = eil.get("evidence_intelligence") or eil
    except Exception as exc:
        pack["layers"]["evidence_intelligence"] = {"enabled": False, "error": str(exc)[:120]}

    # Compact summary for UI / Ask AGI
    mii = pack["layers"].get("management_intelligence") or {}
    aci = pack["layers"].get("accounting_intelligence") or {}
    pio = pack["layers"].get("portfolio_intelligence") or {}
    cig = pack["layers"].get("causal_intelligence") or {}
    fie = pack["layers"].get("forecast_intelligence") or {}
    ikg = pack["layers"].get("knowledge_graph") or {}
    ilm = pack["layers"].get("institutional_memory") or {}
    ssl = pack["layers"].get("simulation_lab") or {}
    idev2 = pack["layers"].get("decision_engine_v2") or {}
    fdi = pack["layers"].get("filing_diff") or {}
    fil = pack["layers"].get("filing_intelligence") or {}
    pil = pack["layers"].get("peer_intelligence") or {}
    impact = pio.get("impact") if isinstance(pio.get("impact"), dict) else {}
    pack["summary"] = {
        "management_confidence": mii.get("confidence"),
        "management_dna": mii.get("dna"),
        "accounting_confidence": aci.get("confidence"),
        "accounting_behaviour": aci.get("behaviour"),
        "accounting_quality_score": aci.get("accounting_quality_score"),
        "manipulation_risk": aci.get("manipulation_risk"),
        "portfolio_id": pio.get("portfolio_id"),
        "portfolio_grade": pio.get("health_grade"),
        "portfolio_quality": pio.get("portfolio_quality"),
        "portfolio_net_effect": impact.get("net_portfolio_effect"),
        "portfolio_fit": (pio.get("suitability") or {}).get("portfolio_fit")
        if isinstance(pio.get("suitability"), dict)
        else None,
        "causal_confidence": cig.get("confidence"),
        "causal_upstream": cig.get("upstream_drivers"),
        "causal_why": (cig.get("why") or [None])[0] if isinstance(cig.get("why"), list) else cig.get("why"),
        "forecast_most_likely": fie.get("most_likely"),
        "forecast_confidence": fie.get("confidence"),
        "forecast_distribution": fie.get("distribution"),
        "forecast_summary": fie.get("executive_forecast"),
        "knowledge_canonical_id": ikg.get("canonical_id"),
        "knowledge_relationship_count": ikg.get("relationship_count"),
        "knowledge_confidence": ikg.get("confidence"),
        "knowledge_summary": ikg.get("summary"),
        "memory_lesson_count": ilm.get("lesson_count"),
        "memory_mistake_count": ilm.get("mistake_count"),
        "memory_thinking_improved": ilm.get("thinking_improved"),
        "memory_summary": ilm.get("summary"),
        "simulation_scenario_id": ssl.get("scenario_id"),
        "simulation_expected_return": ssl.get("expected_return"),
        "simulation_confidence": ssl.get("confidence"),
        "simulation_summary": ssl.get("summary"),
        "simulation_stress_completed": ssl.get("stress_completed"),
        "decision_status": idev2.get("recommendation_status"),
        "decision_confidence": idev2.get("confidence"),
        "decision_audit_id": idev2.get("audit_id"),
        "decision_summary": idev2.get("summary"),
        "decision_conflict_count": idev2.get("conflict_count"),
        "filing_found": fil.get("found", bool(fil.get("enabled"))),
        "material_change_signal": bool(fdi.get("committee") or fdi.get("desk") or fdi.get("enabled")),
        "peer_enabled": bool(pil.get("enabled")),
        "primary_question_mii": "Can this management team be trusted to compound shareholder value?",
        "primary_question_aci": "Can the financial statements be trusted?",
        "primary_question_pio": "Does this company improve this specific portfolio?",
        "primary_question_cig": "Why did this happen?",
        "primary_question_fie": "What future paths are plausible?",
        "primary_question_ikg": "What is connected?",
        "primary_question_ilm": "What has AGIB learned over time?",
        "primary_question_ssl": "What happens if this decision is taken?",
        "primary_question_idev2": "What is the highest-quality institutional decision?",
        "primary_question_fdi": "What materially changed since the previous filing?",
        "primary_question_fil": "What do the company's own filings actually say?",
        "primary_question_pil": "How does this company compare to the best and most relevant peers?",
        "primary_question_eil": "What evidence supports each claim, and at what confidence?",
        "architecture_frozen": True,
    }
    return pack
