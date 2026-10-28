"""ACI analyse pipeline — trust assessment from profile + FIL soft inputs."""

from __future__ import annotations

from typing import Any

from accounting_intelligence.accounting_policies.score import policy_score
from accounting_intelligence.accruals.score import accruals_score
from accounting_intelligence.balance_sheet_quality.score import balance_sheet_quality
from accounting_intelligence.behaviour.classify import classify_behaviour
from accounting_intelligence.cash_quality.score import cash_quality
from accounting_intelligence.confidence.model import accounting_confidence
from accounting_intelligence.earnings_quality.score import earnings_quality
from accounting_intelligence.evidence.attach import evidence_pack
from accounting_intelligence.forensic.score import forensic_score
from accounting_intelligence.manipulation.detect import detect_manipulation
from accounting_intelligence.profiles.packs import profile_for
from accounting_intelligence.reports.build import build_report
from accounting_intelligence.revenue_recognition.score import revenue_recognition
from accounting_intelligence.schema import ACI_VERSION
from accounting_intelligence.timeline.build import build_timeline
from accounting_intelligence.working_capital.score import working_capital


def analyse_accounting(ticker: str) -> dict[str, Any]:
    profile = profile_for(ticker)
    if not profile:
        return {"ticker": (ticker or "").upper(), "found": False, "aci_version": ACI_VERSION}

    fil_extra: list[dict[str, Any]] = []
    thesis_events: list[dict[str, Any]] = []
    open_concerns: list[str] = []

    # Soft pull FIL narrative / facts (no FIL redesign)
    try:
        from filing_intelligence.production import analyse as fil_analyse

        fil = fil_analyse(profile["ticker"])
        if fil.get("found"):
            narrative = str(fil.get("narrative") or "")
            fil_extra.append(
                {
                    "as_of": profile.get("latest_period"),
                    "period": profile.get("latest_period"),
                    "event": f"FIL soft-ingest: {len(fil.get('timeline') or fil.get('documents') or [])} filing objects",
                    "type": "filing_intelligence",
                }
            )
            if "exceptional items nil" in narrative.lower() or "exceptional items nil" in str(
                fil.get("management") or ""
            ).lower():
                thesis_events.append(
                    {
                        "event": "Exceptional items nil (FIL)",
                        "thesis_impact": "strengthens_thesis",
                        "source": "filing_intelligence",
                    }
                )
            # Bank NIM compression is economic — note as monitoring, not manipulation
            for fact in fil.get("facts") or []:
                if fact.get("metric") == "NIM":
                    open_concerns.append(
                        "NIM pressure visible in filings — test whether earnings quality is economic vs accounting"
                    )
                    thesis_events.append(
                        {
                            "event": "NIM pressure in filings",
                            "thesis_impact": "neutral",
                            "source": "filing_intelligence",
                        }
                    )
                    break
    except Exception:
        pass

    # Soft pull FDI accounting / note changes
    try:
        from filing_diff.pipeline import analyse_diff

        fdi = analyse_diff(profile["ticker"])
        if fdi.get("found"):
            for c in fdi.get("changes") or []:
                domain = str(c.get("domain") or c.get("metric") or "").lower()
                if "account" in domain or "note" in domain or "revenue" in domain:
                    thesis_events.append(
                        {
                            "event": f"FDI: {c.get('metric')} {c.get('change_type')}",
                            "thesis_impact": "critical_review_required"
                            if c.get("materiality") in {"high", "critical"}
                            else "weakens_thesis",
                            "source": "filing_diff",
                        }
                    )
    except Exception:
        pass

    earnings = earnings_quality(profile.get("earnings"))
    cash = cash_quality(profile.get("cash"))
    accruals = accruals_score(profile.get("accruals"))
    revenue = revenue_recognition(profile.get("revenue"))
    wc = working_capital(profile.get("working_capital"))
    bs = balance_sheet_quality(profile.get("balance_sheet"))
    policies = policy_score(list(profile.get("policies") or []))
    forensic = forensic_score(profile.get("forensic"))
    manipulation = detect_manipulation(
        profile_flags=list(profile.get("manipulation_flags") or []),
        earnings=earnings,
        cash=cash,
        accruals=accruals,
        revenue=revenue,
        policies=policies,
        forensic=forensic,
    )
    behaviour = classify_behaviour(
        priors=list(profile.get("behaviour_prior") or []),
        cash=cash,
        earnings=earnings,
        accruals=accruals,
        policies=policies,
        forensic=forensic,
        manipulation=manipulation,
        working_capital=wc,
    )

    unknowns = [
        "Full multi-year cash-flow statement series still expanding via FIL",
        "Detailed DSO/DIO/DPO panels pending denser filing tables",
    ]
    if (profile.get("working_capital") or {}).get("coverage_gap"):
        unknowns.append("Working-capital line items sparse in current FIL stub")
        open_concerns.append("Working-capital coverage gap — enhance FIL tables before high-conviction WC calls")

    for a in manipulation.get("alerts") or []:
        open_concerns.append(str(a.get("flag")))
        thesis_events.append(
            {
                "event": a.get("flag"),
                "thesis_impact": a.get("thesis_impact") or "weakens_thesis",
                "source": "accounting_intelligence",
            }
        )

    ev_cov = min(
        100.0,
        30.0
        + 12.0 * len(profile.get("observations") or [])
        + 8.0 * len(profile.get("policies") or [])
        + (10.0 if profile.get("forensic") else 0.0),
    )
    confidence = accounting_confidence(
        cash_quality=float(cash.get("cash_quality") or 0),
        earnings_quality=float(earnings.get("earnings_quality") or 0),
        working_capital=float(wc.get("working_capital") or 0),
        accounting_consistency=float(policies.get("accounting_consistency") or 0),
        forensic=float(forensic.get("forensic") or 0),
        evidence_coverage=ev_cov,
        unknowns=unknowns,
    )
    evidence = evidence_pack(profile, confidence=confidence)
    timeline = build_timeline(profile, extra=fil_extra)
    report = build_report(
        profile=profile,
        confidence=confidence,
        earnings=earnings,
        cash=cash,
        accruals=accruals,
        revenue=revenue,
        working_capital=wc,
        balance_sheet=bs,
        policies=policies,
        forensic=forensic,
        manipulation=manipulation,
        behaviour=behaviour,
        thesis_events=thesis_events,
        evidence=evidence,
    )

    return {
        "ticker": profile["ticker"],
        "company": profile.get("company"),
        "found": True,
        "aci_version": ACI_VERSION,
        "latest_period": profile.get("latest_period"),
        "earnings": earnings,
        "cash": cash,
        "accruals": accruals,
        "revenue": revenue,
        "working_capital": wc,
        "balance_sheet": bs,
        "policies": policies,
        "forensic": forensic,
        "manipulation": manipulation,
        "behaviour": behaviour,
        "confidence": confidence,
        "evidence": evidence,
        "timeline": timeline,
        "thesis_events": thesis_events,
        "open_concerns": open_concerns,
        "report": report,
        "primary_question": "Can the financial statements be trusted?",
    }
