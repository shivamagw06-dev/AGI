"""Production façades for Nifty / NSE index constituents."""

from __future__ import annotations

import re
from typing import Any

from market_indices.loader import (
    INDEX_CATALOG,
    dashboard,
    get_index,
    health,
    list_indices,
    list_members,
    membership_for_symbol,
    search_index,
)

_MEMBERSHIP_Q = re.compile(
    r"\b("
    r"which\s+indices?|what\s+indices?|which\s+index|what\s+index|"
    r"comes?\s+under|belong(?:s|ing)?\s+to|part\s+of|member\s+of|"
    r"included\s+in|under\s+which\s+indices?"
    r")\b",
    re.I,
)
_CONSTITUENTS_Q = re.compile(
    r"\b("
    r"which\s+stocks?|what\s+stocks?|constituents?|members?|"
    r"stocks?\s+(?:in|under|of)|companies\s+(?:in|under|of)|"
    r"list\s+(?:the\s+)?(?:stocks?|constituents?|members?)"
    r")\b",
    re.I,
)


def _ticker_from_payload(payload: dict[str, Any] | None, question: str) -> str | None:
    body = payload or {}
    for key in ("ticker", "detected_ticker", "symbol"):
        v = body.get(key)
        if v:
            return str(v).upper().strip()
    ere = body.get("entity_resolution") or {}
    if isinstance(ere, dict):
        t = ere.get("ticker") or (ere.get("entity") or {}).get("ticker")
        if t:
            return str(t).upper().strip()
    # Soft: known alias hits in question via trading / market search
    q = (question or "").lower()
    for alias, meta in (
        ("hdfc bank", "HDFCBANK"),
        ("hdfcbank", "HDFCBANK"),
        ("idbi bank", "IDBI"),
        ("idbi", "IDBI"),
        ("reliance", "RELIANCE"),
        ("infosys", "INFY"),
        ("tcs", "TCS"),
        ("sbi", "SBIN"),
        ("icici bank", "ICICIBANK"),
    ):
        if re.search(rf"\b{re.escape(alias)}\b", q):
            return meta
    # Bare ticker token present in any index
    for tok in re.findall(r"\b[A-Z]{2,12}\b", (question or "").upper()):
        mem = membership_for_symbol(tok)
        if mem.get("count"):
            return tok
    return None


def _pretty_index(index_id: str) -> str:
    meta = INDEX_CATALOG.get(index_id) or {}
    return str(meta.get("display_name") or index_id.replace("_", " ").title())


def answer_membership(symbol: str) -> dict[str, Any]:
    mem = membership_for_symbol(symbol)
    indices = list(mem.get("indices") or [])
    names = [_pretty_index(i) for i in indices]
    if not names:
        text = (
            f"{symbol} is not in the currently loaded Nifty index books "
            f"(50 / Next 50 / 100 / 200 / 500 / Midcap Select / Bank / Financial Services)."
        )
    elif len(names) == 1:
        text = f"{symbol} is a constituent of {names[0]}."
    else:
        text = f"{symbol} is a constituent of: " + ", ".join(names) + "."
    return {
        "ok": True,
        "mode": "symbol_membership",
        "symbol": symbol,
        "indices": indices,
        "index_names": names,
        "count": len(indices),
        "direct_answer": text,
        "bullets": [f"• {n}" for n in names] or ["• No matching index membership in registry"],
        "answerable": True,
    }


def answer_constituents(index_id: str, *, limit: int = 40) -> dict[str, Any]:
    idx = get_index(index_id, include_members=True)
    if not idx:
        return {"ok": False, "answerable": False, "error": "unknown_index"}
    symbols = list(idx.get("symbols") or [])
    shown = symbols[: max(1, min(int(limit), 80))]
    more = len(symbols) - len(shown)
    text = (
        f"{idx['display_name']} has {len(symbols)} constituents. "
        f"Includes: {', '.join(shown)}"
        + (f" … and {more} more." if more > 0 else ".")
    )
    return {
        "ok": True,
        "mode": "index_constituents",
        "index_id": idx["index_id"],
        "display_name": idx["display_name"],
        "count": len(symbols),
        "symbols": symbols,
        "direct_answer": text,
        "bullets": [f"• {s}" for s in shown],
        "answerable": True,
    }


def soft_slice_for_ask_agi(question: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Answer index membership / constituent questions for Ask AGI."""
    q = str(question or "").strip()
    low = q.lower()
    idx = search_index(q) if q else None
    ticker = _ticker_from_payload(payload, q)

    answer: dict[str, Any] | None = None
    if q and _MEMBERSHIP_Q.search(low) and ticker:
        answer = answer_membership(ticker)
    elif q and _CONSTITUENTS_Q.search(low) and idx:
        answer = answer_constituents(idx["index_id"])
    elif q and idx and any(k in low for k in ("index", "nifty", "constituent", "member")):
        # "nifty bank stocks" / "tell me nifty bank index"
        if _CONSTITUENTS_Q.search(low) or "stock" in low or "compan" in low:
            answer = answer_constituents(idx["index_id"])

    # Also attach membership whenever we know the ticker (enrichment for company questions)
    membership = answer_membership(ticker) if ticker else None

    return {
        "market_indices": {
            "enabled": True,
            "version": health().get("version"),
            "matched_index": {
                "index_id": idx.get("index_id"),
                "display_name": idx.get("display_name"),
                "count": idx.get("count"),
            }
            if idx
            else None,
            "ticker": ticker,
            "membership": membership,
            "answer": answer,
            "answerable": bool(answer and answer.get("answerable")),
            "direct_answer": (answer or {}).get("direct_answer"),
            "bullets": (answer or {}).get("bullets") or [],
            "health": {"available_count": health().get("available_count")},
        }
    }


__all__ = [
    "answer_constituents",
    "answer_membership",
    "dashboard",
    "get_index",
    "health",
    "list_indices",
    "list_members",
    "membership_for_symbol",
    "search_index",
    "soft_slice_for_ask_agi",
]
