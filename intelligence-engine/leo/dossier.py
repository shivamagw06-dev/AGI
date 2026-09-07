"""LEO dossier bridge — delegates to CID (permanent institutional memory).

Kept for backward compatibility with LEO v1.0 call sites.
"""

from __future__ import annotations

from typing import Any


def update_dossier(
    ticker: str | None,
    evidence_objects: list[dict[str, Any]],
    *,
    plan: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update the living Company Intelligence Dossier from LEO evidence."""
    try:
        from cid.ingest import ingest_leo_evidence

        return ingest_leo_evidence(
            ticker,
            evidence_objects,
            plan=plan,
            finance_academy=finance_academy,
            sif_pkg=sif_pkg,
        )
    except Exception:
        # Soft fallback — minimal in-process summary if CID unavailable
        if not ticker:
            return {"enabled": False, "reason": "no_ticker"}
        return {
            "ticker": (ticker or "").upper(),
            "coverage_score": 0.0,
            "updated_at": None,
            "annual_reports": [],
            "quarterly_results": [],
            "investor_presentations": [],
            "corporate_announcements": [],
            "financial_statements": [],
            "evidence_timeline": [],
        }


def get_dossier(ticker: str) -> dict[str, Any]:
    try:
        from cid.production import get_dossier as cid_get

        return cid_get(ticker)
    except Exception:
        return {}


def list_dossiers(limit: int = 50) -> list[dict[str, Any]]:
    try:
        from cid.store import get_cid_store

        return get_cid_store().summary_rows(limit=limit)
    except Exception:
        return []
