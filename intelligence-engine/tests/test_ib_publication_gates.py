"""IB publication gates — buy-side PM bar (Reliance review encoded)."""

from __future__ import annotations

from institutional_grade_benchmark.production import publication_gates_api
from institutional_grade_benchmark.publication_gates import (
    PUBLICATION_GATES,
    evaluate_publication_readiness,
    evaluate_reliance_note_as_reviewed,
)


def test_seven_blocking_gates_defined():
    assert len(PUBLICATION_GATES) == 7
    assert all(g["blocks_publication"] for g in PUBLICATION_GATES)


def test_reliance_ground_truth_fails_all_blocking_gates():
    out = evaluate_reliance_note_as_reviewed()
    assert out["publication_allowed"] is False
    assert out["scaffold_only"] is True
    assert out["gates_passed"] == 0
    assert len(out["blocking_failures"]) == 7
    assert out["pm_overall_score"] == 67.0
    assert "Don't publish" in out["pm_verdict"]
    assert "G6_evidence_links" in out["blocking_failures"]
    assert "G7_contradiction_check" in out["blocking_failures"]
    assert "G4_valuation" in out["blocking_failures"]


def test_passing_note_is_publication_allowed():
    note = {
        "thesis_bullets": [
            "Retail EBIT compounding above consensus",
            "Jio ARPU expansion with disciplined capex",
            "O2C normalized margins support FCF",
            "SOTP implies material holding discount",
        ],
        "financial_metrics": {
            "revenue": [1, 2, 3, 4, 5],
            "ebitda": [1, 2, 3, 4, 5],
            "net_debt": 10,
            "fcf": 2,
            "roce": 0.12,
            "margins": 0.15,
        },
        "has_ttm": True,
        "has_5y_history": True,
        "segment_economics": {
            "O2C": {"revenue": 100, "ebitda": 20, "margin": 0.2},
            "Retail": {"revenue": 80, "growth": 0.18},
            "Jio": {"revenue": 60, "arpu_trend": "up"},
            "New Energy": {"capex": 15, "revenue": 1},
        },
        "valuation": {
            "sotp": {"equity_value": 100, "discount": 0.2},
            "peers": [{"ticker": "PEER", "ev_ebitda": 12}],
            "ev_ebitda": 11,
            "sensitivity": {"oil": [-5, 0, 5]},
        },
        "decision_triggers": {
            "upgrade_to_buy": ["SOTP upside > 20% with stable O2C"],
            "downgrade_to_sell": ["Net debt/EBITDA > threshold with FCF miss"],
        },
        "evidence_links": [
            {"claim": "revenue", "source_type": "annual_report", "uri": "ar://2025"},
            {"claim": "segment", "source_type": "quarterly", "uri": "qr://q4"},
            {"claim": "capex", "source_type": "earnings", "uri": "ppt://q4"},
            {"claim": "stake", "source_type": "exchange", "uri": "nse://filing"},
        ],
        "primary_filings_count": 4,
        "recommendation": "NEUTRAL",
        "recommendations": ["NEUTRAL"],
        "scenario_probabilities": {"bull": 0.2, "base": 0.6, "bear": 0.2},
        "numeric_density_ok": True,
        "fabricated_numbers": False,
    }
    out = evaluate_publication_readiness(note)
    assert out["publication_allowed"] is True
    assert out["gates_passed"] == 7
    assert out["blocking_failures"] == []
    assert out["enhancers"][0]["passed"] is True


def test_api_reliance_case():
    out = publication_gates_api({"case": "reliance"})
    assert out["ok"] is True
    assert out["publication_allowed"] is False
    assert out["pm_overall_score"] == 67.0
