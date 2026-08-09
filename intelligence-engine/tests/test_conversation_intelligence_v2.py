from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
app_pkg = sys.modules.setdefault("app", types.ModuleType("app"))
ui_pkg = sys.modules.setdefault("app.ui", types.ModuleType("app.ui"))
ui_pkg.__path__ = [str(ROOT / "app" / "ui")]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "app" / "ui" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_load("app.ui.conversation_checkpoints", "conversation_checkpoints.py")
ConversationStore = _load("app.ui.conversation_context", "conversation_context.py").ConversationStore


class MemoryCheckpoint:
    def __init__(self):
        self.rows = {}

    def load(self, thread_id):
        return self.rows.get(thread_id)

    def save(self, thread_id, payload):
        self.rows[thread_id] = dict(payload)

    def delete(self, thread_id):
        self.rows.pop(thread_id, None)


def tickers(question: str) -> list[str]:
    out = []
    for name, ticker in (("tcs", "TCS"), ("infosys", "INFY"), ("reliance", "RELIANCE")):
        if name in question.lower():
            out.append(ticker)
    return out


def resolve(store, question, cid="thread-1"):
    return store.resolve(question, conversation_id=cid, ticker=None, ticker_extractor=tickers)


def test_conversation_moves_and_execution_policy():
    store = ConversationStore(checkpoint_backend=MemoryCheckpoint())
    _, _, hi = resolve(store, "hi")
    assert hi["conversation_move"] == "GREETING"
    assert hi["research_execution"] == "SKIP"
    assert hi["research_required"] is False

    resolve(store, "Analyse TCS")
    _, ticker, follow = resolve(store, "what about its valuation?")
    assert ticker == "TCS"
    assert follow["conversation_move"] == "FOLLOW_UP"
    assert follow["research_intent"] == "VALUATION"
    assert follow["research_execution"] == "INCREMENTAL_RETRIEVAL"


def test_reuse_previous_answer_without_research():
    store = ConversationStore(checkpoint_backend=MemoryCheckpoint())
    _, _, first = resolve(store, "Analyse TCS")
    store.record_answer(
        first["conversation_id"], question="Analyse TCS",
        answer_summary="TCS has durable client relationships, but valuation evidence is incomplete.",
        research_artifact_ref="ask-run-123",
    )
    _, _, simple = resolve(store, "explain that simply")
    assert simple["conversation_move"] == "SIMPLIFY"
    assert simple["research_execution"] == "REUSE_PREVIOUS"
    assert simple["previous_answer_reused"] is True
    assert simple["previous_evidence_reused"] is True


def test_checkpoint_survives_store_restart_and_excludes_raw_evidence():
    backend = MemoryCheckpoint()
    first = ConversationStore(checkpoint_backend=backend)
    _, _, trace = resolve(first, "Analyse TCS", cid="durable")
    first.record_answer(
        trace["conversation_id"], question="Analyse TCS",
        answer_summary="Compact approved summary", research_artifact_ref="artifact-7",
    )
    second = ConversationStore(checkpoint_backend=backend)
    _, ticker, follow = resolve(second, "what about its valuation?", cid="durable")
    assert ticker == "TCS"
    assert follow["context_source"] == "THREAD_CHECKPOINT"
    payload = backend.rows["durable"]
    assert "evidence" not in payload
    assert "prompt" not in payload


def test_challenge_correction_and_capability_routes():
    store = ConversationStore(checkpoint_backend=MemoryCheckpoint())
    resolve(store, "Analyse Reliance")
    for question, move, execution in (
        ("I disagree", "CHALLENGE", "INCREMENTAL_RETRIEVAL"),
        ("that's wrong", "CORRECTION", "INCREMENTAL_RETRIEVAL"),
        ("what can you do?", "CAPABILITY_QUESTION", "SKIP"),
        ("thanks", "THANKS", "SKIP"),
    ):
        _, _, trace = resolve(store, question)
        assert trace["conversation_move"] == move
        assert trace["research_execution"] == execution
