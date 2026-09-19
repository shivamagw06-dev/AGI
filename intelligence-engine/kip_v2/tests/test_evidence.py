from kip_v2.evidence import validate_evidence, validate_fact
from kip_v2.schema import Evidence, Fact


def _make_fact(**overrides):
    evidence = overrides.pop("evidence", None) or Evidence(
        document_id="doc_1", page=3, paragraph_id="doc_1:p0",
        snippet="Revenue for FY25 was Rs. 4,250 crore, up from the prior year.",
    )
    defaults = dict(
        fact_id="f1", company_id="COMP_TEST", category="financial_metric", key="revenue",
        value=4250.0, period="FY25", unit="crore", currency="INR", confidence=0.8,
        evidence=evidence, source_document_id="doc_1",
    )
    defaults.update(overrides)
    return Fact(**defaults)


def test_valid_fact_passes_gate():
    fact = _make_fact()
    ok, errors = validate_fact(fact)
    assert ok is True
    assert errors == []


def test_fact_without_evidence_is_rejected():
    fact = _make_fact()
    fact.evidence = None
    ok, errors = validate_fact(fact)
    assert ok is False
    assert "evidence.missing" in errors


def test_fact_with_tampered_hash_is_rejected():
    fact = _make_fact()
    fact.evidence.evidence_hash = "0" * 64
    ok, errors = validate_fact(fact)
    assert ok is False
    assert "evidence.hash.mismatch" in errors


def test_fact_with_short_snippet_is_rejected():
    ev = Evidence(document_id="doc_1", page=1, paragraph_id="doc_1:p0", snippet="ok")
    fact = _make_fact(evidence=ev, source_document_id="doc_1")
    ok, errors = validate_fact(fact)
    assert ok is False
    assert "evidence.snippet.too_short" in errors


def test_fact_with_invalid_page_is_rejected():
    ev = Evidence(document_id="doc_1", page=0, paragraph_id="doc_1:p0", snippet="A sufficiently long snippet of text.")
    fact = _make_fact(evidence=ev)
    ok, errors = validate_fact(fact)
    assert ok is False
    assert "evidence.page.invalid" in errors


def test_fact_confidence_out_of_range_rejected():
    fact = _make_fact(confidence=1.4)
    ok, errors = validate_fact(fact)
    assert ok is False
    assert "fact.confidence.out_of_range" in errors


def test_fact_source_document_mismatch_rejected():
    fact = _make_fact(source_document_id="doc_other")
    ok, errors = validate_fact(fact)
    assert ok is False
    assert "fact.source_document_id.mismatch" in errors


def test_evidence_hash_is_deterministic():
    e1 = Evidence(document_id="doc_1", page=2, paragraph_id="doc_1:p1", snippet="Some snippet text here.")
    e2 = Evidence(document_id="doc_1", page=2, paragraph_id="doc_1:p1", snippet="Some snippet text here.")
    assert e1.evidence_hash == e2.evidence_hash
    ok, errors = validate_evidence(e1)
    assert ok is True and errors == []
