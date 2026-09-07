"""AQE production facade — health, dashboard, quality gate."""

from __future__ import annotations

from typing import Any, Optional

from ask_product_quality import PROGRAMME, VERSION
from ask_product_quality.confidence import calibrate
from ask_product_quality.evidence_rank import rank_evidence
from ask_product_quality.routing import inspect_routing, routing_accuracy

# Showcase probes for routing / metadata dashboards (no live vendors).
_ROUTING_PROBES = (
    "What is HDFC Bank's business model?",
    "Is Reliance expensive or cheap versus history?",
    "What is equity risk premium?",
    "Compare Infosys vs TCS.",
    "What is Costco's moat?",
    "Axis Bank primary sector",
    "Explain inflation",
    "Why is Ferrari more profitable than Toyota?",
    "What is HDFC Bank market cap?",
    "Compare Visa vs Mastercard.",
)


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "module": "ask_product_quality",
        "programme": PROGRAMME,
        "version": VERSION,
        "constraints": [
            "No new intelligence engines",
            "No live vendor calls during Ask",
            "IFAC remains the composition layer",
            "Warehouse → engines → IFAC path preserved",
        ],
    }


def dashboard() -> dict[str, Any]:
    inspections = [inspect_routing(q) for q in _ROUTING_PROBES]
    accuracy = routing_accuracy(inspections)
    metadata_n = sum(1 for i in inspections if i.get("metadata_route"))
    pedagogy_n = sum(1 for i in inspections if (i.get("entity") or {}).get("pedagogy_only"))
    domains: dict[str, int] = {}
    for i in inspections:
        d = str(i.get("domain") or "unknown")
        domains[d] = domains.get(d, 0) + 1

    targets = {
        "routing_accuracy": 95.0,
        "metadata_accuracy": 99.0,
        "institutional_template_coverage": 100.0,
        "answer_completeness": 95.0,
        "evidence_coverage": 95.0,
        "consensus_headline_rate": 0.0,
        "hallucination_rate": 0.0,
        "regression_pass_rate": 95.0,
    }
    return {
        "ok": True,
        "programme": PROGRAMME,
        "version": VERSION,
        "targets": targets,
        "routing": {
            **accuracy,
            "metadata_routes": metadata_n,
            "pedagogy_only": pedagogy_n,
            "domains": domains,
            "probes": inspections,
        },
        "metrics": {
            "routing_accuracy": accuracy.get("accuracy_pct"),
            "metadata_probe_count": metadata_n,
            "pedagogy_probe_count": pedagogy_n,
        },
        "note": (
            "AQE dashboard probes local planners only. Full regression scores come "
            "from Production Release Gate artifacts."
        ),
    }


def quality_gate(
    payload: dict[str, Any],
    *,
    question: str = "",
) -> dict[str, Any]:
    """DQIV-style product quality checks on an Ask/KUL/IFAC payload."""
    issues: list[str] = []
    summary = str(
        payload.get("summary")
        or (payload.get("answer") or {}).get("summary")
        or payload.get("executive_summary")
        or ""
    ).strip()
    if not summary:
        issues.append("empty_summary")

    ei = payload.get("entity_intelligence") or {}
    identity = ((payload.get("company_intelligence") or {}).get("identity") or {})
    ticker = identity.get("ticker") or payload.get("ticker") or ei.get("ticker")
    state = ei.get("state")
    if state == "unsupported_entity" and not ei.get("allow_planner") and not payload.get("pedagogy_only"):
        # Honest refusal is OK — not a DQIV fail.
        pass
    elif state == "clarification_required":
        pass
    elif question and not ticker and not state and "company" in question.lower():
        issues.append("primary_entity_unresolved")

    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    providers = list(payload.get("providers_used") or sources)
    if providers == ["legacy_kip"]:
        issues.append("generic_retrieval_only")

    low = summary.lower()
    if any(
        p in low
        for p in (
            "based on retrieved evidence for the subject",
            "indian stock market q&a",
            "for unknown,",
            "business type: unknown",
        )
    ):
        issues.append("unsupported_conclusion_or_boilerplate")

    if "consensus target" in low and "capital iq market consensus" in low:
        # Consensus as sole headline is a demotion failure when no AGIB engine present.
        agib = {
            "business_intelligence",
            "research_intelligence_engine",
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "forecast_intelligence_engine",
            "macro_intelligence_engine",
        }
        if not agib.intersection(set(providers)):
            issues.append("consensus_promoted_above_agib")

    conf = payload.get("confidence")
    if conf is None and payload.get("aqe_confidence") is None:
        # Soft: note missing confidence rather than hard-fail every legacy path.
        issues.append("confidence_missing")

    evidence = list(payload.get("evidence") or payload.get("evidence_used") or [])
    ranked = rank_evidence(evidence if isinstance(evidence, list) else [], question=question)
    aqe_conf = calibrate(
        overall=conf if isinstance(conf, (int, float)) else None,
        evidence_count=len(ranked),
        missing_data=list(payload.get("missing_data") or []),
        entity_confidence=ei.get("confidence") if isinstance(ei.get("confidence"), (int, float)) else None,
        providers_used=providers,
        warehouse_freshness=payload.get("warehouse_freshness"),
    )

    return {
        "ok": len(issues) == 0 or issues == ["confidence_missing"],
        "hard_fail": bool(
            set(issues)
            - {
                "confidence_missing",
            }
        ),
        "issues": issues,
        "ranked_evidence": ranked[:8],
        "aqe_confidence": aqe_conf,
        "version": VERSION,
    }


def enrich_answer(payload: dict[str, Any], *, question: str = "") -> dict[str, Any]:
    """Non-breaking enrichment: attach AQE confidence + ranked evidence."""
    gate = quality_gate(payload, question=question)
    out = dict(payload)
    out["aqe"] = {
        "version": VERSION,
        "programme": PROGRAMME,
        "quality_ok": gate.get("ok"),
        "issues": gate.get("issues"),
        "confidence": gate.get("aqe_confidence"),
    }
    if gate.get("ranked_evidence"):
        out["aqe"]["ranked_evidence"] = gate["ranked_evidence"]
    return out
