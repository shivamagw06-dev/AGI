"""IMAI report helper for CIO / Mission Control."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.dashboard.board import build_board
from institutional_analog_intelligence.registry.index import registry_snapshot


def build_report() -> dict[str, Any]:
    board = build_board()
    snap = registry_snapshot()
    return {
        "title": "Institutional Memory & Analog Intelligence — Status",
        "board": board,
        "registry": snap,
        "objective": "Have we seen this before?",
        "augments_reasoning": True,
        "replaces_reasoning": False,
        "fabricated": False,
    }
