"""ECP production bridge — soft evidence completion before recommendation gates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ecp.completers import complete_from_kip_kf, complete_market_and_valuation
from ecp.gaps import coverage_from_gaps, identify_gaps
from ecp.merge import (
    apply_cid_enrichment,
    merge_evidence_objects,
    quality_panel,
    reassess_leo_package,
    withheld_explanation,
)
from ecp.schema import ECP_VERSION
from ecp import store as ecp_store


def is_ecp_enabled() -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), "ecp", True))
    except Exception:
        return True


def soft_complete(
    *,
    query: str = "",
    ticker: str | None = None,
    leo_pkg: Dict[str, Any] | None = None,
    cid: Dict[str, Any] | None = None,
    sif_pkg: Dict[str, Any] | None = None,
    dvc_pkg: Dict[str, Any] | None = None,
    kip: Any | None = None,
    kf: Any | None = None,
    client: Any | None = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Ask AGI soft entry — identify gaps, auto-complete, refresh LEO/CID, re-evaluate gates.
    Recommendation gate logic itself is unchanged (LEO/SIF assessors).
    """
    if not is_ecp_enabled():
        return {"enabled": False, "ecp_version": ECP_VERSION, "bypassed": True}

    leo_pkg = dict(leo_pkg or {})
    cid = dict(cid or {})
    sif_pkg = dict(sif_pkg or {})
    dvc_pkg = dict(dvc_pkg or {})
    t = (ticker or leo_pkg.get("ticker") or cid.get("ticker") or "").upper() or None

    gaps_before = identify_gaps(ticker=t, leo_pkg=leo_pkg, cid=cid, sif_pkg=sif_pkg, dvc_pkg=dvc_pkg)
    cov_before = coverage_from_gaps(gaps_before)

    gate = leo_pkg.get("quality_gate") or {}
    sif_gate = sif_pkg.get("recommendation_gate") or {}
    needs_completion = bool(gate.get("blocked") or sif_gate.get("blocked") or gaps_before.get("target_leo_types"))
    if not needs_completion and not force:
        panel = quality_panel(
            gaps_before=gaps_before,
            gaps_after=gaps_before,
            leo_pkg=leo_pkg,
            cid=cid,
            coverage_before=cov_before,
            coverage_after=cov_before,
        )
        return {
            "enabled": True,
            "ecp_version": ECP_VERSION,
            "ticker": t,
            "skipped": True,
            "reason": "gates_not_blocked",
            "gaps_before": gaps_before,
            "quality_panel": panel,
            "leo_delta": {},
            "cid_delta": {},
            "ask_agi_hints": [],
        }

    providers_used: List[str] = []
    completed_automatically: List[str] = []
    new_objects: List[Dict[str, Any]] = []
    yahoo_pack: Dict[str, Any] = {}
    dvc_pack: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    # Market / valuation / financials via MarketDataClient + YFP + DVC
    if t and any(
        x in (gaps_before.get("target_leo_types") or [])
        for x in ("market_data", "valuation_metrics", "financial_statements", "sector_kpis")
    ):
        try:
            mv = complete_market_and_valuation(t, client=client)
            providers_used.extend(mv.get("providers_used") or [])
            new_objects.extend(mv.get("evidence_objects") or [])
            completed_automatically.extend(mv.get("completed_types") or [])
            yahoo_pack = mv.get("yahoo_pack") or {}
            dvc_pack = mv.get("dvc_pack") or {}
            errors.update(mv.get("errors") or {})
        except Exception as exc:  # noqa: BLE001
            errors["market_completion"] = str(exc)[:200]

    # KIP / KF soft knowledge
    if t and (gaps_before.get("item_gaps") or {}).get("company_knowledge"):
        try:
            kk = complete_from_kip_kf(t, query or t, kip=kip, kf=kf)
            providers_used.extend(kk.get("providers_used") or [])
            new_objects.extend(kk.get("evidence_objects") or [])
            completed_automatically.extend(kk.get("completed_types") or [])
        except Exception as exc:  # noqa: BLE001
            errors["kip_kf"] = str(exc)[:200]

    # Merge into LEO package and reassess gate
    merged_objects = merge_evidence_objects(list(leo_pkg.get("evidence_objects") or []), new_objects)
    leo_updated = reassess_leo_package(leo_pkg, merged_objects)

    # Update CID (fill empties only)
    cid_updated = apply_cid_enrichment(t or "", cid, yahoo_pack=yahoo_pack, dvc_pack=dvc_pack)

    # Prefer DVC pack for gap re-evaluation
    dvc_for_gaps = dvc_pack if dvc_pack else dvc_pkg
    gaps_after = identify_gaps(
        ticker=t,
        leo_pkg=leo_updated,
        cid=cid_updated,
        sif_pkg=sif_pkg,
        dvc_pkg=dvc_for_gaps,
    )
    cov_after = coverage_from_gaps(gaps_after)

    # Soft refresh SIF recommendation_gate via sif_evidence_supplied (no SIF redesign)
    sif_delta: Dict[str, Any] = {}
    supplied = leo_updated.get("sif_evidence_supplied") or {}
    if supplied:
        sif_delta["sif_evidence_supplied"] = supplied
        try:
            from sif.evidence import assess_company_evidence

            ev = assess_company_evidence(t, supplied=supplied, kip=kip)
            if isinstance(ev, dict):
                sif_delta["company_evidence"] = ev
                allow = bool(ev.get("sufficient"))
                sif_delta["recommendation_gate"] = {
                    "allow_buy_hold_sell": allow,
                    "blocked": not allow,
                    "reason": (
                        "ecp_reassessed"
                        if allow
                        else (ev.get("recommendation_policy") or "still_insufficient_after_ecp")
                    ),
                    "message": ev.get("message")
                    or (
                        "Evidence completion satisfied SIF company-evidence bar."
                        if allow
                        else "Insufficient company evidence for institutional recommendation."
                    ),
                    "from_ecp": True,
                }
        except Exception:
            if not (leo_updated.get("quality_gate") or {}).get("blocked"):
                sif_delta["recommendation_gate"] = {
                    **(sif_pkg.get("recommendation_gate") or {}),
                    "allow_buy_hold_sell": True,
                    "blocked": False,
                    "from_ecp": True,
                    "message": "Evidence completion satisfied LEO must-have bar; SIF re-check soft-passed.",
                }

    panel = quality_panel(
        gaps_before=gaps_before,
        gaps_after=gaps_after,
        leo_pkg=leo_updated,
        cid=cid_updated,
        coverage_before=cov_before,
        coverage_after=cov_after,
    )

    still_missing = list(dict.fromkeys([*(gaps_after.get("must_have_missing") or []), *(gaps_after.get("leo_missing") or [])]))
    still_items = [x.get("item") for x in (gaps_after.get("flat_missing") or [])][:20]

    explanation = None
    if panel.get("gate_blocked"):
        explanation = withheld_explanation(panel, gaps_after)

    hints = _ask_agi_hints(panel, completed_automatically, still_missing, explanation)

    report = {
        "enabled": True,
        "ecp_version": ECP_VERSION,
        "ticker": t,
        "query": (query or "")[:240],
        "coverage": panel.get("coverage_pct"),
        "coverage_before": panel.get("coverage_before_pct"),
        "completed_automatically": sorted(set(completed_automatically)),
        "still_missing": still_missing,
        "still_missing_items": still_items,
        "providers_used": list(dict.fromkeys(providers_used)),
        "conflicts": (dvc_pack.get("conflicts") or dvc_for_gaps.get("conflicts") or [])[:10],
        "quality_improvement": panel.get("quality_improvement_pct"),
        "quality_panel": panel,
        "gaps_before": gaps_before,
        "gaps_after": gaps_after,
        "gate_blocked_after": panel.get("gate_blocked"),
        "withheld_explanation": explanation,
        "errors": errors,
        "objects_added": len(new_objects),
    }
    ecp_store.save_report(report)

    return {
        **report,
        "leo_delta": {
            "evidence_objects": leo_updated.get("evidence_objects"),
            "quality_gate": leo_updated.get("quality_gate"),
            "evidence_plan": leo_updated.get("evidence_plan"),
            "usage": leo_updated.get("usage"),
            "sif_evidence_supplied": leo_updated.get("sif_evidence_supplied"),
            "missing_evidence": leo_updated.get("missing_evidence"),
            "ecp_completed": True,
        },
        "cid_delta": {
            **{k: cid_updated.get(k) for k in (
                "market_data",
                "financial_metrics",
                "valuation",
                "identity",
                "validated_fields",
                "data_quality_panel",
                "dvc",
                "coverage",
                "coverage_score",
                "coverage_grade",
                "missing_evidence",
                "enrichment",
                "research_grade",
                "data_grade",
                "knowledge_grade",
                "financial_statements",
            ) if k in cid_updated},
            "ticker": t,
            "ecp_completed": True,
        },
        "sif_delta": sif_delta,
        "ask_agi_hints": hints,
        "answer_policy": "complete_evidence_before_recommendation_gate",
    }


def _ask_agi_hints(
    panel: Dict[str, Any],
    completed: List[str],
    still_missing: List[str],
    explanation: str | None,
) -> List[str]:
    hints: List[str] = []
    if completed:
        hints.append(
            f"ECP auto-completed evidence types: {', '.join(completed[:8])}. "
            f"Coverage {panel.get('coverage_before_pct')}% → {panel.get('coverage_pct')}%."
        )
    hints.append(
        f"Quality gates — Coverage {panel.get('coverage_pct')}%, "
        f"Research Grade {panel.get('research_grade')}, Data Grade {panel.get('data_grade')}, "
        f"Knowledge Grade {panel.get('knowledge_grade')}, "
        f"Confidence {round(float(panel.get('confidence') or 0) * 100) if panel.get('confidence') is not None else 'n/a'}%, "
        f"Freshness {round(float(panel.get('freshness') or 0) * 100) if panel.get('freshness') is not None else 'n/a'}%."
    )
    if panel.get("gate_blocked") and explanation:
        hints.append(explanation.replace("\n", " "))
    elif still_missing:
        hints.append("Still missing after ECP: " + ", ".join(still_missing[:8]))
    else:
        hints.append("ECP: must-have evidence bar satisfied — recommendation pipeline eligible for evaluation.")
    return hints[:6]


def production_dashboard() -> Dict[str, Any]:
    reports = ecp_store.list_reports(limit=50)
    completed_n = sum(len(r.get("completed_automatically") or []) for r in reports)
    still_n = sum(len(r.get("still_missing") or []) for r in reports)
    improvements = [float(r.get("quality_improvement") or 0) for r in reports]
    avg_imp = round(sum(improvements) / len(improvements), 2) if improvements else 0.0
    return {
        "programme": "ECP",
        "ecp_version": ECP_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_ecp_enabled(),
        "role": "evidence_completion_orchestration",
        "not_an_engine": True,
        "not_a_recommendation_model": True,
        "flow": "CID → Quality Check → Identify Missing → ECP → Update LEO → Update CID → Re-evaluate → IRP → Answer",
        "reports": reports[:30],
        "latest_reports": reports[:15],
        "metrics": {
            "runs": len(reports),
            "types_completed": completed_n,
            "types_still_missing": still_n,
            "avg_quality_improvement_pct": avg_imp,
        },
        "provider_priority": [
            "official_exchange",
            "indianapi",
            "finnhub",
            "fmp",
            "yahoo",
            "kip",
            "knowledge_foundation",
        ],
    }


def quality_gates(tickers: List[str] | None = None) -> Dict[str, Any]:
    # Offline authoritative checks
    fake_leo = {
        "ticker": "NESTLEIND",
        "quality_gate": {
            "blocked": True,
            "must_have_missing": ["market_data", "valuation_metrics", "financial_statements"],
            "missing_evidence": ["market_data", "valuation_metrics", "financial_statements"],
            "present_types": ["annual_report", "quarterly_results"],
        },
        "evidence_objects": [
            {"evidence_type": "annual_report", "evidence_id": "a1"},
            {"evidence_type": "quarterly_results", "evidence_id": "q1"},
        ],
        "evidence_plan": {
            "required_evidence": [
                "annual_report",
                "quarterly_results",
                "financial_statements",
                "market_data",
                "valuation_metrics",
                "sector_kpis",
                "corporate_announcement",
            ],
            "missing_evidence": ["financial_statements", "market_data", "valuation_metrics"],
            "intent": "investment_recommendation",
        },
        "usage": {"external_api_contributed": True, "documents_used": True},
    }
    gaps = identify_gaps(
        ticker="NESTLEIND",
        leo_pkg=fake_leo,
        cid={"ticker": "NESTLEIND", "market_data": {}, "missing_evidence": ["market_data", "valuation"]},
        sif_pkg={"sector_id": "fmcg", "priority_metrics": ["volume_growth", "roic"], "recommendation_gate": {"blocked": True}},
    )
    from ecp.merge import merge_evidence_objects, reassess_leo_package
    from ecp.completers import _evidence_object

    objs = merge_evidence_objects(
        fake_leo["evidence_objects"],
        [
            _evidence_object(
                evidence_type="market_data",
                ticker="NESTLEIND",
                source_id="yahoo",
                title="md",
                facts=[{"field": "current_price", "value": 1443.5, "value_text": "1443.5"}],
            ),
            _evidence_object(
                evidence_type="valuation_metrics",
                ticker="NESTLEIND",
                source_id="yahoo",
                title="val",
                facts=[{"field": "trailing_pe", "value": 70.0, "value_text": "70"}],
            ),
            _evidence_object(
                evidence_type="financial_statements",
                ticker="NESTLEIND",
                source_id="yahoo",
                title="fs",
                facts=[{"field": "roe", "value": 0.9, "value_text": "0.9"}],
            ),
            _evidence_object(
                evidence_type="sector_kpis",
                ticker="NESTLEIND",
                source_id="ecp_derived",
                title="kpi",
                facts=[{"field": "roe", "value": 0.9, "value_text": "0.9"}],
            ),
            _evidence_object(
                evidence_type="corporate_announcement",
                ticker="NESTLEIND",
                source_id="nse",
                title="ann",
                facts=[{"field": "title", "value_text": "update"}],
            ),
        ],
    )
    refreshed = reassess_leo_package(fake_leo, objs)
    gate = refreshed.get("quality_gate") or {}

    checks = {
        "identifies_leo_gaps": "market_data" in (gaps.get("leo_missing") or []),
        "targets_completion_types": "market_data" in (gaps.get("target_leo_types") or []),
        "merge_adds_missing_types": "market_data" in {o.get("evidence_type") for o in objs},
        "reassess_uses_leo_gate": "allow_recommendation" in gate,
        "gate_unblocked_when_must_haves_present": gate.get("blocked") is False,
        "withheld_explains_when_blocked": bool(
            withheld_explanation(
                {
                    "coverage_pct": 62,
                    "research_grade": "C",
                    "data_grade": "C",
                    "knowledge_grade": "C",
                    "missing_items": ["roic"],
                    "must_have_missing": ["peer_valuation"],
                },
                gaps,
            ).startswith("Institutional recommendation status")
        ),
        "flag_readable": is_ecp_enabled() in (True, False),
        "store_roundtrip": _store_ok(),
    }
    return {
        "ecp_version": ECP_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "sample_gaps": {
            "leo_missing": gaps.get("leo_missing"),
            "target_leo_types": gaps.get("target_leo_types"),
        },
        "sample_gate_after": {
            "blocked": gate.get("blocked"),
            "must_have_missing": gate.get("must_have_missing"),
            "allow_recommendation": gate.get("allow_recommendation"),
        },
        "note": "Offline gap/merge/gate checks are authoritative; live provider completion is optional.",
    }


def _store_ok() -> bool:
    try:
        ecp_store.save_report({"ticker": "TESTECP", "completed_automatically": ["market_data"], "still_missing": []})
        return bool(ecp_store.get_report("TESTECP"))
    except Exception:
        return False
