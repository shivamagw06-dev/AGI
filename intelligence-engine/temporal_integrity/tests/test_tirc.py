"""AGI TIRC — Temporal Integrity & Replay Certification acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from temporal_integrity import TIRC_VERSION, guard, status
from temporal_integrity.replay_guard.guard import apply_replay_guard
from temporal_integrity.validator.contract import build_contract


ROOT = Path(__file__).resolve().parents[1]


def test_tirc_status_branded_agi() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["version"].startswith("temporal-integrity")
    assert TIRC_VERSION.startswith("temporal-integrity")


def test_reject_available_from_after_as_of() -> None:
    c = build_contract(
        {"memory_id": "M1", "available_from": "2021-01-01", "time_period": "2018-01 to 2020-12"},
        as_of="2020-03-31",
    )
    assert c["temporal_status"] == "rejected"
    assert "available_from" in (c["reason_if_rejected"] or "")


def test_reject_time_period_future_year_label() -> None:
    c = build_contract(
        {
            "memory_id": "MEM_BANK_PB_RI_ANALOG",
            "available_from": "2015-12-31",
            "time_period": "2009-01 to 2024-12",
            "title": "Bank P/B RI analog",
        },
        as_of="2022-06-30",
    )
    assert c["temporal_status"] == "rejected"
    assert "time_period" in (c["reason_if_rejected"] or "") or "year" in (c["reason_if_rejected"] or "")


def test_allow_historical_memory() -> None:
    c = build_contract(
        {
            "memory_id": "MEM_OK",
            "available_from": "2019-01-01",
            "time_period": "2010-01 to 2019-12",
            "title": "Pre-COVID",
        },
        as_of="2020-03-31",
    )
    assert c["temporal_status"] == "allowed"


def test_guard_strips_future_surface_bullets() -> None:
    im = {
        "top_memory_ids": ["M1"],
        "have_we_seen_this_before": True,
        "surface_bullets": [
            "MEM_OK: useful (2010-01 to 2019-12; similarity 0.8)",
            "MEM_BAD: span (2018-01 to 2024-12; similarity 0.7)",
        ],
        "scored": [
            {
                "memory": {
                    "memory_id": "M1",
                    "available_from": "2019-01-01",
                    "time_period": "2010-01 to 2019-12",
                }
            },
            {
                "memory": {
                    "memory_id": "M2",
                    "available_from": "2015-12-31",
                    "time_period": "2009-01 to 2024-12",
                }
            },
        ],
    }
    out = guard(as_of="2020-03-31", institutional_memory=im, stage="post_analog")
    kept = out["institutional_memory"]
    blob = " ".join(kept.get("surface_bullets") or [])
    assert "2024" not in blob
    assert "2025" not in blob
    ids = set(kept.get("top_memory_ids") or [])
    assert "M2" not in ids
    assert out["report"]["objects_rejected"] >= 1
    assert out["report"]["silent_substitution"] is False


def test_graph_filter_drops_future_nodes() -> None:
    eg = {
        "nodes": [
            {"node_id": "n1", "available_from": "2019-01-01", "label": "ok"},
            {"node_id": "n2", "available_from": "2024-04-01", "label": "future AI"},
        ],
        "edges": [{"source": "n1", "target": "n2", "available_from": "2024-04-01"}],
        "surface_bullets": ["ok event 2019", "future 2024 generative"],
        "n_nodes": 2,
        "n_edges": 1,
    }
    out = apply_replay_guard(as_of="2020-03-31", evidence_graph=eg, stage="pre_analog")
    g = out["evidence_graph"]
    assert g["n_nodes"] == 1
    assert all("2024" not in str(b) for b in (g.get("surface_bullets") or []))


def test_checksum_stable() -> None:
    im = {
        "surface_bullets": ["x 2018"],
        "scored": [{"memory": {"memory_id": "A", "available_from": "2018-01-01", "time_period": "2018"}}],
        "top_memory_ids": ["A"],
    }
    a = guard(as_of="2020-03-31", institutional_memory=im, stage="post_analog")
    b = guard(as_of="2020-03-31", institutional_memory=im, stage="post_analog")
    assert a["report"]["replay_checksum"] == b["report"]["replay_checksum"]


def test_no_reasoning_or_kf_imports_in_tirc() -> None:
    banned = ("govern_answer", "run_daily_pipeline", "package_for_governance", "select_frameworks", "resolve_intent")
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned


def test_gen_rep_soft_probe_no_future_leakage() -> None:
    from institutional_evaluation_lab.datasets.catalog import get_question
    from institutional_evaluation_lab.benchmarks.probe import probe_question
    from institutional_evaluation_lab.judges.structural import judge_replay

    for qid in ("GEN-REP-01-01", "GEN-REP-04-01", "GEN-REP-05-01"):
        q = get_question(qid)
        assert q is not None
        probe = probe_question(q, mode="soft")
        j = judge_replay(q, probe)
        assert j["passed"] is True, f"{qid} leaks={j.get('leaks')} root={j.get('root_cause')}"
        blob = " ".join(str(x) for x in ((probe.get("institutional_memory") or {}).get("surface_bullets") or []))
        assert "2024" not in blob
        assert "2025" not in blob
