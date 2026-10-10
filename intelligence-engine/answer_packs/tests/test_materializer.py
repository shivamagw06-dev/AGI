from answer_packs.materializer import covered_universe, load_materialized_pack, materialize_batch


def test_materializer_rotates_and_deduplicates(monkeypatch, tmp_path):
    monkeypatch.setenv("ANSWER_PACK_STORE_ROOT", str(tmp_path))

    def analyse(_query, *, ticker, record):
        assert record is False
        return {
            "executive_summary": f"Current analysis for {ticker}",
            "identity": {"company_name": ticker, "sector": "Test"},
            "business_overview": f"Database overview for {ticker}",
            "financial_intelligence": {"coverage_pct": 80, "narrative": "Financial evidence"},
            "valuation_intelligence": {"coverage_pct": 60, "narrative": "Valuation evidence"},
            "recommendation_readiness": {"overall": 50, "gate": "Withheld"},
        }

    first = materialize_batch(batch_size=2, analyser=analyse)
    assert first["written"] == 2
    assert load_materialized_pack(first["tickers"][0])["materialization"]["llm_used"] is False
    second = materialize_batch(batch_size=2, analyser=analyse)
    assert second["unchanged"] == 2


def test_covered_universe_is_core_first_and_includes_database_tickers():
    universe = covered_universe()

    assert universe[0] == "AXISBANK"
    assert "INFY" in universe
    assert len(universe) == len(set(universe))
    # Local acceptance fixtures can be a strict subset of production, but the
    # core set must remain intact and database entries must merge without dupes.
    assert len(universe) >= 30


def test_materializer_preserves_scalar_cases_and_nested_evidence(monkeypatch, tmp_path):
    monkeypatch.setenv("ANSWER_PACK_STORE_ROOT", str(tmp_path))

    def analyse(_query, *, ticker, record):
        return {
            "executive_summary": "Infosys is an export-led IT services franchise.",
            "investment_thesis": "Durable client relationships support recurring demand.",
            "bull_case": "Large-deal conversion accelerates.",
            "bear_case": "Discretionary spending remains weak.",
            "risks": ["Demand slowdown"],
            "catalysts": ["Deal wins"],
            "evidence": {
                "items": [
                    {"title": "INFY company record", "source": "institutional_warehouse"}
                ]
            },
        }

    result = materialize_batch(batch_size=1, analyser=analyse)
    pack = load_materialized_pack(result["tickers"][0])

    assert pack["investment_case"]["bull_case"] == ["Large-deal conversion accelerates."]
    assert pack["investment_case"]["bear_case"] == ["Discretionary spending remains weak."]
    assert pack["evidence"][0]["source"] == "institutional_warehouse"
