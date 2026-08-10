from __future__ import annotations

import json
import sys
import types

from ask_pipeline.llm_synthesis import synthesize_financial_answer


def _evidence() -> dict:
    return {
        "packs": {
            "iere": {
                "evidence": {
                    "top_evidence": [
                        {
                            "title": "Zen Technologies order announcement",
                            "source": "company filing",
                            "available_from": "2026-08-01",
                            "payload": {"order_value_crore": 295},
                        }
                    ]
                }
            }
        }
    }


class _Usage:
    input_tokens = 321
    output_tokens = 123


class _Response:
    id = "resp_test"
    usage = _Usage()
    output_text = json.dumps(
        {
            "executive_summary": "The order is material based on the supplied filing [E1].",
            "why": ["The disclosed order value is ₹295 crore [E1]."],
            "prose": "The filing supports the order value; margin impact is not disclosed [E1].",
            "cited_evidence_ids": ["E1", "E999"],
            "uncertainty": "Execution timing and margins were not supplied.",
        }
    )


class _Responses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _Response()


class _OpenAI:
    last = None

    def __init__(self, **kwargs):
        self.responses = _Responses()
        _OpenAI.last = self


def test_synthesis_calls_responses_api_and_filters_citations(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ASK_REASONING_MODEL", "gpt-5.6-terra")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))

    result = synthesize_financial_answer(
        question="What is the view?",
        evidence=_evidence(),
        intent_resolution={"intent": "research"},
        entities={"entities": ["ZENTEC"]},
        deterministic_answer={"executive_summary": "Fallback"},
    )

    assert result["used"] is True
    assert result["status"] == "completed"
    assert result["answer"]["cited_evidence_ids"] == ["E1"]
    assert _OpenAI.last.responses.kwargs["store"] is False
    assert _OpenAI.last.responses.kwargs["reasoning"] == {"effort": "medium"}
    assert "order_value_crore" in _OpenAI.last.responses.kwargs["input"]
    assert "295" in _OpenAI.last.responses.kwargs["input"]


def test_missing_key_uses_deterministic_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = synthesize_financial_answer(
        question="What is the view?",
        evidence=_evidence(),
        intent_resolution={},
        entities={},
        deterministic_answer={"executive_summary": "Fallback"},
    )
    assert result["used"] is False
    assert result["status"] == "missing_api_key"


def test_api_error_does_not_break_ask(monkeypatch):
    class BrokenResponses:
        def create(self, **kwargs):
            raise TimeoutError("upstream timed out")

    class BrokenOpenAI:
        def __init__(self, **kwargs):
            self.responses = BrokenResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=BrokenOpenAI))
    result = synthesize_financial_answer(
        question="What is the view?",
        evidence=_evidence(),
        intent_resolution={},
        entities={},
        deterministic_answer={"executive_summary": "Fallback"},
    )
    assert result["used"] is False
    assert result["status"] == "fallback"
    assert result["error_type"] == "TimeoutError"
