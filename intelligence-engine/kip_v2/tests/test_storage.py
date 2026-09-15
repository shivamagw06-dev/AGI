from kip_v2.schema import Evidence, Fact, GraphEdge, GraphNode, Paragraph


def _fact(document_id="doc_1", page=1, snippet="A sufficiently long evidence snippet.", confidence=0.7):
    evidence = Evidence(document_id=document_id, page=page, paragraph_id=f"{document_id}:p0", snippet=snippet)
    return Fact(
        fact_id=Fact.make_id("COMP_X", "risks", "risks", "FY25", evidence.evidence_hash),
        company_id="COMP_X", category="risks", key="risks", value=snippet, period="FY25",
        unit=None, currency=None, confidence=confidence, evidence=evidence, source_document_id=document_id,
    )


def test_store_fact_gate_rejects_invalid_and_records_rejection(store):
    bad = _fact()
    bad.evidence = None
    ok, errors = store.store_fact(bad)
    assert ok is False
    assert errors
    assert store.stats()["rejections"] == 1
    assert store.get_facts("COMP_X") == []


def test_store_fact_accepts_valid_fact_and_is_queryable(store):
    good = _fact()
    ok, errors = store.store_fact(good)
    assert ok is True and errors == []
    facts = store.get_facts("COMP_X", category="risks")
    assert len(facts) == 1
    assert facts[0].fact_id == good.fact_id
    assert facts[0].evidence.snippet == good.evidence.snippet


def test_paragraph_idempotent_storage(store):
    p = Paragraph(
        paragraph_id="doc_1:p0", document_id="doc_1", company_id="COMP_X", section="general",
        page=1, index=0, text="Some paragraph text that is long enough to matter.",
    )
    assert store.store_paragraph(p) is True
    assert store.store_paragraph(p) is False  # same evidence_hash -> no-op
    assert len(store.list_paragraphs("doc_1")) == 1


def test_supersede_fact_marks_old_archived(store):
    old = _fact(document_id="doc_old")
    new = _fact(document_id="doc_new", snippet="A different but also sufficiently long snippet.")
    store.store_fact(old)
    store.store_fact(new)
    store.supersede_fact(old.fact_id, new.fact_id)
    archived = store.get_fact(old.fact_id)
    assert archived.status == "archived"
    assert archived.superseded_by == new.fact_id
    active = store.get_facts("COMP_X", category="risks")
    assert old.fact_id not in {f.fact_id for f in active}


def test_graph_upsert_and_query(store):
    store.upsert_node(GraphNode(node_id="company_x", node_type="company", name="Company X"))
    store.upsert_node(GraphNode(node_id="person_a", node_type="executive", name="A"))
    store.upsert_edge(GraphEdge(edge_id="e1", source_id="person_a", target_id="company_x", relation="works_at"))
    nodes, edges = store.get_graph("company_x")
    assert {n.node_id for n in nodes} == {"company_x", "person_a"}
    assert len(edges) == 1


def test_stats_reports_counts(store):
    store.store_fact(_fact())
    stats = store.stats()
    assert stats["facts_active"] == 1
    assert stats["backend"] == "sqlite"
