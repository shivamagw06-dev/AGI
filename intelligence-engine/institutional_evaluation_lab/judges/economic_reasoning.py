"""Deterministic economic-reasoning evaluator for structured AGI answers."""
from __future__ import annotations
from typing import Any

DIMENSIONS = (
    "evidence", "causality", "financial_impact", "valuation", "risk_analysis",
    "monitoring", "epistemic_separation", "decision_relevance", "client_usefulness",
)

def _present(answer: dict[str, Any], *keys: str) -> bool:
    return any(bool(answer.get(key)) for key in keys)

def evaluate_answer(answer: dict[str, Any]) -> dict[str, Any]:
    layers = answer.get("epistemic_layers") or {}
    checks = {
        "evidence": _present(answer, "evidence", "sources") and not answer.get("fabricated", False),
        "causality": _present(answer, "why", "financial_transmission"),
        "financial_impact": _present(answer, "financial_transmission", "financial_impact"),
        "valuation": _present(answer, "valuation", "market_expectations") or "valuation" in (answer.get("evidence_gaps") or []),
        "risk_analysis": _present(answer, "bear_case", "risks", "what_changes_view"),
        "monitoring": _present(answer, "monitoring") and _present(answer, "what_changes_view"),
        "epistemic_separation": all(key in layers for key in ("evidence", "interpretation", "scenario", "thesis")),
        "decision_relevance": str(answer.get("decision_relevance") or "") in {
            "THESIS_STRENGTHENS", "THESIS_WEAKENS", "VALUATION_CHANGES", "RISK_INCREASES",
            "RISK_DECREASES", "NO_MATERIAL_CHANGE", "INSUFFICIENT_EVIDENCE",
        },
        "client_usefulness": _present(answer, "direct_conclusion") and _present(answer, "why") and bool(answer.get("confidence")),
    }
    scores = {key: 10 if value else 0 for key, value in checks.items()}
    overall = round(sum(scores.values()) / len(scores), 2)
    return {"dimensions": scores, "overall": overall, "passed": overall >= 8.0,
            "missing": [key for key, value in checks.items() if not value], "deterministic": True}

def evaluate_industry_models() -> dict[str, Any]:
    from industry_intelligence.dna_catalog import INDUSTRY_DNA
    from causal_graph.graph.store import graph_snapshot
    graph = graph_snapshot()
    graph_sectors = set(graph.get("sectors_modelled") or [])
    company_sectors = {
        str(node.get("sector")) for node in (graph.get("nodes") or [])
        if node.get("type") == "company" and node.get("sector")
    }
    rows = []
    required = ("revenue_drivers", "margin_drivers", "cost_drivers", "value_drivers", "valuation_methods",
                "typical_risks", "macro_sensitivity", "kpis", "why_margins", "why_roic", "why_valuation")
    for key, dna in sorted(INDUSTRY_DNA.items()):
        missing = [field for field in required if not getattr(dna, field)]
        kpi_relationships = sum(bool(k.relationships) for k in dna.kpis)
        actionable_kpis = sum(bool(k.importance and k.good_range and k.poor_range) for k in dna.kpis)
        knowledge = 3 * (len(required) - len(missing)) / len(required)
        causal = 2 * kpi_relationships / max(1, len(dna.kpis))
        graph_coverage = 2.0 if key in graph_sectors else 0.0
        company_coverage = 1.0 if key in company_sectors else 0.0
        valuation = 1.0 if dna.valuation_methods and dna.valuation_why else 0.0
        monitoring = 1.0 * actionable_kpis / max(1, len(dna.kpis))
        score = round(knowledge + causal + graph_coverage + company_coverage + valuation + monitoring, 2)
        gaps = list(missing)
        if not graph_coverage: gaps.append("causal_graph_coverage")
        if not company_coverage: gaps.append("gold_company_link")
        rows.append({"industry": key, "score": score, "knowledge_coverage": round(knowledge, 2),
                     "kpi_causality": round(causal, 2), "causal_graph": graph_coverage,
                     "company_linkage": company_coverage, "valuation": valuation,
                     "monitoring": round(monitoring, 2), "missing": gaps,
                     "kpi_count": len(dna.kpis), "passed": score >= 8.0})
    return {"industry_count": len(rows), "passed": sum(x["passed"] for x in rows),
            "pass_pct": round(100 * sum(x["passed"] for x in rows) / max(1, len(rows)), 2),
            "mean_score": round(sum(x["score"] for x in rows) / max(1, len(rows)), 2), "rows": rows}
