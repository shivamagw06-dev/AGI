"""Sprint 6.3 — Institutional Learning Engine success criteria."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.collectors.base import checksum_payload
from app.config.settings import Settings
from app.contracts.models import KnowledgeObjectType, RawEvent, Source
from app.ile.policy import MaterialityTier, score_numeric_change
from app.main import create_app
from app.pipeline.orchestrator import AcquisitionPipeline
from app.storage.db import KaipStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "kaip.db",
        scheduler_enabled=False,
        live_collectors_enabled=False,
        watchlist=("INFY", "TCS", "WIPRO"),
        pe_material_abs=1.0,
        revenue_growth_material_pp=5.0,
        duplicate_window_seconds=0,
    )


def _yahoo_fixture(
    *,
    pe: float,
    revenue_growth: float,
    pat_margin: float,
    debt: float,
    cash: float,
    price: float = 1600.0,
) -> dict:
    return {
        "yahoo_symbol": "INFY.NS",
        "as_of": "2026-07-28T10:00:00+00:00",
        "info": {
            "longName": "Infosys",
            "sector": "Technology",
            "industry": "IT Services",
            "currency": "INR",
            "marketCap": 8100000000000,
            "trailingPE": pe,
            "regularMarketPrice": price,
            "regularMarketVolume": 5000000,
            "revenueGrowth": revenue_growth,
            "earningsGrowth": 0.12,
            "totalRevenue": 150000000000,
            "ebitda": 40000000000,
            "netIncomeToCommon": 30000000000,
            "totalCash": cash,
            "totalDebt": debt,
            "pat_margin": pat_margin,
            "ebitda_margin": pat_margin + 0.02,
        },
    }


def test_materiality_policy_ignores_noise_and_scores_signal() -> None:
    pe = score_numeric_change("pe_ratio", previous=24.10, new=24.12)
    assert pe.learn is False
    assert pe.tier == MaterialityTier.IGNORE

    rev = score_numeric_change("revenue_growth", previous=18.0, new=26.0)
    assert rev.learn is True
    assert rev.tier == MaterialityTier.HIGH
    assert rev.score >= 80
    assert rev.importance == "High"


def test_infosys_earnings_triggers_full_learning_stack(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = KaipStore(settings.db_path)
    pipeline = AcquisitionPipeline(store, settings)

    day1 = _yahoo_fixture(pe=24.1, revenue_growth=0.18, pat_margin=0.20, debt=150000000000, cash=80000000000)
    day2 = _yahoo_fixture(pe=24.12, revenue_growth=0.26, pat_margin=0.22, debt=90000000000, cash=110000000000)

    from app.collectors.yahoo.collector import YahooCollector

    pipeline.run_collector(YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": day1}))
    result = pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": day2})
    )

    fields = {le.field_name for le in result.learning_events}
    observations = " ".join(le.observation for le in result.learning_events)

    # ✓ Revenue accelerated (material) — PE noise ignored
    assert "revenue_growth" in fields
    assert "pe" not in fields and "pe_ratio" not in fields
    assert "Revenue acceleration" in observations

    # ✓ Margins improved / cash strengthened / debt reduced when present on financial KO
    assert "pat_margin" in fields or "Operating margins improved" in observations or "cash" in fields or "debt" in fields

    # Learning event is institutional
    rev_events = [le for le in result.learning_events if le.field_name == "revenue_growth"]
    assert rev_events
    assert rev_events[0].importance.value == "High"
    assert rev_events[0].confidence.value == "High"
    assert rev_events[0].materiality_score >= 80
    assert rev_events[0].evidence in {"Quarterly Financials", "Company Profile Update"}
    assert set(rev_events[0].affected) >= {"Company", "Sector", "Valuation"}

    # ✓ Institutional memory updated (narrative, not raw metric)
    memory = store.list_memory("INFY")
    assert memory
    assert any("stronger growth phase" in m["narrative"].lower() for m in memory)
    assert all("0.26" not in m["narrative"] for m in memory)

    # ✓ Timeline updated
    timeline = store.list_timeline("INFY")
    assert timeline
    assert any("Revenue Acceleration" in t["label"] for t in timeline)

    # ✓ Publication envelope ready for Evidence Graph / IE
    assert result.published is not None
    assert result.published.envelope is not None
    assert result.published.envelope.evidence_graph_ready is True
    assert result.published.envelope.institutional_memory_ready is True
    assert result.published.envelope.learning_events
    assert result.published.envelope.institutional_memory
    assert result.published.envelope.learning_timeline

    # ✓ Relationship impact recorded
    # relationship_changes table should have rows
    rel = store._conn.execute("SELECT COUNT(*) AS c FROM relationship_changes").fetchone()["c"]
    assert rel >= 1

    store.close()


def test_sector_learning_from_multiple_companies(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pipeline = AcquisitionPipeline(KaipStore(settings.db_path), settings)

    # Seed same margin-compression signal across three IT names via ILE sector signals path
    from app.ile.sector_learning import SectorLearningEngine
    from app.ile.materiality import ScoredChange
    from app.ile.comparator import FieldChange
    from app.ile.policy import MaterialityScore, MaterialityTier

    engine = SectorLearningEngine(pipeline.store)
    scored = ScoredChange(
        change=FieldChange("pat_margin", 22.0, 19.0, "margins.pat_margin_pct"),
        materiality=MaterialityScore(
            field_name="pat_margin",
            category="Financial Performance",
            magnitude=3.0,
            score=90.0,
            tier=MaterialityTier.HIGH,
            importance="High",
            learn=True,
            reason="test",
        ),
    )
    engine.maybe_learn(sector="Technology", company_symbol="INFY", learnable=[scored])
    engine.maybe_learn(sector="Technology", company_symbol="TCS", learnable=[scored])
    out = engine.maybe_learn(sector="Technology", company_symbol="WIPRO", learnable=[scored])
    assert out
    assert "margin compression" in out[0].observation.lower()
    assert set(out[0].supporting_companies) >= {"INFY", "TCS", "WIPRO"}


def test_contradiction_when_margins_decline(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = KaipStore(settings.db_path)
    pipeline = AcquisitionPipeline(store, settings)
    from app.collectors.yahoo.collector import YahooCollector

    up = _yahoo_fixture(pe=25.0, revenue_growth=0.20, pat_margin=0.22, debt=100, cash=100)
    down = _yahoo_fixture(pe=25.0, revenue_growth=0.20, pat_margin=0.18, debt=100, cash=100)
    # Ensure financial statement carries explicit margin fields through normalizer:
    # compact path uses pat_margin on info — shape_financial may need margins from canonical.
    # Inject via direct financial KO ingest as RawEvent after first day.
    pipeline.run_collector(YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": up}))

    # Direct financial statement versions for clean margin contradiction
    from app.contracts.models import EntityRefs, KnowledgeMetadata, KnowledgeObject, utc_now

    def fin(margin: float, version: int, prev_id: str | None = None) -> KnowledgeObject:
        knowledge = {
            "company": "Infosys",
            "company_symbol": "INFY",
            "statement_type": "income",
            "period_end": "2026-06-30",
            "pat_margin": margin,
            "margins": {"pat_margin_pct": margin},
            "revenue_growth": 0.20,
            "revenue_growth_pct": 20.0,
        }
        return KnowledgeObject(
            object_type=KnowledgeObjectType.FINANCIAL_STATEMENT,
            company_symbol="INFY",
            subject_key="INFY",
            version=version,
            previous_object_id=prev_id,
            knowledge=knowledge,
            payload=knowledge,
            metadata=KnowledgeMetadata(source=Source.YAHOO, version=version),
            entity_refs=EntityRefs(
                company_id="co_infy",
                company_name="Infosys",
                company_symbol="INFY",
                sector="Technology",
                industry="IT Services",
                indexes=["NIFTY50"],
                peers=["TCS"],
                sector_key="technology",
            ),
            created_at=utc_now(),
            updated_at=utc_now(),
        )

    # Publish v1 then learn v2 decline via ILE directly
    v1 = fin(22.0, 1)
    pipeline.store.insert_knowledge_object(v1)
    v2 = fin(18.0, 2, v1.object_id)
    ile = pipeline.ile.learn(v2, v1)
    assert any(c.field_name == "pat_margin" for c in ile.conflicts)
    conflict = next(c for c in ile.conflicts if c.field_name == "pat_margin")
    assert conflict.status == "Needs Review"
    assert "Margins expanding" in conflict.previous_assumption
    assert "Margins declining" in conflict.new_observation


def test_learning_apis(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db_path = settings.db_path
    pipeline = AcquisitionPipeline(KaipStore(db_path), settings)
    from app.collectors.yahoo.collector import YahooCollector

    d1 = _yahoo_fixture(pe=24.1, revenue_growth=0.18, pat_margin=0.20, debt=150, cash=80)
    d2 = _yahoo_fixture(pe=24.12, revenue_growth=0.26, pat_margin=0.22, debt=90, cash=110)
    pipeline.run_collector(YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": d1}))
    pipeline.run_collector(YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": d2}))
    pipeline.store.close()

    app = create_app(Settings(db_path=db_path, scheduler_enabled=False, live_collectors_enabled=False))
    with TestClient(app) as client:
        learn = client.get("/v1/knowledge/learning/INFY")
        assert learn.status_code == 200
        assert any(i["field_name"] == "revenue_growth" for i in learn.json()["items"])

        memory = client.get("/v1/knowledge/memory/INFY")
        assert memory.status_code == 200
        assert memory.json()["items"]

        timeline = client.get("/v1/knowledge/timeline/INFY")
        assert timeline.status_code == 200
        assert timeline.json()["items"]
