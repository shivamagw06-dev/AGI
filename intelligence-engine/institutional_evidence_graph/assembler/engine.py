"""IEG assembler — build institutional evidence graphs from soft-read sources."""

from __future__ import annotations

import uuid
from typing import Any

from institutional_evidence_graph.chains.paths import build_chains, chain_bullets
from institutional_evidence_graph.edges.relationships import edge
from institutional_evidence_graph.nodes.evidence import domain_node, entity_node, evidence_node
from institutional_evidence_graph.ontology.domains import DOMAIN_LABELS, domain_coverage, empty_domain_tree
from institutional_evidence_graph.quality.gates import validate_graph
from institutional_evidence_graph.replay.filter import filter_edges, filter_nodes
from institutional_evidence_graph.schema import (
    ENTITY_DOMAINS,
    EVIDENCE_TYPE_TO_DOMAIN,
    FREEZE_LOCKS,
    IEG_VERSION,
    MODULE_CODE,
    PROGRAMME,
    RELATIONSHIP_BUCKET_TO_DOMAIN,
)
from institutional_evidence_graph.seeds.entity_profiles import domain_stub_seeds, historical_event_seeds


def build_evidence_graph(
    *,
    question: str,
    entities: list[dict[str, Any]] | None = None,
    ticker_hint: str | None = None,
    concept_mode: bool = False,
    as_of: str | None = None,
    evidence: dict[str, Any] | None = None,
    knowledge: dict[str, Any] | None = None,
    playbook_selection: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    intent_v2: str | None = None,
) -> dict[str, Any]:
    """Assemble entity-centric evidence graph after playbooks, before reasoning.

    Soft-reads IERE ranked evidence + IERI relationships/transmission + curated seeds.
    Never fabricates relationships. Point-in-time when as_of is set.
    """
    graph_id = f"ieg_{uuid.uuid4().hex[:12]}"
    company_ids = _resolve_companies(
        entities=entities or [],
        ticker_hint=ticker_hint,
        concept_mode=concept_mode,
        question=question,
    )
    industry_ids = _resolve_industries(question=question) if not company_ids else []

    ranked = _ranked_evidence(knowledge=knowledge, evidence=evidence)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    entity_trees: dict[str, Any] = {}
    all_chains: list[dict[str, Any]] = []

    q_node = {
        "node_id": f"question:{graph_id}",
        "kind": "question",
        "label": (question or "")[:160],
        "fabricated": False,
    }
    nodes.append(q_node)

    # Soft-read IERI once
    ieri_ok = False
    try:
        from knowledge_factory.economic_relationship_intelligence.production import (
            company as ieri_company,
        )
        from knowledge_factory.economic_relationship_intelligence.transmission.orders import (
            transmission_from_entity as ieri_transmission,
        )

        ieri_ok = True
    except Exception:
        ieri_company = None  # type: ignore
        ieri_transmission = None  # type: ignore

    hist_seeds = historical_event_seeds()
    stub_seeds = domain_stub_seeds()

    for cid in company_ids:
        en = entity_node(cid)
        nodes.append(en)
        edges.append(edge(q_node["node_id"], en["node_id"], relationship="asks_about", weight=1.0, confidence=0.95))

        tree = empty_domain_tree(cid)
        for domain in ENTITY_DOMAINS:
            dn = domain_node(cid, domain, label=DOMAIN_LABELS.get(domain, domain))
            nodes.append(dn)
            edges.append(
                edge(en["node_id"], dn["node_id"], relationship="has_domain", weight=1.0, confidence=1.0)
            )

        # IERE ranked evidence → domain nodes
        for item in ranked:
            if not _evidence_belongs(item, cid, concept_mode=concept_mode):
                continue
            et = str(item.get("evidence_type") or "")
            domain = EVIDENCE_TYPE_TO_DOMAIN.get(et, "news")
            node = evidence_node(
                entity=cid,
                domain=domain,
                source=str(item.get("source") or "knowledge_factory"),
                timestamp=item.get("available_from"),
                available_from=item.get("available_from"),
                confidence=float(item.get("confidence") or item.get("rank_score") or 0.5),
                document=item.get("document_id"),
                paragraph=item.get("title"),
                title=item.get("title"),
                evidence_id=item.get("evidence_id"),
                relationship="supports",
                kind="evidence",
            )
            nodes.append(node)
            edges.append(
                edge(
                    f"domain:{cid}:{domain}",
                    node["node_id"],
                    relationship="contains_evidence",
                    weight=float(item.get("rank_score") or 0.6),
                    confidence=float(item.get("confidence") or 0.5),
                    available_from=item.get("available_from"),
                    evidence_strength=node.get("evidence_strength"),
                )
            )
            tree["domains"][domain]["node_ids"].append(node["node_id"])

        # IERI relationships
        buckets: dict[str, list] = {}
        tx: dict[str, Any] = {}
        if ieri_ok and ieri_company is not None:
            try:
                rel = ieri_company(cid, as_of=as_of)
                buckets = rel.get("relationships") or {}
                for bucket, rows in buckets.items():
                    domain = RELATIONSHIP_BUCKET_TO_DOMAIN.get(bucket)
                    if not domain:
                        continue
                    for row in rows[:8]:
                        cp = row.get("counterpart")
                        node = evidence_node(
                            entity=cid,
                            domain=domain,
                            source="ieri",
                            available_from=row.get("available_from") or "2015-01-01",
                            confidence=float(row.get("confidence") or 0.7),
                            relationship=str(row.get("relationship_type") or bucket),
                            title=f"{cid} {row.get('relationship_type')} {cp}",
                            paragraph=str(row.get("evidence") or row.get("relationship_type") or ""),
                            counterpart=str(cp) if cp else None,
                            evidence_id=row.get("relationship_id"),
                            kind="relationship",
                            evidence_strength=7.5,
                        )
                        nodes.append(node)
                        edges.append(
                            edge(
                                f"domain:{cid}:{domain}",
                                node["node_id"],
                                relationship=str(row.get("relationship_type") or "related_to"),
                                weight=0.8,
                                confidence=float(row.get("confidence") or 0.7),
                                available_from=row.get("available_from"),
                                evidence_strength=7.5,
                            )
                        )
                        tree["domains"][domain]["node_ids"].append(node["node_id"])
                        if cp:
                            cp_node = entity_node(str(cp), kind="related")
                            if not any(n.get("node_id") == cp_node["node_id"] for n in nodes):
                                nodes.append(cp_node)
                            edges.append(
                                edge(
                                    en["node_id"],
                                    cp_node["node_id"],
                                    relationship=str(row.get("relationship_type") or "related_to"),
                                    weight=0.75,
                                    confidence=float(row.get("confidence") or 0.7),
                                    available_from=row.get("available_from"),
                                )
                            )
            except Exception:
                buckets = {}

            try:
                if ieri_transmission is not None:
                    tx = ieri_transmission(cid, as_of=as_of, max_order=3, limit=30)
            except Exception:
                tx = {}

        # Curated stubs (structure)
        for stub in stub_seeds:
            if str(stub.get("entity")).upper() != cid:
                continue
            domain = str(stub.get("domain"))
            if domain not in tree["domains"]:
                continue
            node = evidence_node(
                entity=cid,
                domain=domain,
                source=str(stub.get("source") or "ieri"),
                available_from=stub.get("available_from"),
                confidence=float(stub.get("confidence") or 0.7),
                relationship=str(stub.get("relationship")),
                title=stub.get("title"),
                counterpart=stub.get("counterpart"),
                kind=str(stub.get("kind") or "relationship_stub"),
                evidence_strength=float(stub.get("evidence_strength") or 7.0),
            )
            nodes.append(node)
            edges.append(
                edge(
                    f"domain:{cid}:{domain}",
                    node["node_id"],
                    relationship="profile_link",
                    weight=0.7,
                    confidence=float(stub.get("confidence") or 0.7),
                    available_from=stub.get("available_from"),
                )
            )
            tree["domains"][domain]["node_ids"].append(node["node_id"])

        # Historical events (replay-critical)
        for ev in hist_seeds:
            if str(ev.get("entity")).upper() != cid:
                continue
            domain = str(ev.get("domain") or "historical_events")
            node = evidence_node(
                entity=cid,
                domain=domain,
                source=str(ev.get("source") or "institutional_documents"),
                timestamp=ev.get("timestamp"),
                available_from=ev.get("available_from"),
                confidence=float(ev.get("confidence") or 0.8),
                relationship=str(ev.get("relationship") or "historical_event"),
                title=ev.get("title"),
                paragraph=ev.get("paragraph"),
                kind="historical_event",
            )
            nodes.append(node)
            edges.append(
                edge(
                    f"domain:{cid}:{domain}",
                    node["node_id"],
                    relationship="historical_event",
                    weight=0.85,
                    confidence=float(ev.get("confidence") or 0.8),
                    available_from=ev.get("available_from"),
                    evidence_strength=node.get("evidence_strength"),
                )
            )
            tree["domains"][domain]["node_ids"].append(node["node_id"])

        # Finalize domain counts
        for domain, meta in tree["domains"].items():
            # unique node ids
            uniq_ids = list(dict.fromkeys(meta["node_ids"]))
            meta["node_ids"] = uniq_ids
            meta["n_nodes"] = len(uniq_ids)
            meta["coverage"] = "filled" if uniq_ids else "empty"

        entity_trees[cid] = {
            **tree,
            "coverage": domain_coverage(tree),
        }
        chains = build_chains(
            entity=cid,
            transmission=tx,
            relationship_buckets=buckets,
        )
        all_chains.extend(chains)

    # Concept / industry questions without tickers — soft industry/commodity graph
    if not company_ids and industry_ids and ieri_ok:
        for ind in industry_ids:
            en = entity_node(ind, kind="industry")
            nodes.append(en)
            edges.append(
                edge(q_node["node_id"], en["node_id"], relationship="asks_about", weight=1.0, confidence=0.9)
            )
            tree = empty_domain_tree(ind)
            try:
                from knowledge_factory.economic_relationship_intelligence.production import (
                    industry as ieri_industry,
                    search as ieri_search,
                )

                ind_view = ieri_industry(ind, as_of=as_of)
                rows = []
                if isinstance(ind_view, dict):
                    for bucket_rows in (ind_view.get("relationships") or {}).values():
                        if isinstance(bucket_rows, list):
                            rows.extend(bucket_rows)
                if not rows:
                    search_hits = ieri_search(ind, as_of=as_of, limit=40)
                    rows = [
                        {
                            "counterpart": h.get("target") if h.get("source") == ind else h.get("source"),
                            "relationship_type": h.get("relationship_type"),
                            "confidence": h.get("confidence"),
                            "available_from": "2015-01-01",
                            "evidence": h.get("relationship_type"),
                            "relationship_id": h.get("relationship_id"),
                            "shock_direction": h.get("shock_direction"),
                            "transmission_order": h.get("transmission_order"),
                        }
                        for h in (search_hits.get("results") or [])
                    ]
                for row in rows[:20]:
                    domain = "macro_exposure"
                    rtype = str(row.get("relationship_type") or "")
                    if "competitor" in rtype:
                        domain = "competitors"
                    elif "supplier" in rtype or "customer" in rtype:
                        domain = "suppliers" if "supplier" in rtype else "customers"
                    node = evidence_node(
                        entity=ind,
                        domain=domain,
                        source="ieri",
                        available_from=row.get("available_from") or "2015-01-01",
                        confidence=float(row.get("confidence") or 0.7),
                        relationship=rtype or "related_to",
                        title=f"{ind} · {rtype} · {row.get('counterpart')}",
                        counterpart=str(row.get("counterpart")) if row.get("counterpart") else None,
                        evidence_id=row.get("relationship_id"),
                        kind="relationship",
                    )
                    nodes.append(node)
                    # ensure domain node exists
                    dn_id = f"domain:{ind}:{domain}"
                    if not any(n.get("node_id") == dn_id for n in nodes):
                        nodes.append(domain_node(ind, domain, label=DOMAIN_LABELS.get(domain, domain)))
                        edges.append(
                            edge(en["node_id"], dn_id, relationship="has_domain", weight=1.0, confidence=1.0)
                        )
                    edges.append(
                        edge(
                            dn_id,
                            node["node_id"],
                            relationship=rtype or "related_to",
                            weight=0.75,
                            confidence=float(row.get("confidence") or 0.7),
                            available_from=row.get("available_from"),
                        )
                    )
                    tree["domains"][domain]["node_ids"].append(node["node_id"])
            except Exception:
                pass
            for domain, meta in tree["domains"].items():
                uniq_ids = list(dict.fromkeys(meta["node_ids"]))
                meta["node_ids"] = uniq_ids
                meta["n_nodes"] = len(uniq_ids)
                meta["coverage"] = "filled" if uniq_ids else "empty"
            entity_trees[ind] = {**tree, "coverage": domain_coverage(tree)}
            if ieri_transmission is not None:
                try:
                    tx = ieri_transmission(ind, as_of=as_of, max_order=3, limit=30)
                    all_chains.extend(build_chains(entity=ind, transmission=tx, relationship_buckets={}))
                except Exception:
                    pass

    # Point-in-time filter
    nodes = filter_nodes(nodes, as_of=as_of)
    node_ids = {n["node_id"] for n in nodes}
    edges = filter_edges(edges, node_ids=node_ids, as_of=as_of)

    # Recompute coverage after replay filter
    for cid, tree in entity_trees.items():
        for domain, meta in tree["domains"].items():
            kept = [nid for nid in meta["node_ids"] if nid in node_ids]
            meta["node_ids"] = kept
            meta["n_nodes"] = len(kept)
            meta["coverage"] = "filled" if kept else "empty"
        tree["coverage"] = domain_coverage(tree)

    # Playbook evidence_required soft overlay (marks missing domains)
    required = list((playbook_selection or {}).get("evidence_required") or [])
    missing_required = []
    for req in required:
        req_l = str(req).lower()
        found = False
        for tree in entity_trees.values():
            for domain, meta in (tree.get("domains") or {}).items():
                if req_l in domain or any(req_l in str(x).lower() for x in meta.get("node_ids") or []):
                    if meta.get("n_nodes", 0) > 0:
                        found = True
        if not found:
            missing_required.append(req)

    bullets = _surface_bullets(
        company_ids=list(entity_trees.keys()) or company_ids or industry_ids,
        entity_trees=entity_trees,
        chains=all_chains,
        as_of=as_of,
        missing_required=missing_required,
    )

    validation = validate_graph(nodes=nodes, edges=edges, entity_trees=entity_trees, as_of=as_of)
    coverage_pcts = [t["coverage"]["coverage_pct"] for t in entity_trees.values()] or [0]
    avg_cov = int(round(sum(coverage_pcts) / len(coverage_pcts)))

    return {
        "ok": True,
        "ieg_version": IEG_VERSION,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "graph_id": graph_id,
        "question": question,
        "intent_v2": intent_v2,
        "as_of": as_of,
        "concept_mode": bool(concept_mode),
        "entities": company_ids or industry_ids,
        "sector": (framework_selection or {}).get("sector"),
        "playbook_id": (playbook_selection or {}).get("playbook_id"),
        "nodes": nodes,
        "edges": edges,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "entity_trees": entity_trees,
        "chains": all_chains[:20],
        "chain_bullets": chain_bullets(all_chains),
        "surface_bullets": bullets,
        "domain_coverage_pct": avg_cov,
        "evidence_required": required,
        "missing_evidence_required": missing_required,
        "ranked_evidence_bound": len(ranked),
        "ieri_soft_read": ieri_ok,
        "validation": validation,
        "confidence": {
            "pct": min(92, 40 + avg_cov // 2 + (8 if ieri_ok else 0) + (5 if ranked else 0)),
            "band": "high" if avg_cov >= 55 else ("medium" if avg_cov >= 30 else "low"),
            "domain_coverage_pct": avg_cov,
        },
        "freeze_locks": FREEZE_LOCKS,
        "llm_used": False,
        "fabricated": False,
        "reasoning_changed": False,
        "guides_evidence": True,
    }


def _resolve_companies(
    *,
    entities: list[dict[str, Any]],
    ticker_hint: str | None,
    concept_mode: bool,
    question: str,
) -> list[str]:
    ids: list[str] = []
    if not concept_mode:
        for e in entities:
            if not isinstance(e, dict):
                continue
            if str(e.get("type") or "").lower() in {"company", "ticker", "equity", ""}:
                eid = e.get("entity_id") or e.get("id") or e.get("ticker")
                if eid:
                    ids.append(str(eid).upper())
        if ticker_hint:
            ids.append(str(ticker_hint).upper())
    # Concept / multi-name soft extract from question for known tickers
    low = (question or "").lower()
    alias = {
        "infosys": "INFY",
        "tcs": "TCS",
        "wipro": "WIPRO",
        "hdfc bank": "HDFCBANK",
        "reliance": "RELIANCE",
        "indigo": "INDIGO",
        "asian paints": "ASIANPAINT",
        "titan": "TITAN",
        "maruti": "MARUTI",
        "banks and insurance": "HDFCBANK",
        "for banks": "HDFCBANK",
    }
    for name, ticker in alias.items():
        if name in low:
            ids.append(ticker)
    # Deduplicate preserve order
    out: list[str] = []
    for x in ids:
        if x not in out:
            out.append(x)
    return out[:6]


def _resolve_industries(*, question: str) -> list[str]:
    import re

    low = (question or "").lower()
    mapping = [
        ("cement", "cement"),
        ("steel", "steel"),
        ("airline", "airlines"),
        ("aviation", "airlines"),
        ("hospital", "hospitals"),
        ("pharmaceutical", "pharma"),
        ("fmcg", "fmcg"),
        ("software", "it_services"),
        ("it services", "it_services"),
        ("nbfc", "nbfc"),
        ("real estate", "real_estate"),
        ("banks", "banks"),
        ("insurance", "insurance"),
        ("crude oil", "crude_oil"),
        ("oil price", "crude_oil"),
        ("oil prices", "crude_oil"),
        ("inflation", "inflation"),
        ("interest rate", "interest_rates"),
        ("repo rate", "interest_rates"),
        ("rupee", "fx"),
        ("currency", "fx"),
        ("gst", "fiscal"),
        ("import dut", "trade_policy"),
    ]
    out: list[str] = []
    for cue, ind in mapping:
        if " " in cue:
            hit = cue in low
        else:
            # Word-boundary: prevent 'repo' matching inside 'report'
            hit = re.search(rf"(?<![a-z0-9]){re.escape(cue)}(?![a-z0-9])", low) is not None
        if hit and ind not in out:
            out.append(ind)
    # Single 'bank' token (not 'banks') — only when not already covered
    if "banks" not in out and re.search(r"(?<![a-z0-9])bank(?![a-z0-9])", low):
        out.append("banks")
    return out[:4]


def _ranked_evidence(
    *,
    knowledge: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    kn = knowledge or {}
    iere = kn.get("iere") if isinstance(kn.get("iere"), dict) else {}
    ranked = list(iere.get("ranked_evidence") or [])
    if ranked:
        return [x for x in ranked if isinstance(x, dict)]
    # Fallback: assembly ordering if present on evidence
    ev = evidence or {}
    for key in ("ranked_evidence", "items"):
        rows = ev.get(key)
        if isinstance(rows, list) and rows:
            return [x for x in rows if isinstance(x, dict)]
    return []


def _evidence_belongs(item: dict[str, Any], company_id: str, *, concept_mode: bool) -> bool:
    co = item.get("company")
    if co is None or co == "" or concept_mode:
        return True
    return str(co).upper() == str(company_id).upper()


def _surface_bullets(
    *,
    company_ids: list[str],
    entity_trees: dict[str, Any],
    chains: list[dict[str, Any]],
    as_of: str | None,
    missing_required: list[str],
) -> list[str]:
    bullets: list[str] = []
    if as_of:
        bullets.append(f"Evidence graph replay as_of={as_of} — future-dated nodes excluded.")
    for cid in company_ids:
        cov = (entity_trees.get(cid) or {}).get("coverage") or {}
        filled = cov.get("n_filled") or 0
        total = cov.get("n_total") or len(ENTITY_DOMAINS)
        bullets.append(
            f"{cid} evidence domains filled: {filled}/{total} ({cov.get('coverage_pct')}%)."
        )
        hist = ((entity_trees.get(cid) or {}).get("domains") or {}).get("historical_events") or {}
        if hist.get("n_nodes"):
            bullets.append(f"{cid} historical event nodes bound: {hist.get('n_nodes')}.")
        comps = ((entity_trees.get(cid) or {}).get("domains") or {}).get("competitors") or {}
        if comps.get("n_nodes"):
            bullets.append(f"{cid} competitor / peer relationship nodes: {comps.get('n_nodes')}.")
    bullets.extend(chain_bullets(chains, max_items=6))
    if missing_required:
        bullets.append(
            "Playbook evidence still thin for: " + ", ".join(missing_required[:6])
        )
    if not company_ids:
        bullets.append(
            "No company entity bound — evidence graph limited to question-level relationships."
        )
    return bullets[:14]
