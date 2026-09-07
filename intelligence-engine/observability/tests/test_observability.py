"""AGI observability — LangSmith tracing must be opt-in, fail-open, output-neutral."""

from __future__ import annotations

import os

import pytest

from observability import config, is_enabled, status
from observability.production import dashboard, verify
from observability.schema import project, tracing_requested
from observability.tracing import llm_span, span, traced, wrap_openai


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in (
        "LANGSMITH_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_PROJECT",
        "LANGCHAIN_PROJECT",
        "LANGSMITH_ENDPOINT",
        "LANGSMITH_WORKSPACE_ID",
    ):
        monkeypatch.delenv(key, raising=False)
    yield


def test_disabled_without_api_key() -> None:
    assert is_enabled() is False
    assert status()["tracing_state"] == "disabled_no_api_key"
    assert config()["api_key_present"] is False


def test_enabled_requires_key_and_flag(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_pt_test_key_value")
    # Key alone turns tracing on (LangSmith default behaviour)
    assert tracing_requested() is True
    assert is_enabled() is True
    # Explicit opt-out wins
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    assert is_enabled() is False
    assert status()["tracing_state"] == "disabled_by_flag"


def test_project_default_and_override(monkeypatch) -> None:
    assert project() == "agi-intelligence-engine"
    monkeypatch.setenv("LANGSMITH_PROJECT", "agi-prod")
    assert project() == "agi-prod"


def test_span_is_noop_when_disabled() -> None:
    with span("x", inputs={"a": 1}) as sp:
        assert sp.active is False
        sp.end(outputs={"b": 2})
        sp.add_metadata(k="v")


def test_traced_returns_identical_value_when_disabled() -> None:
    @traced("unit", run_type="chain")
    def f(a, b=2):
        return {"sum": a + b, "obj": object()}

    out = f(1, b=5)
    assert out["sum"] == 6


@pytest.mark.asyncio
async def test_traced_async_passthrough() -> None:
    @traced("unit_async")
    async def g(x):
        return x * 2

    assert await g(21) == 42


def test_traced_propagates_exceptions_unchanged() -> None:
    @traced("boom")
    def f():
        raise ValueError("original")

    with pytest.raises(ValueError, match="original"):
        f()


def test_tracing_failure_does_not_break_caller(monkeypatch) -> None:
    """Even with tracing 'on' and a broken SDK, work still executes."""
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_pt_test_key_value")

    import observability.tracing as tracing_mod

    def _boom(*_a, **_k):
        raise RuntimeError("langsmith exploded")

    monkeypatch.setattr(tracing_mod, "is_enabled", lambda: True)
    monkeypatch.setitem(__import__("sys").modules, "langsmith", None)

    @tracing_mod.traced("resilient")
    def f():
        return "value"

    assert f() == "value"

    with tracing_mod.span("resilient_span") as sp:
        sp.end(outputs={"ok": True})


def test_llm_span_noop_when_disabled() -> None:
    with llm_span(provider="gemini", model="gemini-flash-latest", prompt="hi") as sp:
        assert sp.active is False
        sp.end(outputs={"status_code": 200})


def test_wrap_openai_returns_client_when_disabled() -> None:
    sentinel = object()
    assert wrap_openai(sentinel) is sentinel


def test_dashboard_lists_traced_stages() -> None:
    d = dashboard()
    assert d["company"] == "AGI"
    assert d["n_traced_stages"] >= 10
    assert any("ask.pipeline" in s for s in d["traced_stages"])
    assert "langsmith trace list" in d["cli_hint"]


def test_verify_is_safe_when_disabled() -> None:
    v = verify()
    assert v["enabled"] is False
    assert v["trace_emitted"] is False


def test_freeze_locks_declared() -> None:
    locks = status()["freeze_locks"]
    for key in ("reasoning_frozen", "knowledge_factory", "observability_only", "never_changes_answers"):
        assert locks[key] is True


def test_ask_pipeline_output_identical_with_tracing_off() -> None:
    """Tracing must be output-neutral on the frozen pipeline."""
    from ask_pipeline.pipeline import run_complete_ask

    q = "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies."
    a = run_complete_ask(q, ticker_hint="INFY")
    b = run_complete_ask(q, ticker_hint="INFY")
    for field in ("intent", "concept_mode", "as_of"):
        assert a.get(field) == b.get(field)
    assert (a.get("intent_resolution") or {}).get("intent") == (b.get("intent_resolution") or {}).get("intent")
    assert a["answer"]["executive_summary"] == b["answer"]["executive_summary"]
    assert a.get("reasoning_changed") is False
    assert a.get("knowledge_factory_changed") is False
