"""ICF-01 — Institutional Coverage Factory tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from institutional_coverage_factory.schema import (
    DEFAULT_CONFIG,
    EVIDENCE_CLASSES,
    ICF_VERSION,
    ICF_WORKSTREAM_ID,
    ICC_EXIT_CRITERIA,
    PIPELINE,
    PRIORITY_TIERS,
    PriorityTier,
)
from institutional_coverage_factory.config import as_yaml_dict, load_config
from institutional_coverage_factory.universe import ordered_universe, tier_for_ticker, top20_tickers
from institutional_coverage_factory.scorer.score import score_evidence_classes
from institutional_coverage_factory.validator.icc import evaluate_icc
from institutional_coverage_factory.collectors.dispatch import collectors_for_missing
from institutional_coverage_factory.planner.plan import plan_coverage
from institutional_coverage_factory.scheduler.loop import run_coverage_tick, scheduler_status
from institutional_coverage_factory.production import (
    get_icf_status,
    health,
    soft_slice_mission_control,
)
from institutional_evidence.schema import PHASE1_TOP20


def test_icf_identity():
    st = get_icf_status()
    assert st["workstream_id"] == "ICF-01"
    assert ICF_VERSION.startswith("icf-01")
    assert health()["ok"] is True
    assert PIPELINE[-1] == "Institutional Coverage Complete"
    assert PRIORITY_TIERS[0] == "TOP20"


def test_evidence_class_weights_sum_100():
    total = sum(int(v["weight"]) for v in EVIDENCE_CLASSES.values())
    assert total == 100
    assert all(v["required"] for v in EVIDENCE_CLASSES.values())


def test_config_is_icc_throughput_not_crawl():
    cfg = load_config()
    assert "max_companies_per_day" in cfg
    assert cfg["institutional_coverage_threshold"] == 100.0
    yml = as_yaml_dict()["coverage_factory"]
    assert yml["max_companies_per_day"] == cfg["max_companies_per_day"]
    assert yml["priority"][0] == PriorityTier.TOP20.value
    # North-star language in defaults
    assert DEFAULT_CONFIG["max_companies_per_day"] == 100


def test_top20_priority_uses_iep_phase1():
    t20 = top20_tickers()
    assert len(t20) == 20
    assert t20 == [r["ticker"] for r in PHASE1_TOP20]
    assert tier_for_ticker("RELIANCE") == "TOP20"
    ordered = ordered_universe()
    assert ordered[0]["priority_tier"] == "TOP20"


def test_score_and_icc_for_demo_company():
    score = score_evidence_classes("RELIANCE")
    assert score["ok"] is True
    assert "coverage_pct" in score
    assert "classes" in score
    assert set(score["classes"]) == set(EVIDENCE_CLASSES)
    icc = evaluate_icc("RELIANCE", score=score)
    assert icc["ok"] is True
    assert set(icc["checks"]) >= set(ICC_EXIT_CRITERIA)
    assert "institutional_coverage_complete" in icc
    # Incomplete companies expose missing collectors
    missing = score.get("missing_classes") or []
    collectors = collectors_for_missing(missing)
    assert all(c for c in collectors)


def test_planner_ranks_non_icc_first():
    plan = plan_coverage(limit=5, scope="TOP20", skip_icc=True)
    assert plan["ok"] is True
    assert plan["metric"] == "companies_entering_icc_per_day"
    assert "queue" in plan
    # Queue items carry priority + missing classes
    for item in plan["queue"]:
        assert item["priority_tier"] == "TOP20"
        assert "coverage_pct" in item
        assert "collectors" in item


def test_scheduler_tick_without_dispatch():
    before = scheduler_status()
    tick = run_coverage_tick(scope="TOP20", limit=2, dispatch=False)
    assert tick["ok"] is True
    assert tick["workstream_id"] == ICF_WORKSTREAM_ID
    assert "icc_entered_today" in tick
    assert tick["max_companies_per_day"] == load_config()["max_companies_per_day"]
    after = scheduler_status()
    assert after["ticks"] >= before.get("ticks", 0)


def test_mission_control_soft_slice():
    slice_ = soft_slice_mission_control()
    assert slice_.get("status") == "ok"
    assert slice_["board"] == "Institutional Coverage"
    assert slice_["workstream_id"] == "ICF-01"
    assert "daily_icc_target" in slice_
    assert slice_["north_star"].startswith("Companies entering ICC")
