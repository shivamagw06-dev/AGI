"""Continuous Gather → Learn — activation + Ask-isolation tests."""

from __future__ import annotations

import os

from continuous_gather_learn import persist as cgl_persist
from continuous_gather_learn.flags import flags_dict, is_enabled
from continuous_gather_learn.knowledge_extract import extract_from_hd_pack
from continuous_gather_learn.orchestrator import learning_for_director, run_cycle, select_slot
from continuous_gather_learn.production import dashboard, health


def test_flags_and_health():
    assert is_enabled() is True  # default true
    flags = flags_dict()
    assert "CONTINUOUS_GATHER_LEARN" in flags
    body = health()
    assert body["ask_isolated"] is True
    assert body["ml_retrain"] is False
    assert "LIDI" in body["components"]


def test_knowledge_extract_is_structured_not_ml():
    out = extract_from_hd_pack(
        {
            "financials": {"revenue_cagr": 0.12, "roe": 0.18},
            "prices": {"volatility": 0.22, "beta": 1.1},
            "themes": ["digital payments"],
        },
        entity="TESTCO",
    )
    assert out["learning_mode"] == "structured_extraction_not_ml_training"
    assert out["metrics"]["revenue_cagr"] == 0.12
    saved = cgl_persist.get_knowledge_extract("TESTCO")
    assert saved.get("entity") == "TESTCO"


def test_run_cycle_never_raises_and_archives():
    # Force overnight slot path with learning; collectors soft-fail OK.
    os.environ.setdefault("CONTINUOUS_GATHER_LEARN", "true")
    os.environ.setdefault("CONTINUOUS_LIDI", "false")  # keep unit test light
    os.environ.setdefault("CONTINUOUS_KF_HD", "false")
    os.environ.setdefault("CONTINUOUS_MORNING_DAG", "false")
    os.environ.setdefault("CONTINUOUS_FAA_REFRESH", "false")
    os.environ.setdefault("CONTINUOUS_LEARNING_LOOP", "true")
    result = run_cycle(slot="overnight", force_morning_dag=False, include_faa=False)
    assert result["enabled"] is True
    assert result["ask_isolated"] is True
    assert result["ml_retrain"] is False
    assert "phases" in result
    assert result["phases"]["archive"]["status"] == "ok"
    dash = dashboard()
    assert dash["loop"][0] == "Collect"
    assert select_slot() in {"pre_market", "intraday", "post_market", "overnight"}


def test_director_learning_pack():
    cgl_persist.archive_learning(
        {
            "learning_id": "unit_learn_1",
            "source": "business",
            "outcome": "correct",
            "explanation": "Franchise durability held through cycle.",
        }
    )
    cgl_persist.put_checkpoint(
        "analyst_accuracy_memory",
        {
            "n_learnings": 1,
            "by_source": [{"source": "business", "n": 1, "correct": 1, "incorrect": 0, "accuracy": 1.0}],
        },
    )
    pack = learning_for_director(query="Should I buy TESTCO?", limit=5)
    assert pack["enabled"] is True
    assert pack["ml_retrain"] is False
    assert pack["opinion_weights"]
    assert "Weight analyst opinions" in pack["instruction"]
