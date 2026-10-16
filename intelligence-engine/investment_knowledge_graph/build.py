"""Build investment graph slice for a company from memory + peers + ownership + IKG soft-read."""

from __future__ import annotations

from typing import Any

from investment_knowledge_graph.schema import MACRO_CHAINS, SECTOR_CHAINS, THEME_MAP


def _node(node_id: str, node_type: str, **props: Any) -> dict[str, Any]:
    return {"id": node_id, "type": node_type, "props": props}


def _edge(src: str, rel: str, tgt: str, **props: Any) -> dict[str, Any]:
    return {"source": src, "rel": rel, "target": tgt, "props": props}


def build_company_graph(
    ticker: str,
    *,
    memory: dict[str, Any] | None = None,
    ownership_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from company_memory.resolve import resolve_ticker
    from company_memory.derive.sector import sector_key_for

    entity = resolve_ticker(ticker)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def add_node(n: dict[str, Any]) -> None:
        nodes[n["id"]] = n

    def add_edge(e: dict[str, Any]) -> None:
        edges.append(e)

    add_node(_node(entity, "Company", ticker=entity))

    # Peers / sector from valuation registry + memory
    sector_key = "unknown"
    industry = None
    peers: list[str] = []
    try:
        from valuation_intelligence.peers import resolve_peers

        meta = resolve_peers(entity)
        sector_key = sector_key_for(entity)
        industry = meta.get("industry") or meta.get("sub_industry")
        peers = list(meta.get("primary_peers") or [])
        if meta.get("sector"):
            sid = f"sector:{meta['sector']}"
            add_node(_node(sid, "Sector", name=meta["sector"]))
            add_edge(_edge(entity, "BELONGS_TO", sid))
        if industry:
            iid = f"industry:{industry}"
            add_node(_node(iid, "Industry", name=industry))
            add_edge(_edge(entity, "BELONGS_TO", iid))
    except Exception:
        sector_key = sector_key_for(entity)

    mem = memory or {}
    if not mem:
        try:
            from knowledge_delta_engine.versioning import load_current

            mem = load_current(entity) or {}
        except Exception:
            mem = {}

    sh = mem.get("sector_history") or {}
    if sh.get("sector_key"):
        sector_key = sh.get("sector_key") or sector_key

    for p in peers:
        add_node(_node(p, "Company", ticker=p))
        add_edge(_edge(entity, "COMPETES_WITH", p, source="peer_registry"))

    # Sector causal chain
    chain = SECTOR_CHAINS.get(sector_key) or []
    prev = None
    for step in chain:
        nid = f"metric:{sector_key}:{step}"
        add_node(_node(nid, "Risk" if step in {"GNPA", "PCR"} else "Product", name=step, sector=sector_key))
        if prev:
            add_edge(_edge(prev, "DRIVES", nid, chain=sector_key))
        else:
            add_edge(_edge(entity, "EXPOSED_TO", nid, chain=sector_key))
        prev = nid
    if prev:
        add_edge(_edge(prev, "AFFECTED_BY", f"valuation:{entity}"))
        add_node(_node(f"valuation:{entity}", "Risk", name="Valuation", ticker=entity))

    # Theme membership
    themes_hit = []
    for theme, members in THEME_MAP.items():
        if entity in members or any(p in members for p in peers):
            tid = f"theme:{theme}"
            add_node(_node(tid, "Theme", name=theme))
            add_edge(_edge(entity, "RELATED_THEME", tid))
            themes_hit.append(theme)
            for m in members:
                if m == entity:
                    continue
                add_node(_node(m, "Company", ticker=m))
                add_edge(_edge(tid, "RELATED_THEME", m))

    # Ownership / institutions
    own = ownership_pack or mem.get("ownership_history") or {}
    latest = own.get("latest") if isinstance(own.get("latest"), dict) else own
    for inst_key, label in (
        ("fii", "FII"),
        ("dii", "DII"),
        ("mutual_funds", "MutualFunds"),
        ("insurance", "Insurance"),
    ):
        val = latest.get(inst_key) if isinstance(latest, dict) else None
        if val is None:
            continue
        iid = f"institution:{label}"
        add_node(_node(iid, "Institution", name=label))
        add_edge(_edge(iid, "OWNS", entity, weight_pct=val, source="ownership_memory"))

    promoter = latest.get("promoter") if isinstance(latest, dict) else None
    if promoter is not None:
        pid = f"promoter:{entity}"
        add_node(_node(pid, "Promoter", ticker=entity))
        add_edge(_edge(pid, "OWNS", entity, weight_pct=promoter))

    # Events from memory
    for ev in ((mem.get("event_timeline") or {}).get("events") or [])[-12:]:
        eid = f"event:{entity}:{ev.get('date')}:{hash(ev.get('title')) % 10_000}"
        add_node(
            _node(
                eid,
                "Event",
                date=ev.get("date"),
                title=ev.get("title"),
                event_type=ev.get("type"),
            )
        )
        add_edge(_edge(entity, "DISCUSSES", eid, source="event_timeline"))

    # Soft IKG overlay (locked seed graph — additive only)
    ikg_rels = []
    try:
        from knowledge_graph.production import company as ikg_company

        ikg = ikg_company(entity)
        if ikg and ikg.get("found"):
            for rel in (ikg.get("relationships") or [])[:30]:
                ikg_rels.append(rel)
                src = str(rel.get("source") or rel.get("from") or entity)
                tgt = str(rel.get("target") or rel.get("to") or "")
                r = str(rel.get("type") or rel.get("rel") or "RELATED_THEME").upper().replace(" ", "_")
                if not tgt:
                    continue
                add_node(_node(tgt, "Company" if len(tgt) <= 20 else "Theme", name=tgt))
                mapped = {
                    "COMPETES_WITH": "COMPETES_WITH",
                    "OWNS": "OWNS",
                    "MEMBER_OF": "BELONGS_TO",
                    "AFFECTED_BY": "AFFECTED_BY",
                    "DEPENDS_ON": "USES",
                    "DRIVES": "DRIVES",
                    "INVESTS_IN": "OWNS",
                }.get(r, "RELATED_THEME")
                add_edge(_edge(src, mapped, tgt, source="ikg_soft"))
    except Exception:
        pass

    # Currency exposure soft for IT
    if sector_key == "it_services":
        add_node(_node("currency:USD", "Currency", code="USD"))
        add_edge(_edge(entity, "EXPOSED_TO", "currency:USD"))
        add_node(_node("tech:GenerativeAI", "Technology", name="Generative AI"))
        add_edge(_edge(entity, "USES", "tech:GenerativeAI"))
        add_node(_node("customer:BFSI", "Customer", name="BFSI"))
        add_edge(_edge(entity, "SERVES", "customer:BFSI"))

    # Auto supply chain soft
    if sector_key == "auto":
        add_node(_node("commodity:Steel", "Commodity", name="Steel"))
        add_edge(_edge(entity, "USES", "commodity:Steel"))
        add_node(_node("commodity:IronOre", "Commodity", name="Iron Ore"))
        add_edge(_edge("commodity:Steel", "AFFECTED_BY", "commodity:IronOre"))
        add_node(_node("macro:ChinaDemand", "MacroVariable", name="China Demand"))
        add_edge(_edge("commodity:IronOre", "AFFECTED_BY", "macro:ChinaDemand"))

    return {
        "entity": entity,
        "sector_key": sector_key,
        "industry": industry,
        "nodes": list(nodes.values()),
        "edges": edges,
        "peers": peers,
        "themes": themes_hit,
        "sector_chain": chain,
        "ikg_soft_relationships": len(ikg_rels),
        "n_nodes": len(nodes),
        "n_edges": len(edges),
    }


def query_theme(theme: str) -> dict[str, Any]:
    key = None
    for t in THEME_MAP:
        if t.lower() == theme.lower() or theme.lower() in t.lower():
            key = t
            break
    if not key:
        return {"found": False, "theme": theme, "members": []}
    members = list(THEME_MAP[key])
    nodes = [_node(f"theme:{key}", "Theme", name=key)] + [_node(m, "Company", ticker=m) for m in members]
    edges = [_edge(f"theme:{key}", "RELATED_THEME", m) for m in members]
    return {"found": True, "theme": key, "members": members, "nodes": nodes, "edges": edges}


def query_macro_chain(chain_id: str | None = None) -> dict[str, Any]:
    if chain_id:
        rows = [c for c in MACRO_CHAINS if c["id"] == chain_id]
    else:
        rows = list(MACRO_CHAINS)
    out = []
    for c in rows:
        nodes = []
        edges = []
        seq = c["nodes"]
        for i, name in enumerate(seq):
            nid = f"macrochain:{c['id']}:{i}"
            nodes.append(_node(nid, "MacroVariable", name=name))
            if i > 0:
                rel = c["edges"][i - 1] if i - 1 < len(c["edges"]) else "DRIVES"
                edges.append(_edge(f"macrochain:{c['id']}:{i-1}", rel, nid))
        out.append({"id": c["id"], "nodes": nodes, "edges": edges, "narrative": " → ".join(seq)})
    return {"chains": out, "n": len(out)}


def ownership_concentration(graph: dict[str, Any]) -> dict[str, Any]:
    owns = [e for e in graph.get("edges") or [] if e.get("rel") == "OWNS"]
    by_inst: dict[str, list[dict[str, Any]]] = {}
    for e in owns:
        by_inst.setdefault(e["source"], []).append(e)
    return {
        "institutions": {
            k: {
                "holdings_n": len(v),
                "targets": [x["target"] for x in v],
                "weights": [x.get("props", {}).get("weight_pct") for x in v],
            }
            for k, v in by_inst.items()
        },
        "n_ownership_edges": len(owns),
    }
