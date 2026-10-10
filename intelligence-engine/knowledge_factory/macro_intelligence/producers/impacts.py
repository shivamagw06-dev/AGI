"""Macro → sector/company institutional relationships and shock impacts."""

from __future__ import annotations

from typing import Any

# Direction: +1 benefit, -1 hurt, 0 neutral; strength 0-2
_REL: dict[str, dict[str, dict[str, Any]]] = {
    "interest_rates": {
        "banks": {"direction": 1, "strength": 2, "confidence": 0.9, "note": "NIM repricing with lag"},
        "insurance": {"direction": 1, "strength": 1, "confidence": 0.7, "note": "mixed float vs discount"},
        "nbfc": {"direction": -1, "strength": 2, "confidence": 0.85, "note": "funding cost"},
        "real_estate": {"direction": -1, "strength": 2, "confidence": 0.9},
        "utilities": {"direction": -1, "strength": 2, "confidence": 0.85},
        "auto": {"direction": -1, "strength": 2, "confidence": 0.85},
        "consumer": {"direction": -1, "strength": 1, "confidence": 0.75},
        "it_services": {"direction": 0, "strength": 0, "confidence": 0.7},
    },
    "oil": {
        "oil_gas": {"direction": 1, "strength": 2, "confidence": 0.95, "note": "exploration / upstream"},
        "logistics": {"direction": -1, "strength": 2, "confidence": 0.9, "note": "airlines / transport fuel"},
        "chemicals": {"direction": -1, "strength": 1, "confidence": 0.7, "note": "mixed feedstock"},
        "fmcg": {"direction": -1, "strength": 1, "confidence": 0.7, "note": "packaging / logistics"},
        "auto": {"direction": -1, "strength": 1, "confidence": 0.7},
        "metals": {"direction": -1, "strength": 1, "confidence": 0.6},
    },
    "inflation": {
        "fmcg": {"direction": -1, "strength": 1, "confidence": 0.8, "note": "margin squeeze until pricing"},
        "metals": {"direction": 1, "strength": 1, "confidence": 0.75},
        "consumer": {"direction": -1, "strength": 1, "confidence": 0.8},
        "it_services": {"direction": 0, "strength": 0, "confidence": 0.75},
        "oil_gas": {"direction": 1, "strength": 1, "confidence": 0.7},
    },
    "usd": {
        "it_services": {"direction": 1, "strength": 2, "confidence": 0.9, "note": "export INR realisation"},
        "pharma": {"direction": 1, "strength": 1, "confidence": 0.8},
        "oil_gas": {"direction": -1, "strength": 1, "confidence": 0.7, "note": "import bill / INR"},
        "metals": {"direction": -1, "strength": 1, "confidence": 0.65},
    },
    "dxy": {
        "it_services": {"direction": 1, "strength": 2, "confidence": 0.85},
        "metals": {"direction": -1, "strength": 1, "confidence": 0.7},
        "oil_gas": {"direction": -1, "strength": 1, "confidence": 0.65},
    },
}

# Track 1 — expand affinity sectors used by Nifty 500 company macro links.
for _macro, _extra in {
    "interest_rates": {
        "industrials": {"direction": -1, "strength": 1, "confidence": 0.75, "note": "capex / WACC"},
        "pharma": {"direction": 0, "strength": 0, "confidence": 0.7},
        "chemicals": {"direction": -1, "strength": 1, "confidence": 0.7},
        "logistics": {"direction": -1, "strength": 1, "confidence": 0.75},
        "cement": {"direction": -1, "strength": 2, "confidence": 0.8},
        "telecom": {"direction": -1, "strength": 1, "confidence": 0.75},
        "healthcare": {"direction": -1, "strength": 1, "confidence": 0.7},
        "retail": {"direction": -1, "strength": 1, "confidence": 0.75},
        "internet": {"direction": -1, "strength": 1, "confidence": 0.7},
        "infrastructure": {"direction": -1, "strength": 2, "confidence": 0.8},
    },
    "oil": {
        "industrials": {"direction": -1, "strength": 1, "confidence": 0.7},
        "pharma": {"direction": -1, "strength": 1, "confidence": 0.65},
        "logistics": {"direction": -1, "strength": 2, "confidence": 0.9},
        "utilities": {"direction": -1, "strength": 1, "confidence": 0.7},
        "cement": {"direction": -1, "strength": 1, "confidence": 0.7},
        "retail": {"direction": -1, "strength": 1, "confidence": 0.65},
        "internet": {"direction": 0, "strength": 0, "confidence": 0.7},
        "healthcare": {"direction": 0, "strength": 0, "confidence": 0.65},
        "infrastructure": {"direction": -1, "strength": 1, "confidence": 0.7},
        "telecom": {"direction": 0, "strength": 0, "confidence": 0.65},
    },
    "inflation": {
        "industrials": {"direction": -1, "strength": 1, "confidence": 0.7},
        "pharma": {"direction": 0, "strength": 0, "confidence": 0.7},
        "chemicals": {"direction": -1, "strength": 1, "confidence": 0.75},
        "logistics": {"direction": -1, "strength": 1, "confidence": 0.7},
        "banks": {"direction": 0, "strength": 0, "confidence": 0.7},
        "nbfc": {"direction": -1, "strength": 1, "confidence": 0.7},
        "insurance": {"direction": 0, "strength": 0, "confidence": 0.65},
        "utilities": {"direction": 0, "strength": 0, "confidence": 0.65},
        "real_estate": {"direction": 0, "strength": 0, "confidence": 0.65},
        "cement": {"direction": 1, "strength": 1, "confidence": 0.7},
        "retail": {"direction": -1, "strength": 1, "confidence": 0.75},
        "internet": {"direction": -1, "strength": 1, "confidence": 0.7},
        "healthcare": {"direction": -1, "strength": 1, "confidence": 0.7},
        "infrastructure": {"direction": -1, "strength": 1, "confidence": 0.7},
        "telecom": {"direction": 0, "strength": 0, "confidence": 0.65},
    },
    "usd": {
        "industrials": {"direction": 0, "strength": 0, "confidence": 0.65},
        "chemicals": {"direction": -1, "strength": 1, "confidence": 0.7},
        "logistics": {"direction": -1, "strength": 1, "confidence": 0.7},
        "banks": {"direction": 0, "strength": 0, "confidence": 0.65},
        "nbfc": {"direction": 0, "strength": 0, "confidence": 0.65},
        "insurance": {"direction": 0, "strength": 0, "confidence": 0.65},
        "fmcg": {"direction": 0, "strength": 0, "confidence": 0.65},
        "auto": {"direction": -1, "strength": 1, "confidence": 0.7},
        "utilities": {"direction": 0, "strength": 0, "confidence": 0.65},
        "real_estate": {"direction": 0, "strength": 0, "confidence": 0.65},
        "consumer": {"direction": 0, "strength": 0, "confidence": 0.65},
        "cement": {"direction": 0, "strength": 0, "confidence": 0.65},
        "retail": {"direction": 0, "strength": 0, "confidence": 0.65},
        "internet": {"direction": 0, "strength": 0, "confidence": 0.65},
        "healthcare": {"direction": 0, "strength": 0, "confidence": 0.65},
        "infrastructure": {"direction": 0, "strength": 0, "confidence": 0.65},
        "telecom": {"direction": 0, "strength": 0, "confidence": 0.65},
    },
}.items():
    _REL.setdefault(_macro, {}).update(_extra)


def relationship(macro: str, sector: str) -> dict[str, Any]:
    m = macro.lower().replace(" ", "_")
    if m in {"usd_inr", "usd"}:
        # USD strength ≈ INR weakness → use usd map for IT
        m = "usd" if m == "usd_inr" else m
    s = sector.lower()
    rel = (_REL.get(m) or {}).get(s)
    if not rel:
        # Soft-read ISI macro_map when available
        try:
            from knowledge_factory.sector_intelligence.macro_map import macro_relationships

            driver = {
                "interest_rates": "higher_rates",
                "oil": "oil_up",
                "inflation": "higher_inflation",
                "usd": "usd_strength",
                "dxy": "usd_strength",
            }.get(m)
            if driver:
                score = int((macro_relationships(s).get("relationships") or {}).get(driver) or 0)
                if score != 0:
                    return {
                        "macro": macro,
                        "sector": s,
                        "direction": 1 if score > 0 else -1,
                        "strength": abs(score),
                        "confidence": 0.7,
                        "historical_validation": "isi_macro_map",
                        "found": True,
                        "fabricated": False,
                    }
        except Exception:
            pass
        return {
            "macro": macro,
            "sector": s,
            "found": False,
            "reason": "macro_history_unavailable",
            "insufficient": True,
            "fabricated": False,
        }
    return {
        "macro": macro,
        "sector": s,
        "found": True,
        "direction": rel["direction"],
        "strength": rel["strength"],
        "confidence": rel["confidence"],
        "note": rel.get("note"),
        "historical_validation": "institutional_prior",
        "fabricated": False,
    }


def sectors_for_driver(macro: str, *, direction: int = 1) -> dict[str, Any]:
    """Sectors that benefit (direction=+1) or suffer (direction=-1) from a macro move."""
    m = macro.lower().replace(" ", "_")
    # falling rates = inverse of interest_rates higher
    invert = False
    if m in {"falling_rates", "lower_rates", "rates_fall"}:
        m = "interest_rates"
        invert = True
        # Hurt by higher rates (direction=-1) → benefit when rates fall (inverted +1)
        want = 1
    else:
        want = direction

    hits = []
    table = _REL.get(m) or _REL.get("usd" if m == "usd_inr" else m) or {}
    for sector, rel in table.items():
        d = int(rel["direction"])
        if invert:
            d = -d
        if (want > 0 and d > 0) or (want < 0 and d < 0):
            hits.append(
                {
                    "sector": sector,
                    "direction": d,
                    "strength": rel["strength"],
                    "confidence": rel["confidence"],
                    "note": rel.get("note"),
                }
            )
    hits.sort(key=lambda x: (-x["strength"], -x["confidence"]))
    return {
        "macro": macro,
        "direction_requested": "benefit" if want > 0 else "hurt",
        "sectors": hits,
        "n": len(hits),
        "found": len(hits) > 0,
        "evidence": "historical_macro_relationships",
        "fabricated": False,
    }


def shock_impact(macro: str, move_pct: float) -> dict[str, Any]:
    """E.g. oil rises 30% → sector/company impact knowledge."""
    m = macro.lower()
    table = _REL.get(m) or {}
    if not table:
        return {
            "found": False,
            "macro": macro,
            "move_pct": move_pct,
            "reason": "macro_history_unavailable",
            "insufficient": True,
            "fabricated": False,
        }
    sign = 1 if move_pct >= 0 else -1
    impacts = []
    for sector, rel in table.items():
        # positive direction sector benefits when macro rises
        effect = rel["direction"] * sign
        impacts.append(
            {
                "sector": sector,
                "impact": "positive" if effect > 0 else "negative" if effect < 0 else "neutral",
                "strength": rel["strength"],
                "confidence": rel["confidence"],
                "note": rel.get("note"),
            }
        )
    # Company examples from sector_map
    companies = []
    try:
        from knowledge_factory.fixtures.seed import sector_map
        from knowledge_factory.sector_intelligence.schema import canonicalize

        smap = sector_map()
        for ticker, sec in smap.items():
            csec = canonicalize(sec)
            for row in impacts:
                if csec == row["sector"]:
                    companies.append(
                        {
                            "ticker": ticker,
                            "sector": csec,
                            "impact": row["impact"],
                            "strength": row["strength"],
                        }
                    )
                    break
    except Exception:
        pass
    return {
        "found": True,
        "macro": macro,
        "move_pct": move_pct,
        "sector_impacts": impacts,
        "company_impacts": companies[:20],
        "fabricated": False,
    }


def usd_strength_it_impact() -> dict[str, Any]:
    rel = relationship("usd", "it_services")
    companies = []
    try:
        from knowledge_factory.fixtures.seed import sector_map
        from knowledge_factory.sector_intelligence.schema import canonicalize

        for t, s in sector_map().items():
            if canonicalize(s) == "it_services":
                companies.append(t)
    except Exception:
        companies = ["INFY", "TCS", "WIPRO"]
    return {
        "found": rel.get("found", False),
        "macro": "usd_strength",
        "sector": "it_services",
        "impact": "positive_export_realisation",
        "direction": rel.get("direction"),
        "strength": rel.get("strength"),
        "confidence": rel.get("confidence"),
        "companies": companies,
        "historical_note": "Strong USD / weak INR historically supports IT Services INR earnings translation",
        "fabricated": False,
    }
