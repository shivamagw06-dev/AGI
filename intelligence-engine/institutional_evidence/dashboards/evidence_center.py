"""Mission Control Evidence Center board payload."""

from __future__ import annotations

from typing import Any, Dict

from ..production import get_evidence_center_board, get_phase1_coverage


def evidence_center_payload() -> Dict[str, Any]:
    board = get_evidence_center_board()
    cov = get_phase1_coverage()
    return {
        **board,
        "phase1_companies": cov.get("companies"),
        "title": "Institutional Evidence Platform",
        "subtitle": "Evidence-first foundation for AGI v1.1",
    }
