"""FSE-ECD — Evidence Coverage Dashboard tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from financial_statements_engine.evidence_coverage.production import company, dashboard, health
from financial_statements_engine.evidence_coverage.schema import FUNNEL_STAGES, WORKSTREAM_ID
from financial_statements_engine.evidence_coverage.stages import assess_company
from financial_statements_engine.evidence_coverage.universe import resolve_universe
from financial_statements_engine.schema import GOLD_UNIVERSE
from financial_statements_engine.store import ensure_dirs, paths_for


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    # Point HD at a tiny synthetic root
    hd = tmp_path / "hd"
    for kind in ("financials_annual", "financials_quarterly"):
        (hd / kind).mkdir(parents=True)
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(hd))
    return tmp_path


def _write_hd(hd_root: Path, kind: str, ticker: str, period_end: str, source: str = "earnings_intelligence_p21"):
    path = hd_root / kind / f"{ticker}.json"
    payload = {
        "entity": ticker,
        "kind": kind,
        "n": 1,
        "records": [
            {
                "entity": ticker,
                "kind": kind,
                "period": "FY26" if "annual" in kind else "Q4FY26",
                "period_end": period_end,
                "source": source,
                "available_from": period_end,
                "payload": {},
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_ecd_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["question"] == "How many companies do we have?"
    assert set(h["funnel_stages"]) == set(FUNNEL_STAGES)
    assert all(v == 1.0 for v in h["stage_targets"].values())


def test_resolve_gold_universe():
    uni = resolve_universe("gold")
    assert uni["universe"] == "gold"
    assert uni["universe_size"] == len(GOLD_UNIVERSE)
    assert "TCS" in uni["tickers"]


def test_funnel_detects_stages(fse_tmp):
    hd = Path(fse_tmp / "hd")
    _write_hd(hd, "financials_annual", "TCS", "2026-03-31")
    _write_hd(hd, "financials_quarterly", "TCS", "2026-06-30")

    # parsed + validated + published + derived markers
    ensure_dirs()
    draft_dir = ensure_dirs() / "parsing" / "drafts" / "TCS"
    draft_dir.mkdir(parents=True)
    (draft_dir / "latest.json").write_text(json.dumps({"path": "x"}), encoding="utf-8")
    val_dir = ensure_dirs() / "validation" / "reports" / "TCS"
    val_dir.mkdir(parents=True)
    (val_dir / "r1.json").write_text(
        json.dumps({"approval": {"approval_status": "APPROVED"}, "publishable": True}),
        encoding="utf-8",
    )
    pub = paths_for("TCS")["published"]
    pub.mkdir(parents=True)
    (pub / "pack.json").write_text(json.dumps({"facts": [1]}), encoding="utf-8")
    der = paths_for("TCS")["derived"]
    der.mkdir(parents=True)
    (der / "latest.json").write_text(json.dumps({"metrics": {"roe": 0.1}}), encoding="utf-8")

    row = assess_company("TCS", in_universe=True)
    assert row["stages"]["discovered"] is True
    assert row["stages"]["latest_annual_filing"] is True
    assert row["stages"]["latest_quarterly_filing"] is True
    assert row["stages"]["parsed"] is True
    assert row["stages"]["validated"] is True
    assert row["stages"]["published"] is True
    assert row["stages"]["derived_metrics"] is True
    assert row["complete"] is True


def test_dashboard_gold_bottleneck(fse_tmp):
    # Only TCS has annual; gold still has 5 names → bottleneck after discovered
    hd = Path(fse_tmp / "hd")
    _write_hd(hd, "financials_annual", "TCS", "2026-03-31")
    dash = dashboard("gold", include_rows=True)
    assert dash["universe"] == "gold"
    assert dash["universe_size"] == 5
    by_stage = {f["stage"]: f for f in dash["funnel"]}
    assert by_stage["discovered"]["have"] == 5
    assert by_stage["discovered"]["target_pct"] == 100.0
    assert by_stage["latest_annual_filing"]["have"] == 1
    assert dash["bottleneck"]["stage"] in FUNNEL_STAGES
    assert dash["bottleneck"]["stage"] != "discovered" or by_stage["latest_annual_filing"]["pct"] < 100


def test_stale_annual_not_latest(fse_tmp):
    hd = Path(fse_tmp / "hd")
    _write_hd(hd, "financials_annual", "TCS", "2018-03-31", source="fixture")
    row = assess_company("TCS")
    assert row["stages"]["discovered"] is True
    assert row["stages"]["latest_annual_filing"] is False
    assert row["first_gap"] == "latest_annual_filing"


def test_company_endpoint(fse_tmp):
    out = company("TCS")
    assert out["ok"] is True
    assert out["company"]["ticker"] == "TCS"
