"""IKG production facade — soft institutional layer, no redesign."""

from __future__ import annotations

from typing import Any

from knowledge_graph.entity_resolution.resolve import canonical_identity_report, resolve_entity
from knowledge_graph.evidence.attach import evidence_pack, is_supported
from knowledge_graph.flags import flags_dict, is_enabled
from knowledge_graph.graph.store import edges, graph_snapshot
from knowledge_graph.pipeline import analyse_company, analyse_entity, analyse_query, graph_health
from knowledge_graph.query.engine import find_path
from knowledge_graph.relationship_engine.engine import relationships_for
from knowledge_graph.schema import (
    ARCHITECTURE_STATUS,
    IKG_VERSION,
    NO_REDESIGN,
    PIPELINE,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IKG_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "not_an_engine_redesign": True,
        "never_recommendation": True,
    }


def dashboard() -> dict[str, Any]:
    gh = graph_health()
    sample = analyse_company("HDFCBANK")
    return {
        "programme": PROGRAMME,
        "ikg_version": IKG_VERSION,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "pipeline": list(PIPELINE),
        "graph_health": gh,
        "sample_ticker": "HDFCBANK",
        "sample_relationship_count": sample.get("relationship_count") if sample.get("found") else None,
        "sample_summary": (sample.get("report") or {}).get("executive_summary") if sample.get("found") else None,
        "sample_confidence": (sample.get("confidence") or {}).get("confidence") if sample.get("found") else None,
        "no_redesign": list(NO_REDESIGN),
        "website_surfaces": ["/admin/knowledge-graph"],
        "api_prefix": "/v1/knowledge-graph",
    }


def entity(entity_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ikg_version": IKG_VERSION}
    out = analyse_entity(entity_id)
    return {"enabled": True, **out}


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ikg_version": IKG_VERSION}
    out = analyse_company(ticker)
    return {"enabled": True, **out}


def relationships(entity_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ikg_version": IKG_VERSION}
    out = relationships_for(entity_id)
    return {"enabled": True, "ikg_version": IKG_VERSION, **out}


def query(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ikg_version": IKG_VERSION}
    out = analyse_query(payload or {})
    return {"enabled": True, **out}


def path(source: str, target: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ikg_version": IKG_VERSION}
    out = find_path(source, target)
    return {"enabled": True, "ikg_version": IKG_VERSION, **out}


def soft_slice_for_analyst(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_company(ticker)
    if not out.get("found"):
        return {"knowledge_graph": {"enabled": True, "found": False, "ticker": (ticker or "").upper()}}
    report = out.get("report") or {}
    deps = out.get("dependencies") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "found": True,
        "version": IKG_VERSION,
        "ticker": out.get("ticker"),
        "canonical_id": out.get("canonical_id"),
        "primary_question": PRIMARY_QUESTION,
        "relationship_count": out.get("relationship_count"),
        "confidence": (out.get("confidence") or {}).get("confidence"),
        "summary": report.get("executive_summary"),
        "rule": "Reason over connected knowledge — every relationship evidenced",
        "never_recommendation": True,
    }
    role = (analyst or "committee").lower()
    if role in {"business"}:
        base["desk"] = {
            "competitive_graph": [r for r in (out.get("relationships") or []) if r.get("relation") == "competes_with"],
            "customer_graph": deps.get("customers"),
            "supplier_graph": deps.get("suppliers"),
        }
    elif role == "financial":
        base["desk"] = {
            "ownership_graph": [r for r in (out.get("relationships") or []) if r.get("relation") in {"owns", "invests_in"}],
            "capital_graph": [r for r in (out.get("relationships") or []) if r.get("relation") in {"listed_on", "invests_in"}],
        }
    elif role == "sector":
        base["desk"] = {
            "industry_graph": [r for r in (out.get("relationships") or []) if r.get("relation") == "member_of"],
        }
    elif role == "risk":
        base["desk"] = {
            "dependency_graph": deps,
            "contagion_graph": deps.get("traversal_paths"),
        }
    elif role == "macro":
        base["desk"] = {
            "macro_graph": deps.get("macro_drivers"),
            "event_links": [r for r in (out.get("relationships") or []) if str(r.get("counterpart") or "").startswith("event_")],
        }
    elif role in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["cio_brief"] = report.get("cio_brief")
        base["dependencies"] = deps
        base["portfolio"] = report.get("portfolio")
    elif role in {"research_writer", "writer"}:
        base["writer_blocks"] = report.get("writer_blocks")
    else:
        base["desk"] = {"relationships": (out.get("relationships") or [])[:8], "dependencies": deps}
    base["evidence"] = {
        "count": (out.get("evidence") or {}).get("count"),
        "unsupported_rejected": (out.get("evidence") or {}).get("unsupported_rejected"),
    }
    return {"knowledge_graph": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "knowledge_graph": {
            "enabled": True,
            "version": IKG_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "Every relationship evidenced; canonical identities; no duplicates; historical edges preserved",
        }
    }


def soft_slice_for_stack() -> dict[str, Any]:
    return soft_slice_for_irs()


def quality_gates() -> dict[str, Any]:
    snap = graph_snapshot()
    canon = canonical_identity_report()
    evid = evidence_pack(snap["edges"])
    company_out = analyse_company("HDFCBANK")
    # Entity resolution aliases → one node
    a = resolve_entity("HDFC Bank Ltd.")
    b = resolve_entity("NSE:HDFCBANK")
    c = resolve_entity("BSE:500180")
    path_out = find_path("oil", "NESTLEIND")
    path2 = find_path("oil", "NESTLEIND")
    unsupported = [e for e in edges(include_unsupported=True) if not is_supported(e)]
    checks = {
        "enabled": is_enabled(),
        "every_relationship_has_evidence": evid.get("unsupported_rejected", 1) == 0 and evid.get("count", 0) >= 1,
        "every_node_has_canonical_identity": all(n.get("canonical") for n in snap["nodes"] if n.get("type") == "company"),
        "no_duplicate_entities": bool(canon.get("no_duplicate_entities")),
        "relationship_confidence_maintained": (company_out.get("confidence") or {}).get("relationship_confidence_maintained")
        is True
        or (company_out.get("confidence") or {}).get("confidence") is not None,
        "historical_edges_preserved": bool(company_out.get("historical_edges_preserved"))
        and snap.get("edge_count", 0) >= 1,
        "graph_traversal_reproducible": bool(path_out.get("reproducible"))
        and (path_out.get("paths") or []) == (path2.get("paths") or [])
        or bool(path_out.get("paths") is not None and path2.get("paths") is not None),
        "unsupported_edges_rejected": len(unsupported) == 0,
        "entity_resolution_collapses_aliases": bool(a and b and c)
        and a["canonical_id"] == b["canonical_id"] == c["canonical_id"] == "HDFCBANK",
        "company_pack_found": bool(company_out.get("found")),
        "flags": flags_dict().get("KNOWLEDGE_GRAPH") is True,
        "not_engine_redesign": bool(company_out.get("not_an_engine_redesign")),
    }
    # Fix reproducible check - paths should be equal
    checks["graph_traversal_reproducible"] = bool(path_out.get("reproducible")) and (
        [p.get("path") for p in (path_out.get("paths") or [])]
        == [p.get("path") for p in (path2.get("paths") or [])]
    )
    return {"passed": all(checks.values()), "checks": checks, "ikg_version": IKG_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    sample = analyse_company("HDFCBANK")
    gh = dash.get("graph_health") or {}
    rels = sample.get("relationships") or []
    rel_rows = "".join(
        f"<tr><td>{r.get('relation')}</td><td>{r.get('counterpart_label')}</td>"
        f"<td>{r.get('confidence')}</td><td>{'yes' if r.get('active') else 'hist'}</td></tr>"
        for r in rels[:15]
    )
    deps = sample.get("dependencies") or {}
    return f"""<!doctype html>
<html><head><title>IKG — Institutional Knowledge Graph</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Institutional Knowledge Graph</h1>
<p>Primary question: <em>{PRIMARY_QUESTION}</em></p>
<div class="card">
  <div>Version: {dash.get('ikg_version')}</div>
  <div>Nodes: {(gh.get('node_count'))} · Edges: {(gh.get('edge_count'))}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>HDFCBANK — relationship explorer</h2>
  <p>{(sample.get('report') or {}).get('executive_summary')}</p>
  <table><thead><tr><th>Relation</th><th>Counterpart</th><th>Confidence</th><th>State</th></tr></thead>
  <tbody>{rel_rows}</tbody></table>
</div>
<div class="card"><h2>Dependency map</h2>
  <div>Suppliers: {', '.join(deps.get('suppliers') or []) or '—'}</div>
  <div>Customers: {', '.join(deps.get('customers') or []) or '—'}</div>
  <div>Macro: {', '.join(deps.get('macro_drivers') or []) or '—'}</div>
  <div>Tech: {', '.join(deps.get('technology_exposure') or []) or '—'}</div>
  <p>{(sample.get('report') or {}).get('cio_brief')}</p>
</div>
<p>API: /v1/knowledge-graph/* · Flag: KNOWLEDGE_GRAPH · Permanent knowledge backbone</p>
</body></html>"""
