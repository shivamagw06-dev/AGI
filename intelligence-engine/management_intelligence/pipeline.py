"""MII analyse pipeline — trust assessment from profile + FIL/FDI soft inputs."""

from __future__ import annotations

from typing import Any

from management_intelligence.capital_allocator.score import capital_allocation_score
from management_intelligence.communication.score import communication_score
from management_intelligence.confidence.model import management_confidence
from management_intelligence.credibility_engine.score import credibility_score
from management_intelligence.dna.classify import classify_dna
from management_intelligence.evidence.attach import evidence_pack
from management_intelligence.execution.score import execution_score
from management_intelligence.governance.score import governance_score
from management_intelligence.guidance_tracker.score import guidance_score
from management_intelligence.incentives.score import incentive_score
from management_intelligence.management_profiles.packs import profile_for
from management_intelligence.reports.build import build_report
from management_intelligence.schema import MII_VERSION
from management_intelligence.strategic_decisions.journal import decision_journal
from management_intelligence.succession.score import succession_score
from management_intelligence.timeline.build import build_timeline


def analyse_management(ticker: str) -> dict[str, Any]:
    profile = profile_for(ticker)
    if not profile:
        return {"ticker": ticker.upper(), "found": False, "mii_version": MII_VERSION}

    # Soft pull FDI optimism / thesis signals when available (no FDI redesign)
    fdi_optimism = None
    fdi_extra_timeline: list[dict[str, Any]] = []
    open_concerns: list[str] = []
    thesis_events: list[dict[str, Any]] = []
    try:
        from filing_diff.pipeline import analyse_diff

        fdi = analyse_diff(profile["ticker"])
        if fdi.get("found"):
            for c in fdi.get("changes") or []:
                if c.get("metric") == "Optimism" and c.get("change_type") == "optimism_decreased":
                    fdi_optimism = "optimism_decreased"
                    thesis_events.append(
                        {
                            "event": "Management tone more cautious (FDI)",
                            "thesis_impact": "needs_monitoring",
                            "source": "filing_diff",
                        }
                    )
                ct = str(c.get("change_type") or "")
                if c.get("metric") in {"CASA", "NIM"} and (
                    "decline" in ct or "compression" in ct
                ):
                    open_concerns.append(
                        f"{c.get('metric')} {ct} detected by FDI — test liability franchise credibility"
                    )
                    thesis_events.append(
                        {
                            "event": f"{c.get('metric')} {ct}",
                            "thesis_impact": "weakens_thesis"
                            if c.get("materiality") in {"high", "critical"}
                            else "needs_monitoring",
                            "source": "filing_diff",
                        }
                    )
            fdi_extra_timeline.append(
                {
                    "as_of": fdi.get("current_period"),
                    "event": f"FDI compare {fdi.get('previous_period')}→{fdi.get('current_period')}: "
                    f"{len(fdi.get('changes') or [])} material changes",
                    "type": "filing_diff",
                }
            )
    except Exception:
        pass

    guidance = guidance_score(list(profile.get("guidance_events") or []))
    credibility = credibility_score(list(profile.get("credibility_claims") or []))
    execution = execution_score(list(profile.get("execution") or []))
    capital = capital_allocation_score(
        list(profile.get("capital_allocation") or []),
        list(profile.get("acquisitions") or []),
    )
    governance = governance_score(profile.get("board"), list(profile.get("governance_events") or []))
    communication = communication_score(profile.get("communication"), fdi_optimism=fdi_optimism)
    incentives = incentive_score(profile.get("incentives"))
    succession = succession_score(profile.get("succession"))
    dna = classify_dna(
        priors=list(profile.get("dna_prior") or []),
        capital=capital,
        execution=execution,
        guidance=guidance,
        credibility=credibility,
        acquisitions=list(profile.get("acquisitions") or []),
    )

    # evidence coverage from claim/guidance/decision counts
    ev_cov = min(
        100.0,
        25.0
        + 10.0 * len(profile.get("guidance_events") or [])
        + 10.0 * len(profile.get("credibility_claims") or [])
        + 8.0 * len(profile.get("capital_allocation") or []),
    )
    confidence = management_confidence(
        credibility=float(credibility.get("credibility") or 0),
        execution=float(execution.get("execution") or 0),
        capital_allocation=float(capital.get("capital_allocation") or 0),
        governance=float(governance.get("governance") or 0),
        communication=float(communication.get("communication") or 0),
        evidence_coverage=ev_cov,
    )
    evidence = evidence_pack(profile, confidence=confidence)
    timeline = build_timeline(profile, extra=fdi_extra_timeline)
    journal = decision_journal(profile)

    if credibility.get("incorrect", 0) >= 1:
        open_concerns.append("At least one tracked management claim marked incorrect — credibility watch")
        thesis_events.append(
            {
                "event": "Credibility claim miss",
                "thesis_impact": "committee_review_required",
                "source": "credibility_engine",
            }
        )
    if execution.get("delayed", 0) >= 1:
        open_concerns.append("Strategic initiative delayed vs plan")

    leadership = {
        "executives": profile.get("executives"),
        "board": profile.get("board"),
        "succession": succession,
    }

    bundle = {
        "ticker": profile["ticker"],
        "company": profile.get("company"),
        "found": True,
        "mii_version": MII_VERSION,
        "primary_question": "Can this management team be trusted to compound shareholder value?",
        "leadership": leadership,
        "guidance": guidance,
        "credibility": credibility,
        "execution": execution,
        "capital": capital,
        "governance": governance,
        "communication": communication,
        "incentives": incentives,
        "succession": succession,
        "dna": dna,
        "confidence": confidence,
        "evidence": evidence,
        "timeline": timeline,
        "decision_journal": journal,
        "open_concerns": open_concerns,
        "thesis_events": thesis_events,
    }
    report = build_report(bundle)
    bundle["report"] = report
    return bundle
