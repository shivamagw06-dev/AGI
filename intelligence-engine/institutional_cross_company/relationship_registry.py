"""CCI-01 Relationship Provider Registry — extensible like UAG-01 object registry.

CCI orchestrates providers; it does not hardcode every relationship type forever.
KG-01 remains the graph system of record.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from institutional_cross_company.kg_bridge import kg_evidence_refs, soft_get_company_graph
from institutional_cross_company.models import EvidenceRef, InstitutionalRelationship
from institutional_cross_company.schema import (
    CCI_VERSION,
    ECOSYSTEMS,
    MACRO_DRIVERS,
    MIN_CONFIDENCE,
    TYPE_TO_CATEGORY,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RelationshipProviderRegistration:
    relationship_type: str
    provider: str
    category: str
    description: str = ""
    discover: Optional[Callable[..., list[InstitutionalRelationship]]] = field(
        default=None, compare=False, hash=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_type": self.relationship_type,
            "provider": self.provider,
            "category": self.category,
            "description": self.description,
            "has_provider": self.discover is not None,
        }


_REGISTRY: dict[str, RelationshipProviderRegistration] = {}


def reset_registry_for_tests() -> None:
    _REGISTRY.clear()
    bootstrap_default_registry()


def register_relationship_provider(
    relationship_type: str,
    *,
    provider: str,
    category: str = "",
    description: str = "",
    discover: Optional[Callable[..., list[InstitutionalRelationship]]] = None,
) -> None:
    key = str(relationship_type).strip().lower()
    _REGISTRY[key] = RelationshipProviderRegistration(
        relationship_type=key,
        provider=provider,
        category=category or TYPE_TO_CATEGORY.get(key, "business"),
        description=description,
        discover=discover,
    )


def get(relationship_type: str) -> Optional[RelationshipProviderRegistration]:
    return _REGISTRY.get(str(relationship_type).strip().lower())


def all_providers() -> list[RelationshipProviderRegistration]:
    return list(_REGISTRY.values())


def catalog() -> list[dict[str, Any]]:
    return [r.to_dict() for r in sorted(_REGISTRY.values(), key=lambda x: x.relationship_type)]


def _rid(rtype: str, src: str, tgt: str) -> str:
    raw = f"{rtype}|{src}|{tgt}|{CCI_VERSION}"
    return f"rel-{hashlib.sha256(raw.encode()).hexdigest()[:14]}"


def _ev(evidence_id: str, label: str, source: str = "CCI-01", snippet: str = "") -> EvidenceRef:
    return EvidenceRef(evidence_id=evidence_id, label=label, source=source, snippet=snippet)


def make_relationship(
    *,
    source: str,
    target: str,
    relationship_type: str,
    strength: float,
    confidence: float,
    provider: str,
    evidence: list[EvidenceRef] | tuple[EvidenceRef, ...] = (),
    propagation_path: list[str] | tuple[str, ...] = (),
    kg_backed: bool = False,
) -> InstitutionalRelationship:
    return InstitutionalRelationship(
        relationship_id=_rid(relationship_type, source, target),
        source_entity=source,
        target_entity=target,
        relationship_type=relationship_type,
        strength=max(0.0, min(1.0, float(strength))),
        confidence=max(0.0, min(1.0, float(confidence))),
        evidence=tuple(evidence),
        propagation_path=tuple(propagation_path),
        category=TYPE_TO_CATEGORY.get(relationship_type, ""),
        provider=provider,
        version=CCI_VERSION,
        kg_backed=kg_backed,
        generated_at=now_iso(),
    )


def ecosystem_for(ticker: str) -> Optional[tuple[str, dict[str, object]]]:
    t = str(ticker or "").upper().strip()
    for key, eco in ECOSYSTEMS.items():
        members = tuple(str(m).upper() for m in (eco.get("members") or ()))
        if t in members:
            return key, eco
    return None


def peers_of(ticker: str) -> list[str]:
    hit = ecosystem_for(ticker)
    if not hit:
        return []
    _, eco = hit
    t = ticker.upper()
    return [m for m in (eco.get("members") or ()) if str(m).upper() != t]


# --- Default providers ---


def _discover_competitors(ctx: dict[str, Any]) -> list[InstitutionalRelationship]:
    ticker = str(ctx.get("ticker") or "").upper()
    if not ticker:
        return []
    out: list[InstitutionalRelationship] = []
    peers = peers_of(ticker)

    # Soft peer intelligence enrichment
    try:
        from peer_intelligence.production import company as pil_company

        pil = pil_company(ticker)
        resolve = pil.get("resolve") or {}
        for p in (resolve.get("peers") or resolve.get("tickers") or [])[:8]:
            pt = str(p if isinstance(p, str) else p.get("ticker") or "").upper()
            if pt and pt != ticker and pt not in peers:
                peers.append(pt)
    except Exception:
        pass

    kg_refs = kg_evidence_refs(ticker)
    kg_backed = bool(soft_get_company_graph(ticker).get("ok"))
    for peer in peers:
        evidence = [
            _ev(f"eco-{ticker}-{peer}", f"Peer group membership: {ticker} ↔ {peer}", "ecosystem_seed"),
        ]
        for ref in kg_refs[:1]:
            evidence.append(_ev(ref["evidence_id"], ref["label"], ref["source"], ref.get("snippet") or ""))
        out.append(
            make_relationship(
                source=ticker,
                target=peer,
                relationship_type="competitor",
                strength=0.85,
                confidence=0.8 if kg_backed else 0.65,
                provider="competitor_engine",
                evidence=evidence,
                propagation_path=[ticker, "competitor", peer],
                kg_backed=kg_backed,
            )
        )
    return out


def _discover_sector(ctx: dict[str, Any]) -> list[InstitutionalRelationship]:
    ticker = str(ctx.get("ticker") or "").upper()
    if not ticker:
        return []
    hit = ecosystem_for(ticker)
    if not hit:
        return []
    _, eco = hit
    sector = str(eco.get("sector") or "")
    industry = str(eco.get("industry") or "")
    cluster = str(eco.get("cluster") or industry)
    evidence = [
        _ev(f"sector-{ticker}", f"{ticker} in {sector} / {industry}", "ecosystem_seed"),
    ]
    kg = soft_get_company_graph(ticker)
    if kg.get("ok"):
        evidence.append(_ev(f"kg-sector-{ticker}", "KG-01 sector linkage", "KG-01"))
    out = [
        make_relationship(
            source=ticker,
            target=sector,
            relationship_type="same_sector",
            strength=0.9,
            confidence=0.85,
            provider="sector_relationship_engine",
            evidence=evidence,
            propagation_path=[ticker, "sector", sector],
            kg_backed=bool(kg.get("ok")),
        ),
        make_relationship(
            source=ticker,
            target=industry,
            relationship_type="same_industry",
            strength=0.88,
            confidence=0.82,
            provider="sector_relationship_engine",
            evidence=evidence,
            propagation_path=[ticker, "industry", industry],
            kg_backed=bool(kg.get("ok")),
        ),
        make_relationship(
            source=ticker,
            target=cluster,
            relationship_type="peer_group",
            strength=0.87,
            confidence=0.8,
            provider="sector_relationship_engine",
            evidence=evidence,
            propagation_path=[ticker, "peer_group", cluster],
        ),
    ]
    return out


def _discover_macro(ctx: dict[str, Any]) -> list[InstitutionalRelationship]:
    ticker = str(ctx.get("ticker") or "").upper()
    driver = str(ctx.get("macro_driver") or "").lower()
    out: list[InstitutionalRelationship] = []

    if ticker:
        hit = ecosystem_for(ticker)
        macros = list((hit[1].get("macro") or ()) if hit else ())
        for m in macros:
            meta = MACRO_DRIVERS.get(str(m), {})
            out.append(
                make_relationship(
                    source=ticker,
                    target=str(m),
                    relationship_type=str(m),
                    strength=0.75,
                    confidence=0.7,
                    provider="macro_dependency_engine",
                    evidence=[
                        _ev(
                            f"macro-{ticker}-{m}",
                            f"{ticker} exposed to {meta.get('label') or m}",
                            "macro_dependency",
                            str(meta.get("channel") or ""),
                        )
                    ],
                    propagation_path=[str(m), "sector", ticker],
                )
            )
        return out

    # Macro → affected companies
    if driver and driver in MACRO_DRIVERS:
        meta = MACRO_DRIVERS[driver]
        clusters = set(meta.get("affects_clusters") or ())
        for eco in ECOSYSTEMS.values():
            if eco.get("cluster") in clusters or driver in (eco.get("macro") or ()):
                for member in eco.get("members") or ():
                    out.append(
                        make_relationship(
                            source=driver,
                            target=str(member).upper(),
                            relationship_type=driver,
                            strength=0.7,
                            confidence=0.68,
                            provider="macro_dependency_engine",
                            evidence=[
                                _ev(
                                    f"macro-{driver}-{member}",
                                    f"{meta.get('label')} → {member}",
                                    "macro_dependency",
                                    str(meta.get("channel") or ""),
                                )
                            ],
                            propagation_path=[driver, str(eco.get("cluster")), str(member).upper()],
                        )
                    )
    return out


def _discover_portfolio(ctx: dict[str, Any]) -> list[InstitutionalRelationship]:
    ticker = str(ctx.get("ticker") or "").upper()
    portfolio_id = str(ctx.get("portfolio_id") or "agi-core-equity")
    out: list[InstitutionalRelationship] = []
    holdings: list[str] = []

    try:
        from institutional_portfolio.production import get_portfolio_graph

        g = get_portfolio_graph(portfolio_id, include_company_graphs=False)
        graph = (g or {}).get("graph") or g or {}
        for h in graph.get("holdings") or graph.get("positions") or []:
            ht = str(h.get("ticker") if isinstance(h, dict) else h or "").upper()
            if ht:
                holdings.append(ht)
    except Exception:
        holdings = ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "TCS", "INFY", "RELIANCE"]

    if ticker and ticker in holdings:
        out.append(
            make_relationship(
                source=ticker,
                target=portfolio_id,
                relationship_type="common_holding",
                strength=0.9,
                confidence=0.75,
                provider="portfolio_relationship_engine",
                evidence=[_ev(f"hold-{ticker}", f"{ticker} in {portfolio_id}", "PKG-01")],
                propagation_path=[ticker, "portfolio", portfolio_id],
            )
        )
        # Common risk / policy / committee soft links
        for rtype, provider_note in (
            ("common_risk", "PRE-01"),
            ("common_policy", "PCE-01"),
            ("common_committee", "ICE-01"),
        ):
            out.append(
                make_relationship(
                    source=ticker,
                    target=portfolio_id,
                    relationship_type=rtype,
                    strength=0.7,
                    confidence=0.65,
                    provider="portfolio_relationship_engine",
                    evidence=[_ev(f"{rtype}-{ticker}", f"{rtype} via {provider_note}", provider_note)],
                    propagation_path=[ticker, rtype, portfolio_id],
                )
            )
        for other in holdings:
            if other == ticker:
                continue
            out.append(
                make_relationship(
                    source=ticker,
                    target=other,
                    relationship_type="common_holding",
                    strength=0.6,
                    confidence=0.6,
                    provider="portfolio_relationship_engine",
                    evidence=[_ev(f"cohold-{ticker}-{other}", f"Co-held in {portfolio_id}", "PKG-01")],
                    propagation_path=[ticker, portfolio_id, other],
                )
            )
    elif not ticker:
        # Portfolio-wide co-holding mesh (capped)
        for i, a in enumerate(holdings[:6]):
            for b in holdings[i + 1 : 6]:
                out.append(
                    make_relationship(
                        source=a,
                        target=b,
                        relationship_type="common_holding",
                        strength=0.55,
                        confidence=0.55,
                        provider="portfolio_relationship_engine",
                        evidence=[_ev(f"cohold-{a}-{b}", f"Co-held in {portfolio_id}", "PKG-01")],
                        propagation_path=[a, portfolio_id, b],
                    )
                )
    return out


def _discover_ownership(ctx: dict[str, Any]) -> list[InstitutionalRelationship]:
    """Soft ownership — only when KG or known seeds provide evidence; no invention."""
    ticker = str(ctx.get("ticker") or "").upper()
    if not ticker:
        return []
    # Known infra adjacency (ports) — evidence-tagged seed, not a second graph
    seeds = {
        "ADANIPORTS": [("ADANIPOWER", "partner", 0.55)],
    }
    out: list[InstitutionalRelationship] = []
    for target, rtype, strength in seeds.get(ticker, []):
        out.append(
            make_relationship(
                source=ticker,
                target=target,
                relationship_type=rtype,
                strength=strength,
                confidence=0.55,
                provider="ownership_relationship_engine",
                evidence=[_ev(f"own-{ticker}-{target}", f"Seed {rtype} link", "ownership_seed")],
                propagation_path=[ticker, rtype, target],
            )
        )
    # Soft-scan KG for ownership-like labels if present
    pack = soft_get_company_graph(ticker)
    graph = pack.get("graph") or {}
    rels = graph.get("relationships") or {}
    rel_iter = rels.values() if isinstance(rels, dict) else (rels if isinstance(rels, list) else [])
    for rel in rel_iter:
        if not isinstance(rel, dict):
            continue
        label = str(rel.get("label") or rel.get("relationship_type") or "").lower()
        if any(k in label for k in ("parent", "subsidiary", "holding", "owner")):
            src = str(rel.get("source_id") or rel.get("source") or ticker)
            tgt = str(rel.get("target_id") or rel.get("target") or "")
            if not tgt:
                continue
            rtype = "parent" if "parent" in label else "subsidiary" if "subsid" in label else "cross_holding"
            out.append(
                make_relationship(
                    source=src,
                    target=tgt,
                    relationship_type=rtype,
                    strength=0.7,
                    confidence=0.6,
                    provider="ownership_relationship_engine",
                    evidence=[_ev(str(rel.get("id") or tgt), f"KG-01 {label}", "KG-01")],
                    propagation_path=[src, rtype, tgt],
                    kg_backed=True,
                )
            )
    return out


def bootstrap_default_registry() -> None:
    if _REGISTRY:
        return
    register_relationship_provider(
        "competitor",
        provider="competitor_engine",
        category="business",
        description="Business competitors / peer rivalry",
        discover=_discover_competitors,
    )
    # Extensibility hooks — empty discover until dedicated providers register
    def _empty(_ctx: dict[str, Any]) -> list[InstitutionalRelationship]:
        return []

    for rtype in ("supplier", "customer", "distributor"):
        register_relationship_provider(
            rtype,
            provider="business_relationship_engine",
            category="business",
            description=f"Business {rtype} (provider slot)",
            discover=_empty,
        )
    register_relationship_provider(
        "partner",
        provider="ownership_relationship_engine",
        category="business",
        description="Business partner / adjacency",
        discover=_discover_ownership,
    )
    # Ownership types share one discoverer (deduped by relationship_id in discover_all)
    register_relationship_provider(
        "parent",
        provider="ownership_relationship_engine",
        category="ownership",
        description="Ownership parent",
        discover=_discover_ownership,
    )
    for rtype in ("subsidiary", "cross_holding"):
        register_relationship_provider(
            rtype,
            provider="ownership_relationship_engine",
            category="ownership",
            description=f"Ownership {rtype} (provider slot)",
            discover=_empty,
        )
    # Sector discoverer emits same_sector + same_industry + peer_group in one pass.
    register_relationship_provider(
        "same_sector",
        provider="sector_relationship_engine",
        category="sector",
        description="Sector linkage (emits same_sector / same_industry / peer_group)",
        discover=_discover_sector,
    )
    for rtype in ("same_industry", "peer_group", "index_membership"):
        register_relationship_provider(
            rtype,
            provider="sector_relationship_engine",
            category="sector",
            description=f"Sector {rtype} (provider slot / covered by sector discoverer)",
            discover=_empty,
        )
    for rtype in MACRO_DRIVERS:
        register_relationship_provider(
            rtype,
            provider="macro_dependency_engine",
            category="macro",
            description=f"Macro driver {rtype}",
            discover=_discover_macro,
        )
    for rtype in ("common_holding", "common_policy", "common_risk", "common_committee"):
        register_relationship_provider(
            rtype,
            provider="portfolio_relationship_engine",
            category="portfolio",
            description=f"Portfolio {rtype}",
            discover=_discover_portfolio,
        )


def discover_all(ctx: dict[str, Any]) -> list[InstitutionalRelationship]:
    seen: set[str] = set()
    out: list[InstitutionalRelationship] = []
    for reg in all_providers():
        if not reg.discover:
            continue
        try:
            rows = reg.discover(ctx) or []
        except Exception:
            rows = []
        for rel in rows:
            if rel.confidence < MIN_CONFIDENCE:
                continue
            if rel.relationship_id in seen:
                continue
            seen.add(rel.relationship_id)
            out.append(rel)
    return out


bootstrap_default_registry()
