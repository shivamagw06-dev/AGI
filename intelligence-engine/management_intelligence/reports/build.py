"""Management Intelligence Report — trust assessment, not commentary dump."""

from __future__ import annotations

from typing import Any

from management_intelligence.schema import MII_VERSION


def build_report(bundle: dict[str, Any]) -> dict[str, Any]:
    ticker = bundle["ticker"]
    conf = bundle.get("confidence") or {}
    dna = bundle.get("dna") or {}
    guidance = bundle.get("guidance") or {}
    cred = bundle.get("credibility") or {}
    exe = bundle.get("execution") or {}
    cap = bundle.get("capital") or {}
    gov = bundle.get("governance") or {}
    comm = bundle.get("communication") or {}

    thesis_events = bundle.get("thesis_events") or []
    exec_summary = [
        f"Management Intelligence — {ticker}",
        f"Primary question: Can management be trusted to compound shareholder value?",
        f"Management Confidence: {conf.get('confidence')} — {conf.get('explain')}",
        f"Management DNA: {dna.get('primary')} (secondary: {', '.join(dna.get('secondary') or [])})",
        f"Guidance Score: {guidance.get('guidance_score')} | Credibility: {cred.get('credibility')} | "
        f"Execution: {exe.get('execution')} | Capital Allocation: {cap.get('capital_allocation')}",
    ]

    text = "\n".join(
        [
            f"Management Intelligence Report — {ticker}",
            f"MII {MII_VERSION}",
            "",
            "EXECUTIVE SUMMARY",
            *exec_summary,
            "",
            "MANAGEMENT DNA",
            str(dna),
            "",
            "CONFIDENCE",
            conf.get("explain") or "",
            "",
            "RULE",
            "No subjective opinion without evidence. Never Buy/Sell.",
        ]
    )

    return {
        "ticker": ticker,
        "mii_version": MII_VERSION,
        "executive_summary": "\n".join(exec_summary),
        "management_quality": {
            "confidence": conf.get("confidence"),
            "dna": dna.get("primary"),
            "guidance_score": guidance.get("guidance_score"),
            "credibility": cred.get("credibility"),
            "execution": exe.get("execution"),
            "capital_allocation": cap.get("capital_allocation"),
            "governance": gov.get("governance"),
            "communication": comm.get("communication"),
        },
        "leadership_assessment": bundle.get("leadership"),
        "guidance_accuracy": guidance,
        "execution_record": exe,
        "capital_allocation": cap,
        "governance": gov,
        "communication_quality": comm,
        "strategic_decisions": bundle.get("decision_journal"),
        "acquisition_review": cap.get("acquisitions"),
        "incentive_alignment": bundle.get("incentives"),
        "succession": bundle.get("succession"),
        "historical_timeline": bundle.get("timeline"),
        "management_dna": dna,
        "confidence": conf,
        "evidence": bundle.get("evidence"),
        "missing_evidence": conf.get("unknowns") or [],
        "thesis_impact_events": thesis_events,
        "committee": {
            "management_dashboard": {
                "confidence": conf.get("confidence"),
                "dna": dna.get("primary"),
                "credibility_trend": cred,
                "guidance_score": guidance.get("guidance_score"),
                "open_concerns": bundle.get("open_concerns") or [],
            },
            "credibility_trend": cred,
            "execution_history": exe.get("items"),
            "open_concerns": bundle.get("open_concerns") or [],
        },
        "cio_brief": (
            f"{ticker} management confidence {conf.get('confidence')}/100 "
            f"(DNA: {dna.get('primary')}). "
            f"Credibility {cred.get('credibility')}, guidance {guidance.get('guidance_score')}, "
            f"execution {exe.get('execution')}, capital {cap.get('capital_allocation')}."
        ),
        "text": text,
        "rule": "Evaluate delivery and trust — do not merely report what management said",
    }
