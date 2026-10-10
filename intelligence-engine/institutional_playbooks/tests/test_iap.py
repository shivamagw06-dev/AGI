"""AGIB v3.5 — Institutional Analytical Playbooks (IAP) acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_playbooks import IAP_VERSION, select_playbook
from institutional_playbooks.production import dashboard, health, playbook, registry, select
from institutional_playbooks.registry.index import category_counts, list_playbooks, playbook_ids
from institutional_playbooks.schema import TARGET_COUNTS
from institutional_communication import communicate_from_ask

ROOT = Path(__file__).resolve().parents[1]


def test_iap_version_and_registry_size() -> None:
    assert IAP_VERSION.startswith("institutional-playbooks")
    ids = playbook_ids()
    assert len(ids) >= 50
    assert "PB_VAL_PREMIUM_MULTIPLE" in ids
    assert "PB_VAL_BANK_PB_RI" in ids
    assert "PB_DOC_ANNUAL_REPORT" in ids
    assert "PB_COMPANY_RESULTS_REACTION" in ids
    assert health()["status"] == "ok"
    assert registry()["n"] >= 50
    counts = category_counts()
    for cat, n in TARGET_COUNTS.items():
        assert counts.get(cat, 0) >= n, f"{cat} expected >= {n}, got {counts.get(cat)}"
    assert dashboard()["target_met"] is True


def test_every_playbook_has_required_fields() -> None:
    for pb in list_playbooks():
        assert pb.get("playbook_id")
        assert pb.get("name")
        assert pb.get("category")
        assert pb.get("checklist"), pb["playbook_id"]
        assert pb.get("procedure"), pb["playbook_id"]
        assert pb.get("frameworks"), pb["playbook_id"]
        assert pb.get("evidence_required"), pb["playbook_id"]
        assert pb.get("common_mistakes"), pb["playbook_id"]
        assert pb.get("output_structure"), pb["playbook_id"]
        assert len(pb["checklist"]) >= 5


def test_premium_valuation_playbook() -> None:
    sel = select_playbook(
        question="Why does this stock trade at a premium multiple?",
        intent_v2="Explain",
        question_type="Explain",
        framework_ids=["FW_DCF", "FW_HISTORICAL_VALUATION", "FW_ROIC"],
    )
    assert sel["playbook_id"] == "PB_VAL_PREMIUM_MULTIPLE"
    labels = [s["label"].lower() for s in (sel["checklist"]["steps"] or [])]
    assert any("moat" in x for x in labels)
    assert any("roic" in x for x in labels)
    assert "→" in (sel["procedure"].get("arrow_text") or "")
    assert sel["guides_reasoning"] is True
    assert sel["reasoning_changed"] is False
    assert (sel.get("validation") or {}).get("passed") is True


def test_bank_valuation_procedure() -> None:
    sel = select_playbook(
        question="Why is HDFC Bank primarily valued using Price-to-Book and Residual Income?",
        intent_v2="Explain",
        sector="banks",
        framework_ids=["FW_PB", "FW_RESIDUAL_INCOME", "FW_ROE"],
    )
    assert sel["playbook_id"] == "PB_VAL_BANK_PB_RI"
    arrow = (sel["procedure"].get("arrow_text") or "").lower()
    for token in ("book value", "roe", "residual income", "npa", "casa", "nim", "peers", "conclusion"):
        assert token in arrow, token
    assert "Using EV/EBITDA for banks" in (sel.get("common_mistakes") or [])


def test_annual_report_playbook_fixes_q22_shape() -> None:
    sel = select_playbook(
        question="How should an analyst read the annual report?",
        intent_v2="Analyse",
        question_type="Document",
        concept_mode=True,
    )
    assert sel["playbook_id"] == "PB_DOC_ANNUAL_REPORT"
    arrow = (sel["procedure"].get("arrow_text") or "").lower()
    for token in ("mda", "risk factors", "auditor", "related party", "contingent", "governance", "conclusion"):
        assert token in arrow, token


def test_results_reaction_playbook() -> None:
    sel = select_playbook(
        question="Why did the stock fall after good results?",
        intent_v2="Explain",
        question_type="Event",
    )
    assert sel["playbook_id"] == "PB_COMPANY_RESULTS_REACTION"
    arrow = (sel["procedure"].get("arrow_text") or "").lower()
    assert "expectation miss" in arrow
    assert "guidance" in arrow
    assert "valuation already rich" in arrow
    assert "liquidity" in arrow


def test_ic_initiate_coverage() -> None:
    sel = select_playbook(
        question="Should we initiate coverage and buy a new position?",
        intent_v2="Assess",
        question_type="IC",
    )
    assert sel["playbook_id"] == "PB_IC_INITIATE_COVERAGE"
    assert any("kill" in str(x).lower() for x in (sel.get("checklist") or {}).get("steps") or [])


def test_production_select_and_get() -> None:
    out = select(question="Explain EV/EBITDA for an industrial company", intent_v2="Explain")
    assert out["ok"] is True
    assert out["playbook_id"]
    detail = playbook(out["playbook_id"])
    assert detail["found"] is True


def test_ice_surfaces_playbook_checklist() -> None:
    sel = select_playbook(
        question="How should an analyst read the annual report?",
        intent_v2="Analyse",
        concept_mode=True,
    )
    comm = communicate_from_ask(
        question="How should an analyst read the annual report?",
        intent_resolution={"intent": "Analyse", "concept_mode": True, "question_type": "Document"},
        framework_selection={
            "framework_ids": ["FW_ACCOUNTING", "FW_GOVERNANCE"],
            "selected": [],
            "explanation": {"reason": "Document review frameworks"},
            "confidence": {"band": "medium", "pct": 60},
            "sector": "generic",
        },
        playbook_selection=sel,
        institutional_answer={
            "sections": {
                "analysis": {"bullets": ["Thin prior analysis"]},
            },
            "confidence": {"band": "medium", "pct": 55},
        },
    )
    prose = (comm.get("prose") or "").lower()
    assert "annual report" in prose or "analytical playbook" in prose
    assert "related party" in prose or "□" in (comm.get("prose") or "")
    assert comm.get("playbook_visible") is True
    assert "analytical_checklist" in (comm.get("sections") or {})


def test_cue_repo_does_not_match_report() -> None:
    """Regression: single-token cue 'repo' must not fire inside 'report'."""
    sel = select_playbook(
        question="How would you detect inconsistencies between an investor presentation and the audited annual report?",
        intent_v2="Analyse",
        sector="it_services",
        framework_ids=["FW_DCF", "FW_EV_EBITDA", "FW_HISTORICAL_VALUATION"],
    )
    assert sel["playbook_id"] == "PB_DOC_ANNUAL_REPORT"
    assert sel["playbook_id"] != "PB_MACRO_RATE_TRANSMISSION"


def test_initiate_coverage_cue() -> None:
    sel = select_playbook(
        question="What evidence should AGIB gather before recommending that an analyst initiate research coverage on a newly listed Indian company?",
        intent_v2="Assess",
        question_type="IC",
    )
    assert sel["playbook_id"] == "PB_IC_INITIATE_COVERAGE"


def test_no_llm_imports_in_iap_package() -> None:
    banned = ("openai", "anthropic", "litellm", "langchain")
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(b in alias.name.lower() for b in banned)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(b in node.module.lower() for b in banned)
