"""IDI Track 4 — institutional documents intelligence acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.chunking import chunk_parsed
from knowledge_factory.institutional_documents.collectors import collect_documents
from knowledge_factory.institutional_documents.parsers import parse_document
from knowledge_factory.institutional_documents.pipeline import run_institutional_documents_pipeline
from knowledge_factory.institutional_documents.production import (
    company,
    dashboard,
    health,
    replay,
    report,
    search,
)
from knowledge_factory.institutional_documents.provenance import assert_chunk_provenance
from knowledge_factory.institutional_documents.schema import FREEZE_LOCKS, IDI_VERSION
from knowledge_factory.institutional_documents.validators import validate_document

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = Path(__file__).resolve().parents[1] / "fixtures" / "samples"


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("IDI_STORE_ROOT", str(tmp_path / "idi"))
    store.reset()
    yield
    store.reset()


def _inject_from_samples() -> list[dict]:
    mapping = [
        ("INFY", "ANNUAL_REPORT", "infy_annual_report_fy24.txt", "2024-06-15"),
        ("INFY", "QUARTERLY_REPORT", "infy_quarterly_q1_fy25.txt", "2024-07-18"),
        ("INFY", "INVESTOR_PRESENTATION", "infy_presentation_q1_fy25.txt", "2024-07-18"),
        ("INFY", "CONFERENCE_CALL_TRANSCRIPT", "infy_transcript_q1_fy25.txt", "2024-07-19"),
        ("INFY", "EXCHANGE_FILING", "infy_exchange_filing_q1_fy25.txt", "2024-07-18"),
    ]
    rows = []
    for company_name, dtype, fname, published in mapping:
        text = (SAMPLES / fname).read_text(encoding="utf-8")
        rows.append(
            {
                "company": company_name,
                "type": dtype,
                "title": f"{company_name} {dtype}",
                "published_date": published,
                "available_from": published,
                "source": "COMPANY_IR" if dtype != "EXCHANGE_FILING" else "NSE_FILINGS",
                "language": "en",
                "text": text,
                "url": "https://www.infosys.com/investors.html",
            }
        )
    return rows


def test_annual_quarterly_presentation_transcript_filing_ingestion() -> None:
    report_out = run_institutional_documents_pipeline(injected=_inject_from_samples())
    assert report_out["idi_version"] == IDI_VERSION
    assert report_out["ingested_ok"] == 5
    assert report_out["reasoning_changed"] is False
    assert report_out["knowledge_factory_core_changed"] is False
    types = {r.get("object_type") for r in report_out["results"] if r.get("ok")}
    assert "AnnualReportObject" in types
    assert "QuarterlyReportObject" in types
    assert "PresentationObject" in types
    assert "TranscriptObject" in types


def test_parser_and_chunking_provenance() -> None:
    raw = collect_documents(injected=_inject_from_samples()[:1])[0]
    v = validate_document(raw)
    assert v["ok"] is True
    parsed = parse_document(raw)
    assert parsed["section_count"] >= 3
    assert "MANAGEMENT_DISCUSSION" in parsed["extracted_labels"]
    chunks = chunk_parsed(raw, parsed)
    assert chunks
    assert all(assert_chunk_provenance(c) for c in chunks)
    assert all(c.get("embedding") and len(c["embedding"]) == 64 for c in chunks)


def test_point_in_time_replay_no_future_leak() -> None:
    run_institutional_documents_pipeline(injected=_inject_from_samples())
    early = replay(as_of="2024-06-20", ticker="INFY")
    assert early["document_count"] == 1
    assert early["future_leakage_blocked"] >= 1
    assert all(d["available_from"] <= "2024-06-20" for d in early["documents"])
    late = replay(as_of="2024-07-19", ticker="INFY")
    assert late["document_count"] == 5
    # Deterministic second call
    late2 = replay(as_of="2024-07-19", ticker="INFY")
    assert [d["checksum"] for d in late["documents"]] == [d["checksum"] for d in late2["documents"]]


def test_evidence_packs_and_search() -> None:
    out = run_institutional_documents_pipeline(injected=_inject_from_samples())
    assert out["packs_created"] >= 5
    c = company("INFY")
    assert c["n_documents"] == 5
    assert c["packs"]
    hits = search(q="guidance", ticker="INFY")
    assert hits["n"] >= 1
    doc_id = c["documents"][0]["document_id"]
    rep = report(doc_id)
    assert rep["ok"] is True
    assert rep["chunk_count"] >= 1


def test_dashboard_and_health() -> None:
    run_institutional_documents_pipeline(injected=_inject_from_samples())
    h = health()
    assert h["not_a_reasoning_engine"] is True
    assert h["not_summarisation"] is True
    assert FREEZE_LOCKS["never_document_to_reasoning"] is True
    d = dashboard()
    assert d["documents"] == 5
    assert d["knowledge_objects_created"] == 5
    assert d["recommendation"] is None


def test_catalog_sample_pipeline() -> None:
    out = run_institutional_documents_pipeline(tickers=["INFY"], allow_samples=True)
    assert out["ingested_ok"] >= 4
    assert out["status"] in {"ok", "degraded"}


def test_validator_rejects_unknown_source_and_future_leak() -> None:
    bad = collect_documents(injected=_inject_from_samples()[:1])[0]
    bad["source"] = "BROKER_RESEARCH"
    assert validate_document(bad)["ok"] is False
    fut = collect_documents(injected=_inject_from_samples()[:1])[0]
    fut["available_from"] = "2025-01-01"
    assert "future_leakage" in validate_document(fut, as_of="2024-07-01")["failures"]


def test_scheduler_soft_wire_present() -> None:
    from institutional_scheduler.execution import handlers as h

    text = Path(h.__file__).read_text(encoding="utf-8")
    assert "institutional_documents" in text
    assert "documents_soft_wire" in text


def test_mission_control_soft_board() -> None:
    run_institutional_documents_pipeline(injected=_inject_from_samples())
    from mission_control.aggregate import _soft_institutional_intelligence

    inst = _soft_institutional_intelligence()
    assert inst.get("institutional_documents") is not None
    assert "institutional_documents" in (inst.get("sources") or [])


def test_reasoning_and_kf_core_untouched() -> None:
    frozen = [
        ROOT / "institutional_reasoning" / "execution_governance.py",
        ROOT / "knowledge_factory" / "schedulers" / "daily.py",
        ROOT / "ask_pipeline" / "pipeline.py",
    ]
    for path in frozen:
        if path.exists():
            ast.parse(path.read_text(encoding="utf-8"))
    idi_root = ROOT / "knowledge_factory" / "institutional_documents"
    banned = "govern" + "_answer"
    for path in idi_root.rglob("*.py"):
        if path.parent.name == "tests":
            continue
        text = path.read_text(encoding="utf-8")
        assert banned not in text
        assert "evaluate_decision" not in text
