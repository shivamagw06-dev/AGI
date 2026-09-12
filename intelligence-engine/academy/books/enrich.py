"""Soft CID enrichment — relevant Academy book concepts/frameworks/formulas."""

from __future__ import annotations

from typing import Any

from academy.books.flags import is_books_enabled
from academy.books.ingest import ensure_seeded
from academy.books.store import get_books_store


# Sector / ticker soft maps for Nestlé-class enrichment
_TICKER_HINTS: dict[str, tuple[str, ...]] = {
    "NESTLEIND": (
        "fmcg",
        "staples",
        "brand",
        "pricing",
        "working capital",
        "cash conversion",
        "roic",
        "moat",
        "premium",
        "valuation",
    ),
    "INFY": ("it services", "utilisation", "deal", "offshore"),
    "TCS": ("it services", "utilisation", "deal"),
    "HDFCBANK": ("bank", "nim", "casa", "roe"),
    "ASIANPAINT": ("fmcg", "brand", "pricing", "moat"),
}

_SECTOR_HINTS: dict[str, tuple[str, ...]] = {
    "fmcg": ("brand", "pricing", "working capital", "staples", "moat", "roic"),
    "consumer_staples": ("brand", "pricing", "working capital", "staples", "moat"),
    "banking": ("nim", "roe", "casa", "credit"),
    "it_services": ("utilisation", "deal", "pricing"),
}


def enrich_dossier(dossier: dict[str, Any], *, ticker: str | None = None) -> dict[str, Any]:
    """Fill-empties Academy learning block on a CID dossier."""
    if not is_books_enabled() or not isinstance(dossier, dict):
        return dossier
    ensure_seeded()
    store = get_books_store()
    t = (ticker or dossier.get("ticker") or (dossier.get("identity") or {}).get("ticker") or "").upper()
    sector = str(
        (dossier.get("identity") or {}).get("sector_id")
        or (dossier.get("identity") or {}).get("sector")
        or ""
    ).lower()

    hints = list(_TICKER_HINTS.get(t, ()))
    for sk, vals in _SECTOR_HINTS.items():
        if sk in sector:
            hints.extend(vals)
    if not hints:
        hints = ("roic", "moat", "valuation", "capital allocation")

    concepts = []
    for c in store.concepts.values():
        blob = f"{c.title} {c.definition} {c.academy} {' '.join(c.linked_companies)}".lower()
        if t and t in " ".join(c.linked_companies).upper():
            score = 3
        else:
            score = sum(1 for h in hints if h in blob)
        if score <= 0:
            continue
        concepts.append((score, c))
        store.touch(c.concept_id)
    concepts.sort(key=lambda x: (-x[0], -x[1].confidence))
    top = [c for _, c in concepts[:12]]

    fw = []
    for f in store.frameworks.values():
        blob = f"{f.name} {f.purpose} {f.academy}".lower()
        if any(h in blob for h in hints) or (t == "NESTLEIND" and "staples" in blob):
            fw.append(f)
    formulas = []
    for f in store.formulas.values():
        blob = f"{f.name} {f.explanation}".lower()
        if any(h in blob for h in ("roic", "wacc", "fcf", "roe", "dcf", "intrinsic")):
            formulas.append(f)

    fa = dossier.setdefault("finance_academy", {})
    # Fill empties only
    if not fa.get("book_concepts"):
        fa["book_concepts"] = [
            {
                "concept_id": c.concept_id,
                "title": c.title,
                "academy": c.academy,
                "definition": c.definition,
                "source_book_id": c.source_book_id,
                "source_chapter": c.source_chapter,
            }
            for c in top
        ]
    if not fa.get("frameworks"):
        fa["frameworks"] = [
            {"framework_id": f.framework_id, "name": f.name, "purpose": f.purpose, "academy": f.academy}
            for f in fw[:8]
        ]
    if not fa.get("formulas"):
        fa["formulas"] = [
            {"formula_id": f.formula_id, "name": f.name, "expression": f.expression, "academy": f.academy}
            for f in formulas[:8]
        ]
    if not fa.get("sector_learning") and top:
        fa["sector_learning"] = sorted({c.academy for c in top if c.academy.startswith("sector_") or c.academy in {"investment", "valuation", "accounting"}})[:8]
    if not fa.get("valuation_learning"):
        fa["valuation_learning"] = [c.title for c in top if c.academy in {"valuation", "investment"}][:8]
    if not fa.get("accounting_learning"):
        fa["accounting_learning"] = [c.title for c in top if c.academy == "accounting"][:8]

    # Keep active_concepts union
    active = list(fa.get("active_concepts") or [])
    for c in top:
        if c.concept_id not in active:
            active.append(c.concept_id)
    fa["active_concepts"] = active[:24]
    return dossier
