import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from cid import learning
from cid.openai_dossier import evidence_rows


def test_learning_retains_form_not_company_prose(monkeypatch, tmp_path):
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path))
    research = {
        "executive_summary": "Company-specific secret prose.",
        "long_company_narrative": "A long company-specific paragraph.",
        "sections": {"risks": {"summary": "Specific risk.", "claims": ["x"], "evidence_ids": ["W1"]}},
    }
    profile = learning.learn_from_success(research)
    saved = learning.load_profile()
    assert profile["successful_examples"] == 1
    assert "Company-specific secret prose" not in str(saved)
    assert saved["section_claims"]["risks"] == 1


def test_fallback_is_explicit_and_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path))
    learning.learn_from_success({"executive_summary": "x", "long_company_narrative": "x", "sections": {}})
    monkeypatch.setattr(learning, "save_version", lambda dossier: {"persisted": True, "version": 1})
    dossier = {
        "ticker": "INFY",
        "identity": {"company_name": "Infosys"},
        "business_profile": {"business_model": "Technology services"},
        "financial_metrics": {"roe": 30},
        "valuation": {"current": {"pe": 24}},
        "warehouse_evidence": {"research_intelligence": [{"risk": "Client concentration"}]},
    }
    out = learning.compose("INFY", dossier, reason="insufficient_quota")
    assert out["ok"] is True
    assert out["research"]["provider"] == "agi"
    assert out["research"]["quality_status"] == "not_equivalent_to_openai_model_reasoning"
    valid_ids = {row["id"] for row in evidence_rows(dossier)}
    cited_ids = {
        evidence_id
        for section in out["research"]["sections"].values()
        for evidence_id in section["evidence_ids"]
    }
    assert cited_ids <= valid_ids
