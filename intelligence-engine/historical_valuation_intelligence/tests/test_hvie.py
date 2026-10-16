"""Phase 8.3 — Historical Valuation Intelligence Engine contract tests."""

from __future__ import annotations

from historical_valuation_intelligence import health
from historical_valuation_intelligence.ask import answer_for, is_historical_valuation_question
from historical_valuation_intelligence.dqiv import validate_observation, validate_series
from historical_valuation_intelligence.engine import (
    bands_for,
    company_pack,
    coverage_for,
    regimes_for,
    rerating_for,
    statistics_for,
)
from historical_valuation_intelligence.statistics import (
    all_window_stats,
    compute_stats,
    filter_points,
    regime_from_percentile,
)


def _points(n=40, start_pe=15.0, step=0.5):
    rows = []
    for i in range(n):
        year = 2015 + (i // 12)
        month = (i % 12) + 1
        rows.append({
            "period": f"{year}-{month:02d}-15",
            "date": f"{year}-{month:02d}-15",
            "value": start_pe + i * step,
            "source": "warehouse_reconstruction",
        })
    return rows


def test_health_contract():
    h = health()
    assert h["ok"] is True
    assert h["version"] == "8.3B"
    assert h["vendor_historical_ratios"] is False
    assert h.get("reconstruction_version") == "8.3B"
    assert "1y" in h["windows"] and "15y" in h["windows"] and "max" in h["windows"]
    assert any("/v1/hvie/company/" in e for e in (h.get("endpoints") or []))


def test_statistics_windows_and_percentile():
    points = _points()
    stats = compute_stats(points)
    assert stats["ok"] is True
    assert stats["observation_count"] == 40
    assert stats["current_percentile"] is not None
    assert stats["min"] <= stats["median"] <= stats["max"]
    assert stats["p25"] <= stats["p75"]

    by_window = all_window_stats(points)
    assert set(by_window) >= {"1y", "3y", "5y", "10y", "15y", "20y", "max"}
    assert by_window["max"]["ok"] is True


def test_regime_classification():
    assert regime_from_percentile(10)["regime"] == "VERY_CHEAP"
    assert regime_from_percentile(50)["regime"] == "FAIR"
    assert regime_from_percentile(90)["regime"] == "VERY_EXPENSIVE"


def test_dqiv_rejects_non_positive_pe():
    bad = validate_observation({"date": "2020-01-01", "pe": -5})
    assert bad["ok"] is False
    assert "non_positive_pe" in bad["errors"]

    extreme = validate_observation({"date": "2020-01-01", "pe": 600})
    assert extreme["ok"] is True
    assert extreme["status"] == "warn"

    series = validate_series(
        [{"period": "2020-01-01", "value": 20}, {"period": "2020-01-01", "value": 21}],
        "pe",
    )
    assert series["ok"] is False
    assert any("duplicate" in e for e in series["errors"])


def test_filter_window():
    points = _points(n=120, start_pe=10, step=0.1)
    filtered = filter_points(points, window="1y")
    assert len(filtered) < len(points)


def test_engine_with_mocked_history(monkeypatch):
    points = _points(n=60, start_pe=12, step=0.3)

    def fake_load(symbol, metric):
        return list(points)

    def fake_policy(symbol):
        return {
            "ok": True,
            "primary_model": "PE",
            "primary_metric": "pe",
            "status": "VALID",
            "confidence": "HIGH",
            "hidden_metrics": [],
            "unavailable_metrics": [],
            "metrics": {},
        }

    monkeypatch.setattr(
        "historical_valuation_intelligence.engine._load_points", fake_load
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.engine._policy", fake_policy
    )

    stats = statistics_for("INFY", metric="pe", window="max")
    assert stats["ok"] is True
    assert stats["stats"]["observation_count"] == 60
    assert stats["regime"]["regime"] in {
        "VERY_CHEAP", "CHEAP", "FAIR", "EXPENSIVE", "VERY_EXPENSIVE"
    }

    bands = bands_for("INFY", metric="pe", window="max")
    assert bands["ok"] is True
    assert bands["min"] <= bands["median"] <= bands["max"]

    regimes = regimes_for("INFY", metric="pe")
    assert regimes["ok"] is True
    assert regimes["regime"]

    rr = rerating_for("INFY", metric="pe", window="max")
    assert rr["ok"] is True
    assert rr["cheapest"]["value"] <= rr["richest"]["value"]
    assert rr["direction"] in {"RERATING", "DERATING", "STABLE"}

    cov = coverage_for("INFY", metric="pe")
    assert cov["ok"] is True
    assert cov["metrics"]["pe"]["observation_count"] == 60
    assert cov["vendor_historical_ratios"] is False

    pack = company_pack("INFY", metric="pe", window="max")
    assert pack["ok"] is True
    assert pack["current"] is not None
    assert pack["historical_percentile"] is not None
    assert pack["vendor_historical_ratios"] is False
    assert "valuation_policy" in " ".join(pack["data_sources"])


def test_vpae_hides_pe_for_bank(monkeypatch):
    def fake_policy(symbol):
        return {
            "ok": True,
            "primary_model": "PRICE_TO_BOOK",
            "primary_metric": "pb",
            "status": "BANKING_MODEL",
            "confidence": "HIGH",
            "hidden_metrics": ["ev_ebitda", "ev_sales"],
            "unavailable_metrics": [],
            "metrics": {
                "ev_ebitda": {
                    "status": "Hidden",
                    "reason": "EV not meaningful for banks.",
                }
            },
        }

    monkeypatch.setattr(
        "historical_valuation_intelligence.engine._policy", fake_policy
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.engine._load_points",
        lambda *a, **k: _points(),
    )

    stats = statistics_for("HDFCBANK", metric="ev_ebitda", window="max")
    assert stats["ok"] is False
    assert stats["status"] == "NOT_APPLICABLE"


def test_ask_helpers(monkeypatch):
    assert is_historical_valuation_question("Is Infosys expensive?")
    assert is_historical_valuation_question("When was TCS cheapest?")
    assert is_historical_valuation_question("Has HDFC Bank ever traded cheaper?")

    monkeypatch.setattr(
        "historical_valuation_intelligence.ask.company_pack",
        lambda symbol, metric=None, window="10y": {
            "ok": True,
            "symbol": symbol,
            "metric": "pe",
            "current": 28.4,
            "median": 23.1,
            "historical_percentile": 84.0,
            "premium_to_median_pct": 22.9,
            "regime": "EXPENSIVE",
            "confidence": "HIGH",
            "coverage": {"coverage_label": "2002 → 2026 · 24 years · 5946 observations"},
            "max_window": {"median": 22.0},
        },
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.ask.regimes_for",
        lambda *a, **k: {"regime": "EXPENSIVE"},
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.ask.rerating_for",
        lambda *a, **k: {"cheapest": {"value": 11.4, "date": "2009-03-15"}},
    )

    ans = answer_for("INFY", "Is Infosys expensive?")
    assert ans["ok"] is True
    assert "28.4" in ans["answer"]
    assert "EXPENSIVE" in ans["answer"]

    cheap = answer_for("TCS", "When was TCS cheapest?")
    assert "11.4" in cheap["answer"]
    assert "2009" in cheap["answer"]
