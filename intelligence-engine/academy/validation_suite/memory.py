"""Level 7 institutional memory — prior company reviews for change detection."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from academy.validation_suite.company_evidence import evidence_for


_LOCK = Lock()
_REVIEWS: dict[str, list[dict[str, Any]]] = {}


def _key(company: str | None, ticker: str | None) -> str:
    return (ticker or company or "UNKNOWN").upper().replace(" ", "")


def seed_prior_review(company: str | None = None, ticker: str | None = None) -> dict[str, Any]:
    """Ensure a prior review exists so Level 7 can test memory, not one-off reasoning."""
    ev = evidence_for(company=company, ticker=ticker)
    mem = ev.get("memory_seed") or {}
    key = _key(company, ticker)
    review = {
        "company": ev.get("name") or company,
        "ticker": ticker,
        "reviewed_at": "2025-01-15T00:00:00+00:00",
        "opinion": mem.get("previous_opinion") or "Initial franchise quality constructive",
        "metrics": {
            "loan_growth": "solid",
            "deposit_mix": "strong CASA advantage",
            "nim": "healthy franchise NIM",
            "capital": "comfortable",
        },
        "themes": ["funding_advantage", "franchise_quality"],
    }
    with _LOCK:
        if key not in _REVIEWS or not _REVIEWS[key]:
            _REVIEWS[key] = [review]
        return deepcopy(_REVIEWS[key][0])


def latest_review(company: str | None = None, ticker: str | None = None) -> dict[str, Any] | None:
    key = _key(company, ticker)
    with _LOCK:
        rows = _REVIEWS.get(key) or []
        return deepcopy(rows[-1]) if rows else None


def record_review(
    *,
    company: str | None,
    ticker: str | None,
    opinion: str,
    metrics: dict[str, Any] | None = None,
    themes: list[str] | None = None,
) -> dict[str, Any]:
    key = _key(company, ticker)
    row = {
        "company": company,
        "ticker": ticker,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "opinion": opinion,
        "metrics": metrics or {},
        "themes": themes or [],
    }
    with _LOCK:
        _REVIEWS.setdefault(key, []).append(row)
        return deepcopy(row)


def memory_delta(company: str | None = None, ticker: str | None = None) -> dict[str, Any]:
    """Compare seeded prior review to current evidence snapshot."""
    prior = seed_prior_review(company=company, ticker=ticker)
    ev = evidence_for(company=company, ticker=ticker)
    mem = ev.get("memory_seed") or {}
    fin = ev.get("financial") or {}
    updated = {
        "company": ev.get("name") or company,
        "ticker": ticker,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "opinion": mem.get("updated_opinion") or "Updated institutional view pending evidence refresh",
        "metrics": {
            "loan_growth": fin.get("loan_growth") or "n/a",
            "deposit_mix": fin.get("deposit_mix") or "n/a",
            "nim": fin.get("nim") or "n/a",
            "capital": fin.get("capital") or "n/a",
        },
        "changed": mem.get("changed") or [],
        "previous_opinion": prior.get("opinion"),
        "updated_opinion": mem.get("updated_opinion"),
    }
    record_review(
        company=company,
        ticker=ticker,
        opinion=str(updated["opinion"]),
        metrics=updated["metrics"],
        themes=["memory_update"],
    )
    return {
        "prior": prior,
        "current": updated,
        "changed_fields": updated["changed"],
    }


def reset_memory() -> None:
    with _LOCK:
        _REVIEWS.clear()
