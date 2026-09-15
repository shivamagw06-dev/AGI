from kip_v2.knowledge_graph import company_node, graph_from_facts, node_id, slugify
from kip_v2.schema import Evidence, Fact


def _fact(category, key, value, extra=None):
    ev = Evidence(document_id="doc_1", page=1, paragraph_id="doc_1:p0", snippet=f"Evidence: {value}"[:500])
    return Fact(
        fact_id=Fact.make_id("COMP_X", category, key, "FY25", ev.evidence_hash),
        company_id="COMP_X", category=category, key=key, value=value, period="FY25",
        unit=None, currency=None, confidence=0.7, evidence=ev, source_document_id="doc_1", extra=extra or {},
    )


def test_slugify_produces_stable_ids():
    assert slugify("Suresh Iyer") == "suresh_iyer"
    assert node_id("person", "Suresh Iyer") == "person_suresh_iyer"
    assert node_id("person", "Suresh Iyer") == node_id("person", "suresh iyer")


def test_company_node_includes_sector_and_industry_edges():
    nodes, edges = company_node("COMP_X", "Aravali Chemicals", sector="Chemicals", industry="Specialty Chemicals")
    node_types = {n.node_type for n in nodes}
    assert {"company", "sector", "industry"} <= node_types
    relations = {e.relation for e in edges}
    assert {"belongs_to_sector", "belongs_to_industry"} <= relations


def test_executive_node_created_from_management_statement():
    fact = _fact("management_statement", "growth_priorities", "quote text", extra={"speaker": "Suresh Iyer", "title": "MD"})
    nodes, edges = graph_from_facts("COMP_X", [fact])
    exec_nodes = [n for n in nodes if n.node_type == "executive"]
    assert exec_nodes and exec_nodes[0].node_id == "person_suresh_iyer"
    assert any(e.relation == "works_at" for e in edges)


def test_customer_relationship_edge_created():
    fact = _fact("customers", "customers", "Our key customers include Tata Motors and Maruti Suzuki this year.")
    nodes, edges = graph_from_facts("COMP_X", [fact])
    customer_nodes = [n for n in nodes if n.node_type == "customer"]
    assert customer_nodes
    assert any(e.relation == "has_customer" for e in edges)


def test_graph_is_deduplicated():
    fact1 = _fact("management_statement", "growth_priorities", "quote 1", extra={"speaker": "Suresh Iyer"})
    fact2 = _fact("management_statement", "demand_outlook", "quote 2", extra={"speaker": "Suresh Iyer"})
    nodes, edges = graph_from_facts("COMP_X", [fact1, fact2])
    exec_nodes = [n for n in nodes if n.node_type == "executive"]
    assert len(exec_nodes) == 1
