from __future__ import annotations

import json
from types import SimpleNamespace

from financials_valuation.bank_kpi_backfill import (
    classify_document,
    deterministic_extract,
    extract_document,
    reprocess_indexed_bank_documents,
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


def test_document_classification_and_deterministic_atomic_extraction():
    document = {**DOCUMENT, "text": "Q1 FY26\nNet Interest Margin (NIM) was 3.80%.\nGNPA was 1.57%."}
    assert classify_document(document) == "QUARTERLY_RESULTS"
    rows = deterministic_extract("AXISBANK", document)
    assert {(row["metric_key"], row["value"]) for row in rows} == {("nim", 3.8), ("gnpa", 1.57)}
    assert all(row["period_end"] == "2025-06-30" for row in rows)
    assert all(row["extraction_method"] == "DETERMINISTIC_TEXT" for row in rows)


def test_reprocess_uses_existing_fre_documents_without_acquisition(monkeypatch):
    class Doc:
        retrieved_at = SimpleNamespace()
        symbol = "AXISBANK"
        company = "Axis Bank"
        title = "Axis Bank Q1 FY26 results"
        url = DOCUMENT["url"]
        raw_text = "Q1 FY26\nNet Interest Margin (NIM) was 3.80%."

        def to_dict(self):
            return {**DOCUMENT, "text": self.raw_text, "raw_text": self.raw_text}

    Doc.retrieved_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    faa = SimpleNamespace(fre=SimpleNamespace(store=SimpleNamespace(documents={"x": Doc()})))
    monkeypatch.setattr("financials_valuation.bank_kpi_backfill.extract_document", lambda *_a, **_k: [])
    monkeypatch.setattr("financials_valuation.bank_kpi_backfill.persist_observations",
                        lambda rows: {"ok": True, "written": len(rows), "proposed": len(rows), "quarantined": 0})
    result = reprocess_indexed_bank_documents(faa, symbols=["AXISBANK"])
    assert result["mode"] == "REPROCESS_INDEXED_ONLY"
    assert result["documents"] == 1
    assert result["observations"] == 1
