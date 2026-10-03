"""Company names in company_master that are really just the ticker.

1,179 of the 2,714 rows carry their own symbol in the company_name field --
3PLAND instead of "3P Land Holdings Limited", HNDFDS instead of "Hindustan
Foods Limited". Their real names are in NIFTYstocks.csv, which is already in
the repo and already read by trading_universe.

It happens because several writers fall back to the symbol when a source has
no name of its own:

    "company_name": master.get("company_name") or symbol

The daily bhavcopy is a price file. It carries symbols and no names, so every
symbol it saw first got a row named after itself, and the real name never
replaced it because a ticker is not falsy. 1,114 of the 1,179 came in that way,
64 more from the Upstox instrument list.

The cost is not cosmetic. Insider trades, bulk deals and disclosures all arrive
naming a company in words, and resolve to a ticker by matching that name. A row
named after its own ticker cannot be matched by anything, so those trades keep
a blank symbol and drop out of anything that joins on one.
"""

from __future__ import annotations

import re
from typing import Any, Optional

SOURCE = "trading_universe"
_PUNCT = re.compile(r"[^a-z0-9]")


def _key(value: Any) -> str:
    return _PUNCT.sub("", str(value or "").lower())


def _universe_names() -> dict[str, str]:
    """Symbol to the name the exchange file gives it."""
    try:
        from trading_universe.loader import load_rows
    except Exception:
        return {}
    names: dict[str, str] = {}
    for row in load_rows() or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        name = str(row.get("name") or "").strip()
        # The loader has the same `or symbol` fallback, so a row can arrive
        # here already carrying its ticker as its name. Not a real name.
        if symbol and name and _key(name) != _key(symbol):
            names[symbol] = name
    return names


def real_name(symbol: str) -> Optional[str]:
    """The company's name, or None. Never the ticker.

    Returning None is the point: a caller that writes `real_name(s) or s` has
    reintroduced the bug, and one that writes `real_name(s)` leaves the field
    empty, which is honest and still fixable later.
    """
    return _universe_names().get(str(symbol or "").strip().upper())


def audit() -> dict[str, Any]:
    """How many master rows are named after themselves, and how many can be fixed."""
    from institutional_warehouse import store

    try:
        masters = store.all_rows("company_master", limit=20000) or []
    except Exception as exc:
        return {"ok": False, "error": f"unreadable:{exc}"[:160]}

    names = _universe_names()
    repairable, unnamed_elsewhere, fine = [], [], 0
    for row in masters:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        if _key(row.get("company_name")) != _key(symbol):
            fine += 1
            continue
        # Some names really are close to the ticker -- "BLB Limited" for BLB.
        # Those are correct and must not be counted as damage or rewritten.
        if symbol in names:
            repairable.append({"symbol": symbol, "was": row.get("company_name"),
                               "becomes": names[symbol], "source": row.get("source")})
        else:
            unnamed_elsewhere.append(symbol)
    return {
        "ok": True,
        "masters": len(masters),
        "named": fine,
        "ticker_as_name": len(repairable) + len(unnamed_elsewhere),
        "repairable": len(repairable),
        "no_name_available": len(unnamed_elsewhere),
        "universe_names": len(names),
        "sample": repairable[:10],
    }


def repair(*, dry_run: bool = True, actor: str = "company_names") -> dict[str, Any]:
    """Put the real name back where a row is named after its own ticker.

    Only touches rows whose company_name is the symbol. A row with any other
    name is left alone even if the universe file disagrees with it -- this
    repairs a known defect, it does not arbitrate between two real names.
    """
    from institutional_warehouse import gateway, store

    found = audit()
    if not found.get("ok"):
        return found

    try:
        masters = store.all_rows("company_master", limit=20000) or []
    except Exception as exc:
        return {"ok": False, "error": f"unreadable:{exc}"[:160]}

    names = _universe_names()
    updates = []
    for row in masters:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol or _key(row.get("company_name")) != _key(symbol):
            continue
        name = names.get(symbol)
        if not name:
            continue
        updates.append({
            "company_id": row.get("company_id") or symbol,
            "symbol": symbol,
            "company_name": name,
            "isin": row.get("isin"),
            "exchange": row.get("exchange") or "NSE",
        })

    if dry_run or not updates:
        return {**found, "dry_run": True, "would_write": len(updates), "written": 0}

    written = updated = quarantined = 0
    for start in range(0, len(updates), 250):
        result = gateway.write("company_master", updates[start:start + 250],
                               source=SOURCE, actor=actor,
                               reason="company_name_repair", detect_conflicts=False)
        written += int(result.get("written") or 0)
        updated += int(result.get("updated") or 0)
        quarantined += int(result.get("quarantined") or 0)
    return {**found, "dry_run": False, "would_write": len(updates),
            "written": written, "updated": updated, "quarantined": quarantined,
            "ok": quarantined == 0}
