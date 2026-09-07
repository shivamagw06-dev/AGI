"""IPO Mission Control dashboard."""

from __future__ import annotations

from typing import Any

from institutional_portfolio_office import store as idea_store
from institutional_portfolio_office.schema import (
    COMPANY,
    IDEA_SCHEMA_VERSION,
    IPO_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
)


def build_board() -> dict[str, Any]:
    tel = idea_store.telemetry_snapshot()
    it = idea_store.list_ideas(sector="IT Services", limit=20)
    ranking = [
        {
            "rank": x.get("relative_rank"),
            "ticker": x.get("ticker"),
            "company": x.get("company"),
            "role": x.get("expected_role"),
            "conviction": x.get("conviction"),
        }
        for x in it
        if x.get("status") in {"Candidate", "Active Consideration"}
    ]
    ranking.sort(key=lambda r: int(r.get("rank") or 999))
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "programme": PROGRAMME,
        "version": IPO_VERSION,
        "schema_version": IDEA_SCHEMA_VERSION,
        "release": "AGI v4.0",
        "n_ideas": tel.get("n_ideas"),
        "role_distribution": tel.get("role_distribution"),
        "sector_distribution": tel.get("sector_distribution"),
        "status_distribution": tel.get("status_distribution"),
        "it_services_relative_ranking": ranking[:10],
        "recent": tel.get("recent"),
        "positions": False,
        "orders": False,
        "execution": False,
        "positions_stored": 0,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }
