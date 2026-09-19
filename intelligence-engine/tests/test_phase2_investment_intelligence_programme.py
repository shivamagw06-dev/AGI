"""Phase 2 programme registry — must not claim to replace Baseline v1.0."""

from __future__ import annotations

from pathlib import Path

from phase2_investment_intelligence.contract import (
    empty_engine_payload,
    validate_engine_payload,
)
from phase2_investment_intelligence.production import contracts, health, programme, scorecard
from phase2_investment_intelligence.schema import FROZEN_BASELINE_LOCKS, SUCCESS_CRITERIA
from phase2_investment_intelligence.scorecard import DEFINITION_OF_DONE
from phase2_investment_intelligence.workstreams import WORKSTREAMS, workstream_board


def test_phase2_health_respects_baseline_freeze():
    h = health()
    assert h["baseline"]["status"] == "FROZEN"
    assert h["replaces_baseline"] is False
    assert h["extends_intelligence"] is True
    assert h["standard_engine_contract"] is True
    assert h["intelligence_scorecard"] is True
    assert FROZEN_BASELINE_LOCKS["decision_engine_contracts"] == "frozen"
    assert FROZEN_BASELINE_LOCKS["institutional_gate"] == "frozen"
    assert FROZEN_BASELINE_LOCKS["institutional_acceptance_test"] == "frozen"
    assert "unknown_drift_zero" in SUCCESS_CRITERIA
    assert "iat_continues_to_pass" in SUCCESS_CRITERIA


def test_workstreams_cover_p21_to_p26():
    ids = {w["id"] for w in WORKSTREAMS}
    assert ids == {"P2.1", "P2.2", "P2.3", "P2.4", "P2.5", "P2.6"}
    board = workstream_board()
    assert board["recommended_first_build"] == ["P2.6", "P2.3", "P2.1"]
    assert board["implementation_order"][:3] == ["P2.6", "P2.3", "P2.1"]


def test_standard_engine_contract_and_degrade():
    c = contracts()
    assert "ownership_intelligence" in c["engines"]
    own = c["engines"]["ownership_intelligence"]
    assert own["failure_mode"]["block_unrelated_engines"] is False
    assert set(own["consumers"]) == {"decision_engine", "evaluation_lab"}
    payload = empty_engine_payload("ownership_intelligence", ticker="ETERNAL", reason="pack_missing")
    v = validate_engine_payload(payload)
    assert v["ok"] is True
    assert payload["degraded"] is True
    assert payload["fabricated"] is False


def test_intelligence_scorecard_and_dod():
    board = scorecard()
    assert board["n"] == 6
    assert "demonstrable_improvement_on_one_intelligence_metric" in DEFINITION_OF_DONE
    assert board["targets"]["coverage_pct_min"] == 95.0
    assert board["targets"]["unknown_drift_max"] == 0


def test_programme_doc_exists():
    root = Path(__file__).resolve().parents[2]
    doc = root / "docs" / "PHASE2_INSTITUTIONAL_INVESTMENT_INTELLIGENCE_PROGRAMME.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "Institutional Investment Intelligence Programme" in text
    assert "Standard engine contract" in text
    assert "Intelligence Scorecard" in text
    assert "Definition of Done" in text
    assert "AGIB Institutional Baseline v1.0" in text


def test_programme_pipeline_ends_with_iat():
    pack = programme()
    assert pack["pipeline"][-1] == "Institutional Acceptance Test"
    assert "redesign_decision_engine" in pack["prohibited"]
    assert pack["contracts"]["standard_contract"] is True
    assert pack["intelligence_scorecard_board"]["n"] == 6
