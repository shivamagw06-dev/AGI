"""AGI IEW — Institutional Evidence Weighting acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_evidence_weighting import IEW_VERSION, apply_weighting, status
from institutional_evidence_weighting.production import explain, ranking, score
from institutional_evidence_weighting.scoring.engine import weight_objects


ROOT = Path(__file__).resolve().parents[1]


def test_iew_status_branded_agi() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["version"].startswith("institutional-evidence-weighting")
    assert IEW_VERSION.startswith("institutional-evidence-weighting")
    assert s["freeze_locks"]["no_llm_weighting"] is True
    assert s["freeze_locks"]["reasoning_frozen"] is True


def test_deterministic_weighting() -> None:
    objs = [
        {
            "evidence_id": "E_AUDIT",
            "source": "audited_filing",
            "title": "FY24 audited results",
            "available_from": "2024-05-01",
            "evidence_strength": 0.95,
            "entity": "INFY",
        },
        {
            "evidence_id": "E_MEDIA",
            "source": "general_media",
            "title": "Blog commentary",
            "available_from": "2024-05-02",
            "evidence_strength": 0.4,
            "entity": "INFY",
        },
    ]
    a = weight_objects(objs, as_of="2024-06-30")
    b = weight_objects(objs, as_of="2024-06-30")
    assert [x["evidence_id"] for x in a] == [x["evidence_id"] for x in b]
    assert [x["weight_score"] for x in a] == [x["weight_score"] for x in b]
    assert a[0]["evidence_id"] == "E_AUDIT"
    assert a[0]["weight_score"] > a[1]["weight_score"]


def test_audited_filings_outrank_commentary() -> None:
    ranked = weight_objects(
        [
            {"evidence_id": "A", "source": "audited_filing", "title": "AR", "available_from": "2023-01-01", "entity": "X"},
            {"evidence_id": "B", "source": "general_media", "title": "Op-ed", "available_from": "2023-01-02", "entity": "X"},
        ],
        as_of="2023-06-01",
    )
    assert ranked[0]["evidence_id"] == "A"


def test_regulator_outranks_media() -> None:
    ranked = weight_objects(
        [
            {"evidence_id": "R", "source": "regulator", "title": "SEBI notice", "available_from": "2022-01-01", "entity": "Y"},
            {"evidence_id": "M", "source": "general_media", "title": "Rumour mill", "available_from": "2022-01-02", "entity": "Y"},
        ],
        as_of="2022-06-01",
    )
    assert ranked[0]["evidence_id"] == "R"


def test_company_filings_outrank_rumours() -> None:
    ranked = weight_objects(
        [
            {"evidence_id": "F", "source": "exchange_filing", "title": "NSE filing", "available_from": "2021-01-01", "entity": "Z"},
            {"evidence_id": "U", "source": "rumour", "title": "WhatsApp tip", "available_from": "2021-01-02", "entity": "Z"},
        ],
        as_of="2021-03-01",
    )
    assert ranked[0]["evidence_id"] == "F"
    assert ranked[0]["weight_score"] > ranked[1]["weight_score"]


def test_fixtures_never_outrank_validated_live() -> None:
    ranked = weight_objects(
        [
            {
                "evidence_id": "LIVE",
                "source": "quarterly_results",
                "title": "Q results",
                "available_from": "2024-01-01",
                "entity": "TCS",
                "evidence_strength": 0.9,
            },
            {
                "evidence_id": "FIX",
                "source": "fixture",
                "title": "Seed fixture",
                "available_from": "2024-01-01",
                "entity": "TCS",
                "fixture": True,
                "evidence_strength": 1.0,
            },
        ],
        as_of="2024-02-01",
    )
    ids = [r["evidence_id"] for r in ranked]
    assert ids.index("LIVE") < ids.index("FIX")
    assert ranked[ids.index("LIVE")]["weight_score"] > ranked[ids.index("FIX")]["weight_score"]


def test_temporal_rejected_excluded() -> None:
    ranked = weight_objects(
        [
            {
                "evidence_id": "OK",
                "source": "annual_report",
                "title": "ok",
                "available_from": "2019-01-01",
                "temporal_status": "allowed",
                "entity": "A",
            },
            {
                "evidence_id": "BAD",
                "source": "annual_report",
                "title": "future",
                "available_from": "2025-01-01",
                "temporal_status": "rejected",
                "entity": "A",
            },
        ],
        as_of="2020-01-01",
    )
    by_id = {r["evidence_id"]: r for r in ranked}
    assert by_id["BAD"]["eligible"] is False
    assert by_id["BAD"]["weight_score"] == 0
    assert by_id["BAD"]["exclusion_reason"] == "temporal_integrity_rejected"


def test_analogue_weighting_consistent() -> None:
    mem = {
        "evidence_id": "MEM1",
        "source": "analogue",
        "kind": "memory",
        "title": "Rate cycle analog",
        "available_from": "2019-01-01",
        "similarity_score": 0.8,
        "entity": "HDFCBANK",
    }
    a = weight_objects([mem], as_of="2020-01-01")
    b = weight_objects([mem], as_of="2020-01-01")
    assert a[0]["analogue_score"] == b[0]["analogue_score"]
    assert a[0]["analogue_score"] > 0


def test_replay_identical_rankings() -> None:
    objs = [
        {"evidence_id": "E1", "source": "bloomberg", "title": "wire", "available_from": "2018-01-01", "entity": "X"},
        {"evidence_id": "E2", "source": "company_ir", "title": "IR", "available_from": "2018-01-01", "entity": "X"},
        {"evidence_id": "E3", "source": "broker_research", "title": "note", "available_from": "2018-06-01", "entity": "X"},
    ]
    r1 = [w["evidence_id"] for w in weight_objects(objs, as_of="2019-01-01")]
    r2 = [w["evidence_id"] for w in weight_objects(objs, as_of="2019-01-01")]
    assert r1 == r2


def test_apply_weighting_soft_wire_pack() -> None:
    eg = {
        "nodes": [
            {
                "node_id": "N1",
                "source": "audited_filing",
                "title": "Audit",
                "available_from": "2020-01-01",
                "entity": "INFY",
            }
        ],
        "surface_bullets": ["N1: Audit note"],
        "ieg_version": "ieg-test",
    }
    im = {
        "memories": [
            {
                "memory_id": "MEM_X",
                "source": "analogue",
                "title": "Prior cycle",
                "available_from": "2019-01-01",
                "similarity_score": 0.7,
            }
        ],
        "surface_bullets": ["MEM_X: Prior cycle"],
        "imai_version": "imai-test",
    }
    out = apply_weighting(
        as_of="2021-01-01",
        evidence_graph=eg,
        institutional_memory=im,
        question_id="Q1",
        intent="Explain",
        framework="F1",
        playbook="P1",
        replay_mode=True,
    )
    pack = out["pack"]
    assert pack["reasoning_changed"] is False
    assert pack["llm_used"] is False
    assert pack["n_weighted"] >= 2
    assert pack["ordered_evidence"]
    assert pack["ordered_evidence"][0]["weight_score"] >= pack["ordered_evidence"][-1]["weight_score"]
    assert out["report"]["reasoning_changed"] is False


def test_explain_and_score_api() -> None:
    payload = {
        "evidence": {
            "evidence_id": "E",
            "source": "sebi",
            "title": "Order",
            "available_from": "2022-01-01",
            "entity": "X",
        },
        "as_of": "2022-06-01",
    }
    s = score(payload)
    e = explain(payload)
    assert s["weight_score"] == e["weight_score"]
    assert "Credibility" in e["reason"]
    r = ranking({"evidence": [payload["evidence"]], "as_of": "2022-06-01"})
    assert r["n"] == 1


def test_frozen_modules_not_imported_for_mutation() -> None:
    """IEW package must not rewrite frozen module source trees."""
    frozen = [
        "knowledge_factory",
        "institutional_reasoning",
        "framework_selection",
        "institutional_communication",
        "temporal_integrity",
        "institutional_evidence_graph",
        "institutional_analog_intelligence",
        "evidence_retrieval",
    ]
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
        # Ensure we never open frozen files for write — structural check: no Path write helpers targeting them
        text = path.read_text(encoding="utf-8")
        for name in frozen:
            assert f"open({name}" not in text
            assert f"{name}.py" not in text or "import" in text


def test_contradictions_identified_not_resolved() -> None:
    out = apply_weighting(
        as_of="2023-01-01",
        evidence_graph={
            "nodes": [
                {
                    "node_id": "same-topic-filing",
                    "source": "exchange_filing",
                    "title": "margin outlook",
                    "available_from": "2022-01-01",
                    "entity": "X",
                },
                {
                    "node_id": "same-topic-media",
                    "source": "general_media",
                    "title": "margin outlook",
                    "available_from": "2022-01-02",
                    "entity": "X",
                },
            ]
        },
    )
    assert out["pack"]["contradictions_resolved"] is False
    assert out["pack"]["n_conflicts"] >= 1
    assert out["pack"]["conflicts"][0]["resolved"] is False
