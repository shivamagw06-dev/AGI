from kip_v2.change_detection import detect_changes
from kip_v2.schema import Evidence, Fact


def _fact(category, key, value, period, doc="doc_1", confidence=0.7):
    ev = Evidence(document_id=doc, page=1, paragraph_id=f"{doc}:p0", snippet=f"Evidence for {key}: {value}")
    return Fact(
        fact_id=Fact.make_id("COMP_X", category, key, period, ev.evidence_hash),
        company_id="COMP_X", category=category, key=key, value=value, period=period,
        unit=None, currency=None, confidence=confidence, evidence=ev, source_document_id=doc,
    )


def test_new_risk_detected():
    old = [_fact("risks", "risks", "Currency risk is not material.", "FY25")]
    new = [_fact("risks", "risks", "Regulatory compliance risk in new markets is significant.", "FY26", doc="doc_2")]
    deltas = detect_changes("COMP_X", "FY25", "FY26", old, new)
    types = {d.change_type for d in deltas if d.category == "risks"}
    assert "new" in types
    assert "removed" in types


def test_unchanged_risk_not_reported_as_new_or_removed():
    text = "Regulatory compliance risk remains material for our operations this year."
    old = [_fact("risks", "risks", text, "FY25")]
    new = [_fact("risks", "risks", text, "FY26", doc="doc_2")]
    deltas = detect_changes("COMP_X", "FY25", "FY26", old, new)
    risk_deltas = [d for d in deltas if d.category == "risks"]
    assert risk_deltas == []


def test_capex_increase_detected():
    old = [_fact("financial_metric", "capex", 310.0, "FY25")]
    new = [_fact("financial_metric", "capex", 520.0, "FY26", doc="doc_2")]
    deltas = detect_changes("COMP_X", "FY25", "FY26", old, new)
    capex = [d for d in deltas if d.key == "capex"]
    assert len(capex) == 1
    assert capex[0].change_type == "increased"
    assert capex[0].magnitude_pct > 0


def test_debt_decrease_detected():
    old = [_fact("financial_metric", "debt", 1200.0, "FY25")]
    new = [_fact("financial_metric", "debt", 1050.0, "FY26", doc="doc_2")]
    deltas = detect_changes("COMP_X", "FY25", "FY26", old, new)
    debt = [d for d in deltas if d.key == "debt"]
    assert len(debt) == 1
    assert debt[0].change_type == "decreased"
    assert debt[0].magnitude_pct < 0


def test_small_metric_change_is_unchanged_and_not_reported():
    old = [_fact("financial_metric", "dividend_per_share", 8.00, "FY25")]
    new = [_fact("financial_metric", "dividend_per_share", 8.10, "FY26", doc="doc_2")]
    deltas = detect_changes("COMP_X", "FY25", "FY26", old, new)
    assert [d for d in deltas if d.key == "dividend_per_share"] == []


def test_new_metric_with_no_prior_period_reported_as_new():
    new = [_fact("financial_metric", "buyback", 100.0, "FY26", doc="doc_2")]
    deltas = detect_changes("COMP_X", "FY25", "FY26", [], new)
    buyback = [d for d in deltas if d.key == "buyback"]
    assert len(buyback) == 1 and buyback[0].change_type == "new"
