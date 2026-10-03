from datetime import datetime, timezone

from research_intelligence_tool.production import (
    build_research_intelligence_package,
    detect_intent,
)


def test_intent_detection():
    assert detect_intent("What changed in ICICI Bank?") == "thesis_change"
    assert detect_intent("What does AGI expect over 5 days?") == "forecast"
    assert detect_intent("Is the forecasting engine working?") == "pipeline_health"


def test_forecast_retrieval_is_gated_and_reports_insufficient_sample():
    calls = []

    def fetch(path):
        calls.append(path)
        if "/forecasts/ICICIBANK" in path:
            return {
                "forecasts": [
                    {
                        "symbol": "ICICIBANK",
                        "horizon": "5d",
                        "forecast_time": "2026-08-09T09:00:00Z",
                        "expected_alpha_pct": 0.9,
                    }
                ]
            }
        return {"observations": 37, "calibrated": False}

    result = build_research_intelligence_package(
        "What does AGI expect over 5 days?",
        entity="ICICIBANK",
        fetcher=fetch,
        now=datetime(2026, 8, 9, 10, 0, tzinfo=timezone.utc),
    )
    assert len(calls) == 2
    assert all(
        "research-memory" not in path and "research-pipeline" not in path
        for path in calls
    )
    assert result["sections"]["FORECAST"]["expected_alpha_pct"] == 0.9
    quality = result["sections"]["DATA_QUALITY"]
    assert quality["forecast_available"] is True
    assert quality["forecast_empirically_calibrated"] is False
    assert quality["validation_sample_size"] == 37
    assert quality["forecast_age"]["age_label"] == "1h"


def test_missing_entity_is_explicit_and_does_not_fetch():
    result = build_research_intelligence_package(
        "Why is it ranked highly?",
        fetcher=lambda _: (_ for _ in ()).throw(AssertionError()),
    )
    assert result["answer_policy"] == "insufficient_entity_do_not_infer"
    assert result["sections"]["DATA_QUALITY"]["missing_components"] == ["entity"]


def test_pipeline_health_only_calls_health():
    calls = []
    result = build_research_intelligence_package(
        "Is the pipeline healthy?",
        fetcher=lambda path: calls.append(path) or {"status": "HEALTHY"},
    )
    assert calls == ["/api/market/research-pipeline/health"]
    assert result["sections"]["CURRENT_EVIDENCE"]["status"] == "HEALTHY"


def test_confluence_uses_live_workspace_items_and_nested_scores():
    result = build_research_intelligence_package(
        "Explain the confluence for ICICI Bank",
        entity="ICICIBANK",
        fetcher=lambda _: {
            "items": [
                {
                    "symbol": "ICICIBANK",
                    "scores": {
                        "fundamental_score": 88,
                        "valuation_score": 76,
                        "eod_confirmation_score": 81,
                        "live_confirmation_score": 84,
                        "catalyst_relevance_score": 60,
                    },
                }
            ]
        },
    )
    assert result["sections"]["CURRENT_EVIDENCE"]["symbol"] == "ICICIBANK"
    assert result["sections"]["DATA_QUALITY"]["missing_components"] == []
