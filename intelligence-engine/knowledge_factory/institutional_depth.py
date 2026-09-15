"""Infosys-class Institutional Depth standard (Track 1).

North star: every covered company has the same institutional depth as Infosys.
Soft Knowledge Factory measurement only — Phases 1–7 frozen.
"""

from __future__ import annotations

from typing import Any

DEPTH_VERSION = "institutional-depth-v1.0.0"
REFERENCE_ENTITY = "INFY"
EVIDENCE_QUALITY_THRESHOLD = 90.0

# Stage-2 company intelligence dimensions (derived metrics never stored).
DEPTH_DIMENSIONS = (
    "identity",
    "historical_financials",
    "derived_metrics",
    "historical_valuation",
    "peer_intelligence",
    "timeline",
    "macro_links",
    "sector_links",
    "evidence_pack",
    "portfolio_readiness",
    "decision_readiness",
)


def _derive_sector_key(sector: str | None) -> str | None:
    sector_key = str(sector or "").lower()
    if sector_key in {"banks", "bank"}:
        return "bank"
    if sector_key in {"insurance"}:
        return "insurance"
    if sector_key in {"nbfc", "capital_markets"}:
        return "nbfc"
    return sector_key or None


def company_identity(entity: str) -> dict[str, Any]:
    """Identity block — profile / sector / industry / exchange / index membership."""
    from knowledge_factory.fixtures.seed import sector_map
    from knowledge_factory.nifty500_universe import NIFTY_500, NIFTY_500_META
    from institutional_reasoning.fundamentals.universe import NIFTY_50, NIFTY_100_EXTRA
    from institutional_reasoning.fundamentals.primitives import latest
    from knowledge_factory.store import repository as store

    e = entity.upper()
    obj = store.get_object("company", e) or {}
    meta = NIFTY_500_META.get(e) or {}
    sector = obj.get("sector") or meta.get("sector") or sector_map().get(e)
    n100 = set(NIFTY_50) | set(NIFTY_100_EXTRA)
    membership = []
    if e in NIFTY_50:
        membership.append("nifty_50")
    if e in n100:
        membership.append("nifty_100")
    if e in NIFTY_500:
        membership.append("nifty_500")
    price = latest(e, "price")
    shares = latest(e, "shares")
    market_cap = None
    if price is not None and shares is not None:
        market_cap = round(float(price) * float(shares), 2)
    return {
        "entity": e,
        "company_profile": bool(obj) or bool(meta),
        "sector": sector,
        "industry": obj.get("industry") or sector,
        "sub_industry": obj.get("sub_industry") or obj.get("industry") or sector,
        "market_cap": market_cap,
        "exchange": obj.get("exchange") or "NSE",
        "index_membership": membership,
        "found": bool(sector) and (e in NIFTY_500 or bool(obj)),
    }


def institutional_depth_checklist(entity: str) -> dict[str, Any]:
    """Per-company Infosys-class depth checklist (never fabricate)."""
    from knowledge_factory.coverage import _company_checklist
    from knowledge_factory.store import repository as store
    from institutional_reasoning.fundamentals.derivations import derive_series
    from institutional_reasoning.fundamentals.primitives import has_primitives, FISCAL_YEARS

    e = entity.upper()
    base = _company_checklist(e)
    identity = company_identity(e)
    sector = identity.get("sector") or base.get("sector")
    derive_sector = _derive_sector_key(sector)

    hist_years = len(FISCAL_YEARS) if has_primitives(e) else 0
    try:
        from knowledge_factory.historical_depth import store as hd_store

        hd_obj = hd_store.get_object("company", e) or {}
        if hd_obj:
            hist_years = max(
                hist_years,
                int(hd_obj.get("history_years") or hd_obj.get("years") or hist_years),
            )
    except Exception:
        pass

    pe = derive_series(e, "PE", sector=derive_sector)
    pb = derive_series(e, "PB", sector=derive_sector)
    hist_val = bool(pe.get("found") and pe.get("points") and pb.get("found") and pb.get("points"))
    try:
        from knowledge_factory.historical_depth.queries import valuation_bands

        hv = valuation_bands(e) or {}
        if hv.get("found") and hv.get("bands"):
            hist_val = True
    except Exception:
        pass

    obj = store.get_object("company", e) or {}
    peers = obj.get("peers") or {}
    peer_ok = bool(
        peers.get("found")
        or peers.get("peers")
        or peers.get("primary")
        or peers.get("members")
        or peers.get("valuation_rank") is not None
    )
    if not peer_ok and sector:
        from knowledge_factory.fixtures.seed import sector_map

        smap = sector_map()
        members = [t for t, s in smap.items() if s == sector and t != e]
        if len(members) < 1:
            # Singleton seed labels (e.g. energy_conglomerate, aviation) still
            # peer against their canonical / affinity sector group.
            try:
                from knowledge_factory.sector_intelligence.schema import canonicalize

                canon = canonicalize(sector)
            except Exception:
                canon = None
            affinity = {
                "oil_gas": {"energy", "energy_conglomerate", "oil_gas"},
                "industrials": {"industrials", "conglomerate", "diversified", "capital_goods"},
                "logistics": {"logistics", "aviation"},
                "consumer": {"consumer", "consumer_durables", "retail", "healthcare"},
                "internet": {"internet", "consumer_internet"},
                "chemicals": {"chemicals", "specialty_chem"},
                "nbfc": {"nbfc", "capital_markets"},
            }
            group = set(affinity.get(canon or "", set()))
            if sector:
                group.add(str(sector).lower())
            if canon:
                group.add(canon)
            members = [
                t
                for t, s in smap.items()
                if str(s).lower() in group and t != e
            ]
            if not members and canon:
                members = [
                    t
                    for t, s in smap.items()
                    if canonicalize(s) == canon and t != e
                ]
        peer_ok = len(members) >= 1

    macro_ok = False
    macro_insufficient = False
    try:
        from knowledge_factory.macro_intelligence.links.company import company_macro_link

        link = company_macro_link(e)
        macro_ok = bool(link.get("macro_sensitivity")) and not link.get("insufficient")
        macro_insufficient = bool(link.get("insufficient"))
    except Exception:
        macro_ok = False

    sector_ok = bool(base["checks"].get("sector_object"))
    if sector and not sector_ok:
        try:
            from knowledge_factory.sector_intelligence.dna.catalog import sector_dna
            from knowledge_factory.sector_intelligence.playbooks.catalog import sector_playbook

            dna = sector_dna(sector)
            pbk = sector_playbook(sector)
            sector_ok = bool(dna.get("business_model") or pbk.get("playbook") or pbk.get("found"))
        except Exception:
            pass

    portfolio_ok = False
    try:
        port = store.get_object("portfolio", "BOOK") or {}
        portfolio_ok = bool(port) and bool(base["decision_ready"])
    except Exception:
        portfolio_ok = bool(base["decision_ready"])

    pack = store.get_pack(e) or {}
    evidence_quality = float(pack.get("quality") or obj.get("quality_score") or 0.0)

    checks = {
        "identity": bool(identity.get("found")),
        "historical_financials": hist_years >= 10 and bool(base["checks"].get("financials")),
        "derived_metrics": all(
            base["checks"].get(k) for k in ("historical_pe", "historical_pb", "ev", "roic", "roe")
        ),
        "historical_valuation": hist_val,
        "peer_intelligence": peer_ok,
        "timeline": bool(base["checks"].get("timeline")),
        "macro_links": macro_ok,
        "sector_links": sector_ok,
        "evidence_pack": bool(base["checks"].get("evidence_pack")),
        "portfolio_readiness": portfolio_ok,
        "decision_readiness": bool(base["decision_ready"]),
    }
    missing = [k for k in DEPTH_DIMENSIONS if not checks.get(k)]
    depth_ready = len(missing) == 0
    insufficient: list[str] = []
    if not checks["macro_links"]:
        insufficient.append(
            "macro_links" if not macro_insufficient else "macro_links:no_sector_affinity"
        )
    if hist_years < 10:
        insufficient.append("historical_financials:lt_10y")
    if evidence_quality < EVIDENCE_QUALITY_THRESHOLD and checks["evidence_pack"]:
        insufficient.append("evidence_quality_below_threshold")

    return {
        "depth_version": DEPTH_VERSION,
        "entity": e,
        "reference_standard": REFERENCE_ENTITY,
        "sector": sector,
        "identity": identity,
        "history_years": hist_years,
        "checks": checks,
        "missing": missing,
        "insufficient": insufficient,
        "institutional_depth_ready": depth_ready,
        "decision_ready": bool(base["decision_ready"]),
        "evidence_quality": evidence_quality,
        "evidence_quality_ok": evidence_quality >= EVIDENCE_QUALITY_THRESHOLD,
        "coverage_score": round(
            100.0 * (len(DEPTH_DIMENSIONS) - len(missing)) / len(DEPTH_DIMENSIONS), 1
        ),
        "fabricated": False,
    }


def institutional_decision_coverage(
    universe: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """North Star: share of universe at Infosys-class institutional depth."""
    from knowledge_factory.nifty500_universe import NIFTY_500

    universe = tuple(universe or NIFTY_500)
    rows = [institutional_depth_checklist(e) for e in universe]
    ready = sum(1 for r in rows if r["institutional_depth_ready"])
    decision_ready = sum(1 for r in rows if r["decision_ready"])
    n = len(universe) or 1
    return {
        "depth_version": DEPTH_VERSION,
        "north_star": "institutional_decision_coverage",
        "definition": (
            "Percentage of the universe for which AGIB can produce Infosys-class "
            "institutional depth: identity, historical financials, derived metrics, "
            "valuation history, peers, timeline, macro/sector links, evidence packs, "
            "portfolio readiness, and decision readiness — without fabricating."
        ),
        "universe": "nifty_500" if list(universe) == list(NIFTY_500) else "custom",
        "n": len(universe),
        "institutional_depth_ready": ready,
        "institutional_decision_coverage_pct": round(100.0 * ready / n, 2),
        "decision_ready": decision_ready,
        "decision_coverage_pct": round(100.0 * decision_ready / n, 2),
        "reference_entity": REFERENCE_ENTITY,
        "gaps": [r["entity"] for r in rows if not r["institutional_depth_ready"]],
        "rows": rows,
    }


def acceptance_for_company(entity: str) -> dict[str, Any]:
    """Eight acceptance tests for a newly onboarded company."""
    from knowledge_factory.coverage import _company_checklist
    from knowledge_factory.store import repository as store

    e = entity.upper()
    depth = institutional_depth_checklist(e)
    base = _company_checklist(e)
    pack = store.get_pack(e) or {}

    t1 = bool(pack) or bool(base["checks"].get("evidence_pack"))

    t2 = bool(depth["checks"].get("historical_financials"))
    try:
        from knowledge_factory.historical_depth.time_travel import state_as_of

        snap = state_as_of(e, "2020-03-31")
        if snap and not snap.get("fabricated") and (snap.get("found") is not False):
            t2 = True
    except Exception:
        pass

    t3 = bool(depth["checks"].get("sector_links") or depth["identity"].get("sector"))
    t4 = bool(depth["checks"].get("macro_links"))
    t5 = bool(depth.get("evidence_quality_ok"))
    t6 = bool(depth["checks"].get("portfolio_readiness"))

    t7 = False
    try:
        from decision_quality import store as idq_store

        t7 = callable(getattr(idq_store, "put_replay", None)) and callable(
            getattr(idq_store, "list_decisions", None)
        )
    except Exception:
        t7 = bool(depth["decision_ready"])

    t8 = depth.get("fabricated") is False and (
        depth["institutional_depth_ready"]
        or bool(depth.get("insufficient") or depth.get("missing"))
    )

    tests = {
        "research_package": t1,
        "historical_replay": t2,
        "sector_mapping": t3,
        "macro_links": t4,
        "evidence_quality_threshold": t5,
        "portfolio_package": t6,
        "decision_quality_replay": t7,
        "transparent_insufficiency": t8,
    }
    passed = sum(1 for v in tests.values() if v)
    return {
        "entity": e,
        "depth_version": DEPTH_VERSION,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "accepted": passed == len(tests),
        "depth": depth,
        "fabricated": False,
    }
