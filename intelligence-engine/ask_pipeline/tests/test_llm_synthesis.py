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
            "thesis": ["The order supports revenue visibility [E1]."],
            "bull_case": ["Execution could deepen the customer relationship [E1]."],
            "bear_case": ["Margin and delivery timing are not disclosed [E1]."],
            "catalysts": ["Execution updates [E1]."],
            "risks": ["Delivery slippage [E1]."],
            "valuation": ["No valuation evidence was supplied."],
            "what_changes_view": ["A cancellation would weaken the view [E1]."],
            "evidence_gaps": ["Order margin and schedule."],
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
    assert result["answer"]["investment_sections"]["risks"]
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


def test_unsupported_financial_figure_uses_fallback(monkeypatch):
    class FabricatedResponse(_Response):
        output_text = json.dumps(
            {
                "executive_summary": "The order is worth ₹999 crore [E1].",
                "why": ["The filing supports it [E1]."],
                "prose": "The order supports the thesis at an invented 45x multiple [E1].",
                "cited_evidence_ids": ["E1"],
            }
        )

    class FabricatingResponses:
        def create(self, **kwargs):
            return FabricatedResponse()

    class FabricatingOpenAI:
        def __init__(self, **kwargs):
            self.responses = FabricatingResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FabricatingOpenAI))
    result = synthesize_financial_answer(
        question="What is the view?",
        evidence=_evidence(),
        intent_resolution={},
        entities={"entities": ["ZENTEC"]},
        deterministic_answer={"executive_summary": "Fallback"},
    )
    assert result["used"] is False
    assert result["status"] == "fallback"
    assert result["error_type"] == "ValueError"


def test_primary_and_uploaded_evidence_is_prioritised_and_deduplicated(monkeypatch):
    evidence = _evidence()
    rows = evidence["packs"]["iere"]["evidence"]["top_evidence"]
    rows.insert(0, {"title": "Market snapshot", "source": "aggregator", "payload": {"price": 1}})
    rows.append({"title": "Duplicate filing", "source": "company filing", "payload": {"order_value_crore": 295}})
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    result = synthesize_financial_answer(
        question="What is the view?", evidence=evidence, intent_resolution={},
        entities={"entities": ["ZENTEC"]}, deterministic_answer={"executive_summary": "Fallback"},
    )
    assert result["used"] is True
    supplied = json.loads(_OpenAI.last.responses.kwargs["input"].split("EVIDENCE\n", 1)[1])
    assert supplied[0]["source"] == "company filing"
    assert len(supplied) == 2
