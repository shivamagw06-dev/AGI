import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from hedge_fund_lab import long_short_equity
from hedge_fund_lab.production import strategy


def test_readiness_blocks_execution_without_short_and_backtest_data():
    out = long_short_equity.readiness()

    assert out["lifecycle"] == "candidate"
    assert out["execution_eligible"] is False
    assert out["market_neutral_claim_allowed"] is False
    assert out["performance_claims_allowed"] is False
    assert "borrow_availability" in out["blocking_datasets"]
    assert "borrow_fee_history" in out["blocking_datasets"]
    assert all(row["status"] == "not_validated" for row in out["promotion_gates"])


def test_strategy_exposes_institutional_readiness():
    out = strategy("long_short_equity")

    assert out["ok"] is True
    assert out["institutional_platform"]["allowed_use"] == "research candidate generation only"


def test_research_book_separates_longs_shorts_and_pairs(monkeypatch):
    def fake_scan(name, limit):
        if name == "alpha":
            return {
                "ok": True,
                "results": [{
                    "ticker": "LONG",
                    "company_name": "Long Co",
                    "factor_scores": {"quality": 80, "value": 70, "growth": 75},
                    "alpha_opportunity_score": 76,
                    "coverage": 0.8,
                    "why": "Independent factors agree.",
                }],
            }
        if name == "stress":
            return {
                "ok": True,
                "results": [{
                    "ticker": "SHORT",
                    "company_name": "Short Co",
                    "stress_flags": ["negative profitability"],
                    "why": "Balance sheet and earnings are stressed.",
                }],
            }
        return {
            "ok": True,
            "results": [{
                "long_leg": {"ticker": "A"},
                "short_leg": {"ticker": "B"},
                "promotion_status": "not_market_neutral",
            }],
        }

    monkeypatch.setattr("hedge_fund_lab.scanner.scan", fake_scan)
    out = long_short_equity.research_book(limit=5)

    assert out["portfolio"] is None
    assert out["long_candidates"][0]["side"] == "long"
    assert out["long_candidates"][0]["position_size"] is None
    assert out["short_candidates"][0]["side"] == "short"
    assert out["short_candidates"][0]["borrow"]["available"] is None
    assert out["short_candidates"][0]["execution_eligible"] is False
    assert out["relative_value_candidates"][0]["market_neutral"] is False
