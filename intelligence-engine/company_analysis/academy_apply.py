"""Step 2 — Apply Academy concepts to THIS company (not bare concept lists)."""

from __future__ import annotations

from typing import Any

from company_analysis.schema import SECTOR_CONCEPT_LENSES


def _sector_key(identity: dict[str, Any]) -> str:
    sid = str(identity.get("sector_id") or identity.get("sector") or "").lower()
    for key in SECTOR_CONCEPT_LENSES:
        if key in sid:
            return key
    # fuzzy
    if "bank" in sid:
        return "banks"
    if "fmcg" in sid or "staple" in sid or "consumer" in sid:
        return "fmcg"
    if "it" in sid or "software" in sid:
        return "it_services"
    return sid or "general"


def _application_text(concept_title: str, sector_key: str, ticker: str) -> str:
    title = (concept_title or "").strip()
    low = title.lower()
    t = ticker or "this company"

    if sector_key in {"banks", "banking"}:
        if "roe" in low:
            return (
                f"For {t}, ROE must be read with capital adequacy, CASA, credit cost, "
                "provision coverage, loan growth and leverage — these determine whether returns are sustainable "
                "or leverage-/cycle-driven."
            )
        if "nim" in low or "net interest" in low:
            return (
                f"For {t}, NIM should be interpreted beside liability mix (CASA), loan yields, "
                "and the rate cycle — margin alone does not prove franchise quality."
            )
        if "casa" in low:
            return (
                f"For {t}, CASA is a deposit-franchise quality signal; pair with deposit growth, "
                "cost of funds and loan-deposit dynamics."
            )
        if "moat" in low or "advantage" in low:
            return (
                f"For {t}, economic moat shows up as low-cost sticky deposits, distribution, "
                "underwriting discipline and operating scale — not just brand language."
            )
        if "margin of safety" in low:
            return (
                f"For {t}, margin of safety is price vs sustainable earning power and book/capital — "
                "after credit-cost normalisation, not peak ROE."
            )
        return (
            f"Apply {title} to {t} using banking evidence: capital, asset quality, funding mix, "
            "growth and returns — not as a standalone label."
        )

    if sector_key in {"fmcg", "consumer_staples"}:
        if "roe" in low:
            return (
                f"For {t}, ROE should be analysed with brand power, pricing power, working capital, "
                "cash conversion and ROIC — premium FMCG creates value differently from banks."
            )
        if "roic" in low:
            return (
                f"For {t}, ROIC is the core operating return metric; read with reinvestment needs, "
                "working-capital intensity and pricing power."
            )
        if "brand" in low or "pricing" in low:
            return (
                f"For {t}, brand/pricing power must show up in volume/value growth, margins and "
                "resilience through inflation cycles — not marketing spend alone."
            )
        if "working capital" in low or "cash conversion" in low:
            return (
                f"For {t}, working capital and cash conversion validate earnings quality for a "
                "staples franchise — accruals without cash are a red flag."
            )
        if "moat" in low:
            return (
                f"For {t}, moat is distribution depth + brand trust + pricing power converting into "
                "durable ROIC above WACC."
            )
        return (
            f"Apply {title} to {t} with FMCG evidence: volume, pricing, brand, distribution, ROIC "
            "and cash conversion."
        )

    if sector_key == "it_services":
        if "utilisation" in low or "margin" in low:
            return (
                f"For {t}, utilisation and margins must be read with deal wins, attrition, pricing "
                "and large-deal ramp — not headcount growth alone."
            )
        return f"Apply {title} to {t} with IT-services evidence: utilisation, deals, pricing, attrition and mix."

    if "margin of safety" in low:
        return (
            f"For {t}, margin of safety compares market price to intrinsic value after adjusting for "
            "business quality and cyclicality — never a generic multiple discount."
        )
    if "moat" in low:
        return (
            f"For {t}, economic moat must be evidenced by durable returns, customer stickiness or "
            "cost advantages — not a label."
        )
    return f"Interpret {title} specifically for {t} using sector economics, financial history and live evidence — not as an isolated concept."


def apply_academy(
    *,
    identity: dict[str, Any],
    finance_academy: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t = identity.get("ticker") or ""
    sector_key = _sector_key(identity)
    lenses = list(SECTOR_CONCEPT_LENSES.get(sector_key, ("roic", "moat", "valuation", "capital allocation")))

    raw_concepts: list[dict[str, Any]] = []
    fa = finance_academy or {}
    for key in ("concepts", "book_concepts", "applied_concepts"):
        block = fa.get(key)
        if isinstance(block, list):
            raw_concepts.extend([c for c in block if isinstance(c, dict)])
    fa_cid = ((cid or {}).get("finance_academy") or {}) if isinstance(cid, dict) else {}
    for key in ("book_concepts", "concepts"):
        block = fa_cid.get(key)
        if isinstance(block, list):
            raw_concepts.extend([c for c in block if isinstance(c, dict)])

    # Soft-pull from Academy Books store when empty
    if not raw_concepts:
        try:
            from academy.books.production import package_for_query

            pkg = package_for_query(
                f"company analysis {t} {sector_key}",
                ticker=t or None,
                limit=12,
            ) or {}
            raw_concepts.extend(list(pkg.get("concepts") or [])[:12])
            fa = {**fa, **{k: pkg.get(k) for k in ("frameworks", "formulas", "answer_hints") if pkg.get(k)}}
        except Exception:
            pass

    applied: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in raw_concepts:
        title = c.get("title") or c.get("name") or c.get("concept_id") or ""
        cid_key = str(c.get("concept_id") or title).lower()
        if not title or cid_key in seen:
            continue
        seen.add(cid_key)
        blob = f"{title} {c.get('definition') or ''} {c.get('academy') or ''}".lower()
        relevance = sum(1 for lens in lenses if lens in blob)
        if t and t.lower() in blob:
            relevance += 2
        if relevance <= 0 and len(applied) >= 6:
            continue
        applied.append(
            {
                "concept_id": c.get("concept_id"),
                "title": title,
                "academy": c.get("academy"),
                "definition": c.get("definition"),
                "application": _application_text(title, sector_key, t),
                "relevance": relevance,
                "source_book_id": c.get("source_book_id"),
                "source": "academy",
            }
        )
    applied.sort(key=lambda x: (-int(x.get("relevance") or 0), str(x.get("title") or "")))
    applied = applied[:12]

    # Ensure sector-critical applications exist even if store sparse
    critical = {
        "banks": ["ROE", "NIM", "CASA", "Margin of Safety", "Economic Moat"],
        "banking": ["ROE", "NIM", "CASA", "Margin of Safety"],
        "fmcg": ["ROE", "ROIC", "Brand Power", "Pricing Power", "Working Capital", "Cash Conversion"],
        "consumer_staples": ["ROE", "ROIC", "Brand Power", "Pricing Power"],
        "it_services": ["Utilisation", "Economic Moat", "Margin of Safety"],
    }.get(sector_key, ["Economic Moat", "Margin of Safety", "ROIC"])
    have = {str(a.get("title") or "").lower() for a in applied}
    for title in critical:
        if title.lower() in have:
            continue
        applied.append(
            {
                "concept_id": f"applied_{title.lower().replace(' ', '_')}",
                "title": title,
                "academy": sector_key,
                "definition": None,
                "application": _application_text(title, sector_key, t),
                "relevance": 1,
                "source": "sector_lens",
            }
        )

    frameworks = list(fa.get("frameworks") or fa_cid.get("frameworks") or [])[:8]
    formulas = list(fa.get("formulas") or fa_cid.get("formulas") or [])[:8]

    return {
        "sector_key": sector_key,
        "lenses": lenses,
        "applied_concepts": applied[:14],
        "frameworks": frameworks,
        "formulas": formulas,
        "policy": "apply_concepts_to_company_not_retrieve_labels",
        "sources": ["academy", "academy.books", "cid.finance_academy", "sector_lens"],
    }
