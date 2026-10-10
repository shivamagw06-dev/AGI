"""AGIB v1.2 — Institutional Universe Intelligence schemas.

Architecture (soft registry layer — NOT a reasoning engine):

    Universe Registry
            │
            ▼
    Universe Membership Engine   (point-in-time)
            │
            ▼
    Company Registry
            │
            ▼
    Knowledge Factory            (FROZEN)
            │
            ▼
    Evidence Factory             (soft KF packs)
            │
            ▼
    Existing Institutional Reasoning  (Phases 1–7 FROZEN)

Freeze locks:
  - Reasoning Architecture Frozen v1.0 (Phases 1–7)
  - Knowledge Factory architecture frozen
  - Decision Quality observability frozen
  - No new engines / planners / committees / governance / learning
  - Frameworks never call APIs directly
  - Never fabricate
"""

from __future__ import annotations

from typing import Any

IUI_VERSION = "institutional-universe-intelligence-v1.2.0"
IUI_SCHEMA_VERSION = "iui-schema-v1.2.0"
PROGRAMME = "AGIB v1.2 – Institutional Universe Intelligence"
LAYER = "IUI"
ARCHITECTURE_STATUS = "SOFT_UNIVERSE_REGISTRY"

# ---------------------------------------------------------------------------
# Coverage Levels — only Level 7 = Institutional Coverage
# ---------------------------------------------------------------------------
COVERAGE_LEVELS: dict[int, str] = {
    0: "discovered",
    1: "identity",
    2: "financials",
    3: "historical",
    4: "sector",
    5: "macro",
    6: "evidence_packs",
    7: "decision_ready",
}

INSTITUTIONAL_COVERAGE_LEVEL = 7

# ---------------------------------------------------------------------------
# Institutional Coverage Index (ICI) — weighted readiness score
# ---------------------------------------------------------------------------
ICI_WEIGHTS: dict[str, float] = {
    "identity": 0.10,
    "historical_depth": 0.20,
    "financial_intelligence": 0.15,
    "sector_intelligence": 0.10,
    "macro_intelligence": 0.10,
    "risk_intelligence": 0.10,
    "evidence_packs": 0.15,
    "portfolio_readiness": 0.05,
    "decision_readiness": 0.05,
}

assert abs(sum(ICI_WEIGHTS.values()) - 1.0) < 1e-9

# Institutional quality gates — one failure ⇒ not institutional-ready
QUALITY_GATES: tuple[str, ...] = (
    "identity",
    "historical",
    "accounting",
    "sector",
    "macro",
    "risk",
    "evidence",
    "replay",
    "decision",
)

# Cross-universe taxonomy (future-proof; India first)
UNIVERSE_FAMILIES: tuple[str, ...] = (
    "india_nifty",
    "india_thematic",
    "global_large_cap",
)

# Provenance required fields on every registry field envelope
PROVENANCE_FIELDS: tuple[str, ...] = (
    "source",
    "retrieved_at",
    "validated_at",
    "confidence",
    "collector",
    "derived_from",
)

FREEZE_LOCKS: dict[str, Any] = {
    "reasoning_architecture": "FROZEN_V1",
    "phases_1_7": True,
    "knowledge_factory_architecture": True,
    "decision_quality": True,
    "not_a_reasoning_engine": True,
    "not_a_planner": True,
    "not_governance": True,
    "not_learning_system": True,
    "no_raw_api_to_frameworks": True,
    "never_fabricate": True,
}


def coverage_level_name(level: int) -> str:
    return COVERAGE_LEVELS.get(int(level), "unknown")


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "iui_version": IUI_VERSION,
        "iui_schema_version": IUI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "kind": kind,
        "architecture_status": ARCHITECTURE_STATUS,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        **extra,
        **payload,
    }
