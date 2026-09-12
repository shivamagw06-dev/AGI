import json
import sys
import types
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from cid.openai_dossier import SECTIONS, _response_schema, evidence_rows, generate
from ask_pipeline.llm_synthesis import _evidence_rows


def _dossier():
    return {
        "ticker": "INFY",
        "identity": {"company_name": "Infosys", "industry": "IT Services"},
        "financial_metrics": {"roe": 30.0},
        "valuation": {"current": {"pe": 24.0}},
        "evidence_timeline": [
            {"evidence_id": "E-AR", "evidence_type": "annual_report", "title": "Annual report", "value_text": "Revenue grew."}
        ],
    }


def test_evidence_rows_are_addressable():
    rows = evidence_rows(_dossier())
    assert rows[0]["id"] == "W1"
    assert any(row["id"] == "E-AR" for row in rows)


def test_structured_output_schema_requires_every_section():
    schema = _response_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["sections"]["required"] == list(SECTIONS)
    assert schema["properties"]["sections"]["additionalProperties"] is False
    section = schema["properties"]["sections"]["properties"][SECTIONS[0]]
    assert section["properties"]["summary"]["maxLength"] == 500
    assert section["properties"]["claims"]["maxItems"] == 4
    assert schema["properties"]["long_company_narrative"]["maxLength"] == 6000


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.setenv("CID_OPENAI_ENABLED", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = generate("INFY", _dossier())
    assert out["ok"] is False
    assert out["error"] == "missing_openai_api_key"


def test_generation_keeps_only_valid_citations(monkeypatch):
    payload = {
        "executive_summary": "Evidence-grounded summary.",
        "long_company_narrative": "A long evidence-grounded company narrative.",
        "long_company_narrative_evidence_ids": ["W1", "FAKE"],
        "long_company_narrative_confidence": 0.75,
        "sections": {
            name: {"summary": name, "claims": ["claim"], "evidence_ids": ["W1", "FAKE"], "confidence": 0.8}
            for name in SECTIONS
        },
    }

    class Response:
        id = "resp_1"
        output_text = json.dumps(payload)
        usage = types.SimpleNamespace(input_tokens=100, output_tokens=200)

    class Client:
        def __init__(self, **kwargs):
            self.responses = self

        def create(self, **kwargs):
            assert kwargs["store"] is False
            assert kwargs["text"]["format"]["type"] == "json_schema"
            assert kwargs["text"]["format"]["strict"] is True
            return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("CID_OPENAI_ENABLED", "true")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=Client))
    monkeypatch.setattr("cid.persistence.save_version", lambda dossier: {"persisted": True, "version": 3})
    out = generate("INFY", _dossier())
    assert out["ok"] is True
    assert out["research"]["sections"]["risks"]["evidence_ids"] == ["W1"]
    assert out["research"]["long_company_narrative_evidence_ids"] == ["W1"]
    assert out["research"]["long_company_narrative_confidence"] == 0.75
    assert out["dossier"]["financial_metrics"]["roe"] == 30.0
    assert out["dossier"]["persisted_version"] == 3


def test_ask_grounding_can_consume_persisted_dossier_sections():
    supplemental = {
        "company_dossier": {
            "ticker": "INFY",
            "openai_research": {
                "generated_at": "2026-08-12T00:00:00Z",
                "sections": {
                    "business_model": {
                        "summary": "Revenue is tied to contracted technology services.",
                        "evidence_ids": ["W1", "E-AR"],
                        "confidence": 0.8,
                    }
                },
            },
        }
    }
    rows = _evidence_rows({}, supplemental)
    assert any(row["source"] == "AGI knowledge dossier synthesis" for row in rows)
    assert any("contracted technology services" in row["content"] for row in rows)
