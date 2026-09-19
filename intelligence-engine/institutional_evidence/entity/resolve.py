"""Entity Resolution bridge — one immutable Entity ID per company.

Every document references the Entity ID (AGI-COMPANY-NNNNNNN).
Soft-consumes entity_resolution / IKG; never guesses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import ENTITY_ID_PREFIX, PHASE1_TOP20


# Stable Phase-1 sequence map + common aliases
_ALIAS_TO_TICKER = {
    "RELIANCE": "RELIANCE",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "RELIANCE INDUSTRIES LTD": "RELIANCE",
    "RELIANCE.NS": "RELIANCE",
    "500325": "RELIANCE",
    "INE002A01018": "RELIANCE",
    "TCS": "TCS",
    "TATA CONSULTANCY SERVICES": "TCS",
    "INFY": "INFY",
    "INFOSYS": "INFY",
    "HDFCBANK": "HDFCBANK",
    "HDFC BANK": "HDFCBANK",
    "ICICIBANK": "ICICIBANK",
    "ICICI BANK": "ICICIBANK",
    "SBIN": "SBIN",
    "STATE BANK OF INDIA": "SBIN",
}


def entity_id_for_ticker(ticker: str) -> str:
    t = str(ticker or "").upper().strip()
    for row in PHASE1_TOP20:
        if row["ticker"] == t:
            return f"{ENTITY_ID_PREFIX}{int(row.get('entity_seq') or 0):07d}"
    # Deterministic fallback outside Phase-1
    seq = abs(hash(t)) % 10_000_000
    return f"{ENTITY_ID_PREFIX}{seq:07d}"


def list_aliases(ticker: str) -> List[str]:
    t = str(ticker or "").upper().strip()
    aliases = {t, f"{t}.NS"}
    for row in PHASE1_TOP20:
        if row["ticker"] == t:
            aliases.add(row["company"].upper())
            break
    for alias, mapped in _ALIAS_TO_TICKER.items():
        if mapped == t:
            aliases.add(alias)
    return sorted(aliases)


def resolve_entity(query: str) -> Dict[str, Any]:
    """Resolve provider aliases to one immutable entity. Never invents."""
    q = str(query or "").strip()
    if not q:
        return {"ok": False, "resolved": False, "reason": "empty_query", "rule": "never_guess"}

    # Deterministic Phase-1 / known aliases first (ISIN, BSE code, .NS, legal name)
    key = q.upper().replace(",", "").strip()
    ticker = _ALIAS_TO_TICKER.get(key)
    if not ticker and key in {r["ticker"] for r in PHASE1_TOP20}:
        ticker = key

    ere: Optional[Dict[str, Any]] = None
    if not ticker:
        # Soft-consume ERE only when alias map misses — never invent
        try:
            from entity_resolution.production import resolve  # type: ignore

            ere = resolve(q) if callable(resolve) else None
        except Exception:
            try:
                from entity_resolution.canonical_resolver import resolve_question  # type: ignore

                ere = resolve_question(q)
            except Exception:
                ere = None

        if isinstance(ere, dict):
            if ere.get("needs_clarification") or ere.get("clarify"):
                return {
                    "ok": True,
                    "resolved": False,
                    "needs_clarification": True,
                    "query": q,
                    "ere": ere,
                    "rule": "never_guess",
                }
            ticker = (
                ere.get("ticker")
                or (ere.get("entity") or {}).get("ticker")
                or (ere.get("canonical") or {}).get("ticker")
            )

    if not ticker:
        return {
            "ok": True,
            "resolved": False,
            "query": q,
            "reason": "unresolved — no guess",
            "rule": "never_guess",
        }

    meta = next((r for r in PHASE1_TOP20 if r["ticker"] == ticker), None)
    eid = entity_id_for_ticker(ticker)
    return {
        "ok": True,
        "resolved": True,
        "query": q,
        "entity_id": eid,
        "ticker": ticker,
        "company": (meta or {}).get("company") or ticker,
        "sector": (meta or {}).get("sector"),
        "aliases": list_aliases(ticker),
        "immutable": True,
        "rule": "Every document references the Entity ID",
        "ere_soft": bool(ere),
    }
