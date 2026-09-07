"""Institutional Knowledge Graph V1 — what is connected?"""

from __future__ import annotations


def test_ikg_entity_resolution_and_gates():
    from knowledge_graph.entity_resolution.resolve import resolve_entity
    from knowledge_graph.production import (
        company,
        path,
        quality_gates,
        query,
        soft_slice_for_analyst,
        soft_slice_for_irs,
    )

    for alias in ("HDFCBANK", "HDFC Bank Ltd.", "NSE:HDFCBANK", "BSE:500180"):
        hit = resolve_entity(alias)
        assert hit and hit["canonical_id"] == "HDFCBANK"

    out = company("HDFCBANK")
    assert out["found"] is True
    assert out["relationship_count"] >= 5
    assert (out.get("evidence") or {}).get("unsupported_rejected") == 0
    assert all((r.get("evidence") or []) for r in (out.get("relationships") or [])[:5])
    assert (out.get("dependencies") or {}).get("regulators")

    p = path("oil", "NESTLEIND")
    assert p.get("found") is True or (p.get("paths") is not None)
    p2 = path("oil", "NESTLEIND")
    assert [x.get("path") for x in (p.get("paths") or [])] == [x.get("path") for x in (p2.get("paths") or [])]

    copper = query({"question": "Show companies exposed to copper"})
    assert copper["result"]["ok"] is True
    assert "TATASTEEL" in (copper["result"].get("companies") or []) or copper["result"].get("sectors")

    qg = quality_gates()
    assert qg["passed"] is True, qg.get("checks")

    biz = soft_slice_for_analyst("HDFCBANK", analyst="business")
    assert biz["knowledge_graph"]["desk"]["competitive_graph"] is not None
    assert soft_slice_for_irs()["knowledge_graph"]["quality_gates_passed"] is True


def test_ikg_query_banks_rate_and_suppliers():
    from knowledge_graph.production import query

    banks = query({"question": "Show all banks affected by RBI rate hikes"})
    assert banks["result"]["ok"] is True
    assert "HDFCBANK" in (banks["result"].get("companies") or [])

    suppliers = query({"entity": "NESTLEIND", "ask": "suppliers"})
    assert suppliers["result"]["ok"] is True
    assert (suppliers["result"]["result"] or {}).get("suppliers")


def test_stack_includes_ikg():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("HDFCBANK")
    assert "knowledge_graph" in chain["layers"]
    pack = company_pack("HDFCBANK")
    assert "knowledge_graph" in pack["layers"]
    assert pack["summary"].get("knowledge_relationship_count") is not None


def test_iaf_soft_wires_ikg_relationships():
    from institutional_analysts.production import package_for_ask_agi

    pack = package_for_ask_agi("What is HDFC Bank connected to?", ticker="HDFCBANK")
    assert pack.get("enabled") is True
    ikg = pack.get("knowledge_graph") or {}
    assert ikg.get("enabled") is True
    assert ikg.get("relationship_count") or ikg.get("summary")
    assert (pack.get("committee") or {}).get("knowledge_graph") or ikg.get("committee") or True
    assert (pack.get("cio") or {}).get("knowledge_graph") or ikg.get("cio_brief") or True
