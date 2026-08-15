from __future__ import annotations

import json
from types import SimpleNamespace

from financials_valuation.bank_kpi_backfill import (
    extract_document,
    persist_observations,
    validate_observation,
)


DOCUMENT = {
    "document_id": "doc-axis-q1fy26",
    "title": "Axis Bank Q1 FY26 results",
    "url": "https://www.axisbank.com/quarterly-results/q1fy26",
    "published_at": "2025-07-17T00:00:00+00:00",
    "retrieved_at": "2025-07-18T00:00:00+00:00",
    "text": ("For Q1 FY26, Net Interest Margin (NIM) was 3.80%. GNPA was 1.57%. "
             "The quarterly results discuss deposits, advances, capital adequacy, liquidity, "
             "asset quality, provisions and operating performance. " * 3),
}


def test_valid_observation_remains_proposed_and_preserves_printed_percent():
    row = validate_observation({
        "metric_key": "nim", "value": 3.8, "unit": "percent", "period": "Q1FY26",
        "period_end": "2025-06-30", "frequency": "QUARTERLY", "basis": "REPORTED",
        "consolidation_scope": "STANDALONE", "annualized": False,
        "source_excerpt": "Net Interest Margin (NIM) was 3.80%", "confidence": .94,
    }, symbol="AXISBANK", document=DOCUMENT)
    assert row["validation_status"] == "PROPOSED"
    assert row["value"] == 3.8
    assert row["confidence"] == .85
    assert row["available_at"] == DOCUMENT["retrieved_at"]


def test_non_verbatim_or_out_of_range_observation_is_quarantined():
    row = validate_observation({
        "metric_key": "gnpa", "value": 400, "unit": "percent", "period": "Q1FY26",
        "period_end": "2025-06-30", "frequency": "QUARTERLY",
        "source_excerpt": "GNPA was very low", "confidence": .9,
    }, symbol="AXISBANK", document=DOCUMENT)
    assert row["validation_status"] == "QUARANTINED"
    assert "EXCERPT_NOT_VERBATIM" in row["validation_notes"]
    assert "RATIO_OUT_OF_RANGE" in row["validation_notes"]


def test_openai_extraction_is_schema_bounded_and_not_self_trusted():
    class Provider:
        def available(self):
            return True

        def structured_generate(self, **_kwargs):
            return SimpleNamespace(text=json.dumps({"observations": [{
                "metric_key": "nim", "value": 3.8, "unit": "percent", "period": "Q1FY26",
                "period_end": "2025-06-30", "frequency": "QUARTERLY", "basis": "REPORTED",
                "consolidation_scope": "STANDALONE", "annualized": False,
                "source_excerpt": "Net Interest Margin (NIM) was 3.80%", "confidence": .99,
            }]}))

    rows = extract_document("AXISBANK", DOCUMENT, provider=Provider())
    assert len(rows) == 1
    assert rows[0]["validation_status"] == "PROPOSED"
    assert rows[0]["extraction_method"] == "OPENAI_STRUCTURED_EXTRACTION"


def test_persistence_is_append_only_upsert(monkeypatch):
    calls = []
    monkeypatch.setattr("financials_valuation.bank_kpi_backfill._rest",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    result = persist_observations([{"validation_status": "PROPOSED"}])
    assert result == {"ok": True, "written": 1, "proposed": 1, "quarantined": 0}
    assert calls[0][0][1] == "bank_kpi_observations"
    assert "resolution=ignore-duplicates" in calls[0][1]["prefer"]
