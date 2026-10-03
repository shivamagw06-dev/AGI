"""Assemble full institutional company analysis report (Steps 1–10)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from company_analysis.academy_apply import apply_academy
from company_analysis.business_quality import score_business_quality
from company_analysis.evidence import pack_evidence
from company_analysis.financial import analyse_financials
from company_analysis.flags import flags_dict, is_enabled
from company_analysis.identity import identify_company
from company_analysis.readiness import evaluate_readiness
from company_analysis.schema import COMPANY_ANALYSIS_VERSION, PROGRAMME
from company_analysis.sector import analyse_sector
from company_analysis import store as ca_store
from company_analysis.thesis import build_thesis
from company_analysis.valuation_intel import analyse_valuation
from company_analysis.what_changed import analyse_what_changed


def _followups(identity: dict[str, Any], sector: dict[str, Any]) -> list[str]:
    t = identity.get("ticker") or "the company"
    sk = str(identity.get("sector_id") or "")
    qs = [
        f"What changed in {t}'s latest quarter vs the prior house view?",
        f"How does {t}'s valuation compare with its own history and peers?",
        f"Which Academy concepts are most binding for {t} right now?",
    ]
    if "bank" in sk.lower():
        qs.append(f"Is {t}'s ROE explained by CASA/NIM advantage or by leverage/credit cycle?")
    elif "fmcg" in sk.lower() or "staple" in sk.lower():
        qs.append(f"Is {t}'s premium valuation supported by ROIC and cash conversion?")
    else:
        metrics = list(sector.get("priority_metrics") or [])[:2]
        if metrics:
            qs.append(f"What do the latest {metrics[0]} trends imply for {t}?")
    return qs[:6]


def analyse_company(
    *,
    query: str = "",
    ticker: str | None = None,
    cid: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
    dvc_pkg: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    irp_pkg: dict[str, Any] | None = None,
    forecast_learning: dict[str, Any] | None = None,
    market_events: dict[str, Any] | None = None,
    record: bool = True,
) -> dict[str, Any]:
    if not is_enabled():
        return {
            "enabled": False,
            "programme": PROGRAMME,
            "version": COMPANY_ANALYSIS_VERSION,
            "bypassed": True,
        }

    # Prefer living dossier
    if cid is None and ticker:
        try:
            from cid.production import get_or_build

            cid = get_or_build(ticker, query=query, leo_pkg=leo_pkg, finance_academy=finance_academy, sif_pkg=sif_pkg)
        except Exception:
            cid = {"ticker": (ticker or "").upper()}

    identity = identify_company(ticker, cid=cid, sif_pkg=sif_pkg)
    t = identity.get("ticker")
    academy_applied = apply_academy(identity=identity, finance_academy=finance_academy, cid=cid)
    financial = analyse_financials(identity=identity, cid=cid, dvc_pkg=dvc_pkg, leo_pkg=leo_pkg)
    valuation = analyse_valuation(identity=identity, cid=cid, valuation_pack=valuation_pack, dvc_pkg=dvc_pkg)
    sector = analyse_sector(identity=identity, sif_pkg=sif_pkg, cid=cid, academy_applied=academy_applied)
    business_quality = score_business_quality(
        identity=identity,
        academy_applied=academy_applied,
        financial=financial,
        sif_pkg=sif_pkg,
        cid=cid,
    )
    thesis = build_thesis(
        identity=identity,
        academy_applied=academy_applied,
        financial=financial,
        valuation=valuation,
        sector=sector,
        business_quality=business_quality,
    )
    changed = analyse_what_changed(cid=cid, leo_pkg=leo_pkg, financial=financial, market_events=market_events)
    evidence = pack_evidence(
        identity=identity,
        academy_applied=academy_applied,
        financial=financial,
        valuation=valuation,
        sector=sector,
        business_quality=business_quality,
        cid=cid,
        leo_pkg=leo_pkg,
        dvc_pkg=dvc_pkg,
    )
    readiness = evaluate_readiness(
        financial=financial,
        valuation=valuation,
        sector=sector,
        academy_applied=academy_applied,
        business_quality=business_quality,
        cid=cid,
        leo_pkg=leo_pkg,
        dvc_pkg=dvc_pkg,
        irp_pkg=irp_pkg,
        forecast_learning=forecast_learning,
    )

    executive = (
        f"{identity.get('company_name') or t}: institutional company analysis. "
        f"Business quality {business_quality.get('business_quality_score', 'n/a')}/100. "
        f"Readiness {readiness.get('overall')}% — gate: {readiness.get('gate')}. "
        "Not a recommendation."
    )

    report = {
        "enabled": True,
        "programme": PROGRAMME,
        "version": COMPANY_ANALYSIS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "not_an_engine": True,
        "not_a_recommendation_engine": True,
        "not_an_llm": True,
        "flags": flags_dict(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "ticker": t,
        "executive_summary": executive,
        "business_overview": thesis.get("business_overview"),
        "identity": identity,
        "academy_application": academy_applied,
        "business_quality": business_quality,
        "financial_intelligence": financial,
        "valuation_intelligence": valuation,
        "sector_intelligence": sector,
        "macro_context": {"drivers": thesis.get("macro_drivers") or []},
        "investment_thesis": thesis.get("investment_thesis"),
        "bull_case": thesis.get("bull_case"),
        "bear_case": thesis.get("bear_case"),
        "base_case": thesis.get("base_case"),
        "historical_evolution": thesis.get("historical_evolution"),
        "what_changed": changed,
        "risks": thesis.get("risks") or [],
        "catalysts": thesis.get("catalysts") or [],
        "peer_comparison": {
            "peers": identity.get("peers") or [],
            "valuation": (valuation or {}).get("peer_valuation"),
        },
        "evidence": evidence,
        "confidence": {
            "evidence_confidence": (readiness.get("scores") or {}).get("evidence_confidence"),
            "overall_readiness": readiness.get("overall"),
        },
        "recommendation_readiness": readiness,
        "suggested_follow_up_questions": _followups(identity, sector),
        "answer_policy": "institutional_company_analysis_before_isolated_concepts",
    }

    # Soft-wire Institutional Stack (FIL→FDI→MII→EIL→PIL) — additive only
    try:
        from institutional_stack.production import soft_slice_for_company_analysis

        stack = soft_slice_for_company_analysis(t)
        if stack:
            report["institutional_stack"] = stack.get("institutional_stack") or stack
            summary = (report["institutional_stack"] or {}).get("summary") or {}
            if summary.get("management_dna") or summary.get("management_confidence") is not None:
                report["management_trust"] = {
                    "confidence": summary.get("management_confidence"),
                    "dna": summary.get("management_dna"),
                    "source": "management_intelligence",
                }
            if (
                summary.get("accounting_behaviour")
                or summary.get("accounting_quality_score") is not None
            ):
                report["accounting_trust"] = {
                    "confidence": summary.get("accounting_confidence"),
                    "behaviour": summary.get("accounting_behaviour"),
                    "quality_score": summary.get("accounting_quality_score"),
                    "manipulation_risk": summary.get("manipulation_risk"),
                    "source": "accounting_intelligence",
                }
            # Enrich peer_comparison when PIL present
            pil = ((report["institutional_stack"] or {}).get("layers") or {}).get("peer_intelligence") or {}
            if pil.get("enabled"):
                report["peer_comparison"] = {
                    **(report.get("peer_comparison") or {}),
                    "peer_intelligence": pil,
                }
            # Enrich what_changed when FDI present
            fdi = ((report["institutional_stack"] or {}).get("layers") or {}).get("filing_diff") or {}
            if fdi.get("enabled"):
                changed_block = report.get("what_changed")
                if isinstance(changed_block, dict):
                    changed_block["filing_diff"] = fdi
                elif changed_block is None:
                    report["what_changed"] = {"filing_diff": fdi}
    except Exception:
        pass

    if record and t:
        ca_store.put_report(t, report)
    return report
