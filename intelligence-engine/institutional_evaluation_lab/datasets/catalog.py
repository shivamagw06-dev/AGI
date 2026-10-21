"""Unified question catalog — CIO gold + institutional 1000+ + Phase 1 universe."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.datasets.cio_frozen_25 import CIO_FROZEN_25
from institutional_evaluation_lab.datasets.generator import generate_institutional_library
from institutional_evaluation_lab.datasets.investor_100 import INVESTOR_100
from institutional_evaluation_lab.datasets.cre_investment_144 import CRE_INVESTMENT_144
from institutional_evaluation_lab.datasets.phase1_golden_universe import (
    load_universe as load_phase1_universe,
    universe_board as phase1_universe_board,
)

_CACHE: dict[str, list[dict[str, Any]]] = {}


def load_suite(suite: str = "institutional_1000") -> list[dict[str, Any]]:
    if suite in _CACHE:
        return list(_CACHE[suite])
    if suite == "cio_frozen_25":
        rows = list(CIO_FROZEN_25)
    elif suite in {"investor_100", "investor100"}:
        rows = list(INVESTOR_100)
    elif suite in {"cre_investment_144", "cre_144"}:
        rows = list(CRE_INVESTMENT_144)
    elif suite == "smoke":
        rows = list(CIO_FROZEN_25[:5]) + generate_institutional_library(target=20)[:15]
    elif suite in {"phase1_golden_200", "phase1_golden"}:
        rows = load_phase1_universe()
    elif suite in {"institutional_1000", "all"}:
        gen = generate_institutional_library(target=1000)
        if suite == "all":
            rows = list(CIO_FROZEN_25) + gen
        else:
            rows = gen
    else:
        raise ValueError(f"unknown_suite:{suite}")
    _CACHE[suite] = rows
    return list(rows)


def catalog_stats() -> dict[str, Any]:
    cio = load_suite("cio_frozen_25")
    inst = load_suite("institutional_1000")
    investor = load_suite("investor_100")
    cre = load_suite("cre_investment_144")
    all_rows = load_suite("all")
    phase1 = phase1_universe_board()
    by_cat: dict[str, int] = {}
    for r in all_rows:
        by_cat[str(r.get("category"))] = by_cat.get(str(r.get("category")), 0) + 1
    return {
        "cio_frozen_25": len(cio),
        "institutional_1000": len(inst),
        "investor_100": len(investor),
        "cre_investment_144": len(cre),
        "all": len(all_rows),
        "phase1_golden_200": phase1.get("n"),
        "phase1_golden_valid": phase1.get("valid"),
        "phase1_bucket_counts": (phase1.get("summary") or {}).get("bucket_counts"),
        "by_category": by_cat,
        "min_required": 1000,
        "meets_1000_plus": len(inst) >= 1000,
    }


def get_question(question_id: str) -> dict[str, Any] | None:
    for suite in ("cio_frozen_25", "investor_100", "cre_investment_144", "institutional_1000"):
        for q in load_suite(suite):
            if q.get("question_id") == question_id:
                return q
    return None
