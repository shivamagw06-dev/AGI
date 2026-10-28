"""DVC V1 — Data Validation & Consensus platform tests (not an engine)."""

from __future__ import annotations

import pytest

from dvc.conflicts import conflict_summary, detect_conflicts
from dvc.consensus import consensus_for_field
from dvc.enrich import merge_dvc_into_dossier
from dvc.learning import compute_adjusted_confidence, empty_provider_stats, record_fetch
from dvc.models import make_validated_field
from dvc.priority import base_confidence, provider_priority
from dvc.production import (
    is_dvc_enabled,
    package_for_ask_agi,
    production_dashboard,
    quality_gates,
)
from dvc.quality import compute_quality, grade_from_quality
from dvc.schema import DVC_VERSION
from dvc import store as dvc_store
from dvc.validate import ask_agi_hints, build_consensus_package, panel_for_company


@pytest.fixture(autouse=True)
def _clean_store():
    dvc_store.reset_for_tests()
    yield
    dvc_store.reset_for_tests()


def test_provider_priority_order():
    assert provider_priority("official_exchange") < provider_priority("indianapi")
    assert provider_priority("indianapi") < provider_priority("finnhub")
    assert provider_priority("finnhub") < provider_priority("fmp")
    assert provider_priority("fmp") < provider_priority("yahoo")
    assert base_confidence("indianapi") > base_confidence("yahoo")


def test_consensus_numeric_prefers_indianapi():
    obs = [
        {"provider": "indianapi", "value": 1245.40},
        {"provider": "finnhub", "value": 1245.35},
        {"provider": "yahoo", "value": 1245.50},
    ]
    vf = consensus_for_field("last", obs, symbol="INFY")
    assert vf["provider"] == "indianapi"
    assert vf["value"] == pytest.approx(1245.40)
    assert vf["confidence"] >= 0.9
    assert "yahoo" in (vf.get("rejected_providers") or []) or vf.get("validation_status")


def test_validated_field_metadata():
    vf = make_validated_field(
        field="last",
        value=1245.40,
        provider="indianapi",
        confidence=0.99,
        symbol="INFY",
        fallback_provider="yahoo",
        previous_value=1244.90,
    )
    assert vf["field"] == "last"
    assert vf["provider"] == "indianapi"
    assert vf["verified_at"]
    assert vf["version"].startswith("v-")
    assert vf["change_percent"] is not None
    assert vf["dvc_version"] == DVC_VERSION


def test_conflict_detection_market_cap():
    obs = {
        "market_cap": [
            {"provider": "indianapi", "value": 1_000_000_000_000},
            {"provider": "yahoo", "value": 1_300_000_000_000},
        ]
    }
    reports = detect_conflicts(obs, company_id="INFY")
    assert any(r["field"] == "market_cap" for r in reports)
    assert reports[0]["winning_provider"] == "indianapi"
    assert reports[0]["severity"] in ("medium", "high", "critical")
    summary = conflict_summary(reports)
    assert summary["total"] >= 1


def test_quality_and_grades():
    fields = {
        "last": make_validated_field(
            field="last", value=100.0, provider="indianapi", confidence=0.97, symbol="INFY"
        ),
        "market_cap": make_validated_field(
            field="market_cap",
            value=1e12,
            provider="indianapi",
            confidence=0.96,
            symbol="INFY",
        ),
    }
    q = compute_quality(fields, conflicts=[], observations_by_field={}, kind="combined")
    assert 0 <= q["overall"] <= 1
    grades = grade_from_quality(q)
    assert "research_grade" in grades
    assert "data_grade" in grades
    assert "gates" in grades


def test_learning_adjusts_confidence():
    stats = empty_provider_stats("indianapi")
    stats = record_fetch(stats, ok=True, latency_ms=40)
    stats = record_fetch(stats, ok=True, latency_ms=50)
    stats = record_fetch(stats, ok=False, latency_ms=200)
    adj = compute_adjusted_confidence(stats)
    assert 0.35 <= adj <= 0.995


def test_build_consensus_package_and_store():
    obs = {
        "last": [
            {"provider": "indianapi", "value": 1245.40},
            {"provider": "finnhub", "value": 1245.35},
            {"provider": "yahoo", "value": 1245.50},
        ],
        "market_cap": [
            {"provider": "indianapi", "value": 1e12},
            {"provider": "yahoo", "value": 1.25e12},
        ],
    }
    pack = build_consensus_package("INFY", obs, kind="combined")
    assert pack["winning_provider_summary"] == "indianapi"
    assert "last" in pack["validated_fields"]
    assert pack["conflict_summary"]["total"] >= 1
    stored = dvc_store.upsert_company_validation("INFY", pack)
    got = dvc_store.get_company("INFY")
    assert got and got["company_id"] == "INFY"
    assert stored["validated_fields"]["last"]["provider"] == "indianapi"


def test_ask_agi_hints_mention_conflicts():
    obs = {
        "market_cap": [
            {"provider": "indianapi", "value": 1e12},
            {"provider": "yahoo", "value": 1.3e12},
        ]
    }
    pack = build_consensus_package("INFY", obs)
    pack["enabled"] = True
    hints = ask_agi_hints(pack)
    assert any("Market capitalisation" in h or "market" in h.lower() for h in hints)


def test_merge_into_dossier_attaches_panel():
    dossier = {"ticker": "INFY", "market_data": {}, "identity": {}}
    obs = {
        "last": [{"provider": "indianapi", "value": 1500.0}],
        "sector": [{"provider": "yahoo", "value": "Technology"}],
    }
    pack = build_consensus_package("INFY", obs)
    pack["enabled"] = True
    merged = merge_dvc_into_dossier(dossier, pack)
    assert merged["market_data"].get("current_price") == 1500.0
    assert merged.get("validated_fields")
    assert merged.get("data_quality_panel")
    assert merged["dvc"]["dvc_version"] == DVC_VERSION
    panel = panel_for_company(pack)
    assert "research_grade" in panel


def test_production_dashboard_and_gates():
    assert is_dvc_enabled() is True
    dash = production_dashboard()
    assert dash["programme"] == "DVC"
    assert dash["not_an_engine"] is True
    assert dash["not_a_provider"] is True
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["checks"]["consensus_winner_indianapi"] is True


def test_package_for_ask_agi_policy():
    obs = {"last": [{"provider": "indianapi", "value": 10.0}]}
    pack = build_consensus_package("INFY", obs)
    dvc_store.upsert_company_validation("INFY", pack)
    pkg = package_for_ask_agi("INFY")
    assert pkg["answer_policy"] == "validated_canonical_values_only"
    assert pkg["validated_fields"]["last"]["value"] == 10.0


@pytest.mark.asyncio
async def test_market_data_client_validated_package_soft_path():
    from app.core.config import get_settings
    from app.market_data.client import MarketDataClient
    from app.market_data.models import MarketDataQuote, Provenance
    from app.market_data.provider_base import MarketDataProvider
    from datetime import datetime, timezone

    class FakeProvider(MarketDataProvider):
        def __init__(self, pid: str, last: float, priority: int = 10):
            self.provider_id = pid
            self.priority = priority
            self._last = last

        def is_configured(self) -> bool:
            return True

        def capabilities(self):
            return {"quote", "fundamental"}

        async def get_quote(self, symbol: str) -> MarketDataQuote:
            return MarketDataQuote(
                symbol=symbol.upper(),
                last=self._last,
                currency="INR",
                provenance=Provenance(
                    source=self.provider_id,
                    provider_id=self.provider_id,
                    pulled_at=datetime.now(timezone.utc),
                ),
            )

        async def get_fundamentals(self, symbol: str):
            from app.market_data.models import FundamentalSnapshot

            return FundamentalSnapshot(
                symbol=symbol.upper(),
                metrics={"market_cap": self._last * 1_000_000_000, "sector": "IT"},
                provenance=Provenance(
                    source=self.provider_id,
                    provider_id=self.provider_id,
                    pulled_at=datetime.now(timezone.utc),
                ),
            )

    from app.market_data.registry import ProviderRegistry

    client = MarketDataClient.from_settings(get_settings())
    client.registry = ProviderRegistry()
    client.register_provider(FakeProvider("indianapi", 1245.40, priority=20))
    client.register_provider(FakeProvider("yahoo", 1245.50, priority=40))

    pack = await client.validated_package("INFY", persist=True)
    assert pack.get("enabled") is True
    assert pack["validated_fields"]["last"]["provider"] == "indianapi"
    assert pack["validated_fields"]["last"]["value"] == pytest.approx(1245.40)
