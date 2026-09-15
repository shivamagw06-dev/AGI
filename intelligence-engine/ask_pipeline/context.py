"""S01 — AskContext builder."""

from __future__ import annotations

import uuid
from typing import Any

from ask_pipeline.schema import PIPELINE_VERSION, PROGRAMME
from ask_pipeline.store import utc_now


def build_ask_context(
    question: str,
    *,
    session_id: str | None = None,
    conversation_id: str | None = None,
    ticker_hint: str | None = None,
    requested_depth: str | None = None,
    requested_horizon: str | None = None,
    requested_asset: str | None = None,
    requested_portfolio: str | None = None,
    jurisdiction: str | None = None,
    knowledge_version: str | None = None,
    evidence_version: str | None = None,
) -> dict[str, Any]:
    pipeline_id = f"askp_{uuid.uuid4().hex[:16]}"
    replay_id = f"replay_{uuid.uuid4().hex[:16]}"
    return {
        "pipeline_id": pipeline_id,
        "replay_id": replay_id,
        "programme": PROGRAMME,
        "pipeline_version": PIPELINE_VERSION,
        "question": str(question or "")[:2000],
        "timestamp": utc_now(),
        "session_id": session_id or f"session_{uuid.uuid4().hex[:10]}",
        "conversation_id": conversation_id or f"conv_{uuid.uuid4().hex[:10]}",
        "ticker_hint": (str(ticker_hint).upper() if ticker_hint else None),
        "intent": None,
        "entities": [],
        "requested_depth": requested_depth or "standard",
        "requested_horizon": requested_horizon or "unspecified",
        "requested_asset": requested_asset,
        "requested_portfolio": requested_portfolio,
        "jurisdiction": jurisdiction or "IN",
        "knowledge_version": knowledge_version or "kf-track1",
        "evidence_version": evidence_version or "evidence-v1",
        "fabricated": False,
    }
