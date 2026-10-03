"""Phase-1 historical coverage collector tests (offline / injected)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from live_data import store
from live_data.collectors.bse_corporate_actions import (
    _parse_actions_any,
    collect_bse_corporate_actions,
)
from live_data.collectors.company_ir import _classify_doc, _discover_documents, collect_company_ir
from live_data.collectors.rbi_dbie import _extract_series_from_html, collect_rbi_dbie
from live_data.qa import qa_corporate_actions, qa_documents, qa_macro_series

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    store.reset_runtime()
    yield
    store.reset_runtime()


def test_bse_csv_injected_and_history_merge() -> None:
    csv_text = (SAMPLES / "bse_corporate_actions.csv").read_text(encoding="utf-8")
    env = collect_bse_corporate_actions(injected_csv=csv_text)
    assert env["ok"] is True
    actions = env["payload"]["actions"]
    assert len(actions) >= 3
    types = {a["action_type"] for a in actions}
    assert "dividend" in types
    assert "bonus" in types
    assert "split" in types
    qa = qa_corporate_actions(actions)
    assert qa["ok"] is True


def test_bse_html_table_parser() -> None:
    html = """
    <html><body><table>
      <tr><th>Security Code</th><th>Security Name</th><th>Ex Date</th><th>Purpose</th></tr>
      <tr><td>500209</td><td>INFOSYS LTD</td><td>25-Jul-2024</td><td>Dividend - Rs.20</td></tr>
      <tr><td>532540</td><td>TCS LTD</td><td>18-Jul-2024</td><td>Bonus 1:1</td></tr>
    </table></body></html>
    """
    actions, effective, path = _parse_actions_any(html)
    assert path == "html_table"
    assert effective == "2024-07-25"
    assert len(actions) == 2
    assert actions[0]["symbol"] == "INFY"


def test_bse_json_api_shape() -> None:
    payload = {
        "Table": [
            {
                "SecurityCode": "500209",
                "SecurityName": "INFOSYS LTD",
                "ExDate": "25-Jul-2024",
                "Purpose": "Dividend - Rs.10",
                "RecordDate": "26-Jul-2024",
            }
        ]
    }
    actions, effective, path = _parse_actions_any(json.dumps(payload))
    assert path == "json"
    assert len(actions) == 1
    assert actions[0]["action_type"] == "dividend"
    assert effective == "2024-07-25"


def test_rbi_html_extract_and_inject() -> None:
    html = """
    <html><body>
      <p>Repo Rate: 6.50%</p>
      <p>Reverse Repo Rate: 3.35%</p>
      <p>CRR: 4.5%</p>
      <p>SLR 18.0%</p>
      <p>CPI inflation 5.1%</p>
      <p>WPI 2.3%</p>
      <p>as on 26 July 2024</p>
    </body></html>
    """
    series = _extract_series_from_html(html)
    metrics = {s["metric"] for s in series}
    assert "repo_rate" in metrics
    assert "crr" in metrics
    assert "slr" in metrics
    sample = json.loads((SAMPLES / "rbi_dbie_key_rates.json").read_text(encoding="utf-8"))
    env = collect_rbi_dbie(injected_json=sample)
    assert env["ok"] is True
    assert env["payload"]["history_points"] >= len(sample["series"]) - 1
    assert qa_macro_series(env["payload"]["series"])["ok"]


def test_company_ir_discovers_pdf_links() -> None:
    hub = b"""
    <html><body>
      <a href="/investors/reports-filings/annual-report/ar-2024.pdf">Annual Report 2024</a>
      <a href="https://cdn.example.com/q1-investor-presentation.pdf">Q1 Presentation</a>
      <a href="/press/release-note.pdf">Press Release</a>
      <a href="/about">About</a>
    </body></html>
    """
    docs = _discover_documents([("https://www.infosys.com/investors.html", hub)], ticker="INFY")
    assert len(docs) >= 3
    types = {d["doc_type"] for d in docs}
    assert "annual_report" in types
    assert "investor_presentation" in types
    assert _classify_doc("x/transcript-q1.pdf", "Earnings Call Transcript") == "earnings_transcript"

    injected = json.loads((SAMPLES / "company_ir_infosys.json").read_text(encoding="utf-8"))
    env = collect_company_ir(ticker="INFY", injected_json=injected, download_files=False)
    assert env["ok"] is True
    assert env["payload"]["document_count"] >= 2
    assert qa_documents(env["payload"]["documents"])["n"] >= 2


def test_hd_backfill_checkpoint_resume(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    monkeypatch.setenv("KF_HD_TARGET_YEARS", "10")
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    from knowledge_factory.historical_depth.backfill import (
        is_complete,
        pending_entities,
        run_backfill_batch,
    )
    from knowledge_factory.historical_depth import store as hd_store
    from knowledge_factory.historical_depth import queue as bf_queue

    hd_store.reset_store()
    monkeypatch.setattr(bf_queue, "supported_universe", lambda: ["INFY", "TCS"])
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY", "TCS"],
    )
    bf_queue.ensure_queue(force_refresh=True)
    report = run_backfill_batch(entities=["INFY", "TCS"], batch_size=2, target_years=10, derive=True)
    assert report["ok"] is True
    assert report["processed"] == 2
    assert is_complete("INFY", target_years=10)
    # Second run should skip completed
    pending = pending_entities(["INFY", "TCS"], target_years=10)
    assert "INFY" not in pending
    assert "TCS" not in pending


def test_knowledge_extract_from_series(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    from knowledge_factory.historical_depth.collectors import collect_entity_history
    from continuous_gather_learn.knowledge_extract import extract_from_hd_series
    from knowledge_factory.historical_depth import store as hd_store

    hd_store.reset_store()
    collect_entity_history("INFY", prefer_live=False)
    out = extract_from_hd_series("INFY")
    assert out["entity"] == "INFY"
    assert out["metrics"].get("annual_periods", 0) >= 10 or out["metrics"].get("price_points", 0) > 0
