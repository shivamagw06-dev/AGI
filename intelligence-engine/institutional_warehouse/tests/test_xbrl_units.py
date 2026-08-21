"""What an XBRL fact declares, and what it must refuse to guess.

The fixtures mirror the units actually present in the 113 NSE filings on disk,
plus the cases those filings do not contain and which must fail closed.
"""

from __future__ import annotations

import pytest

from institutional_warehouse import xbrl_units as xu

# The unit block as NSE actually files it.
UNITS_DOC = """
<xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>
<xbrli:unit id="pure"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>
<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>
<xbrli:unit id="INRPerShare"><xbrli:divide>
  <xbrli:unitNumerator><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unitNumerator>
  <xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>
</xbrli:divide></xbrli:unit>
<xbrli:unit id="USD"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
"""


@pytest.fixture
def units():
    return xu.parse_units(UNITS_DOC)


def test_the_declared_units_are_read(units):
    assert units["INR"]["kind"] == xu.CURRENCY and units["INR"]["currency"] == "INR"
    assert units["shares"]["kind"] == xu.SHARES
    assert units["pure"]["kind"] == xu.PURE
    assert units["INRPerShare"]["kind"] == xu.COMPOUND


# --- the correction: decimals is precision, never scale -------------------

def test_decimals_does_not_scale_the_value(units):
    """Reliance's real filing: unitRef=INR decimals=-7 value=2407150000000.00.

    Read as a scale factor, -7 would turn 2.4 trillion rupees into 240,715 -
    which reads as an ordinary figure in crore and is wrong by ten million.
    """
    fact = {"unitRef": "INR", "decimals": "-7", "raw_value": "2407150000000.00"}
    out = xu.resolve(fact, units)
    assert out["usable_as_money"] is True
    assert out["normalised_value"] == pytest.approx(2_407_150.0)   # INR million
    assert out["decimals"] == "-7", "recorded as precision"


def test_changing_decimals_cannot_change_the_result(units):
    """The property that makes the rule enforceable rather than a comment."""
    base = {"unitRef": "INR", "raw_value": "2407150000000.00"}
    values = {xu.resolve({**base, "decimals": d}, units)["normalised_value"]
              for d in ("-7", "-6", "-4", "0", "2", "INF", None)}
    assert len(values) == 1, "decimals must not participate in any arithmetic"


def test_decimals_inf_is_not_a_scale_signal(units):
    out = xu.resolve({"unitRef": "INR", "decimals": "INF", "raw_value": "1000000.0"}, units)
    assert out["normalised_value"] == pytest.approx(1.0)


# --- fail closed ----------------------------------------------------------

def test_a_compound_unit_is_not_an_aggregate(units):
    """INRPerShare carries EPS in every money filing surveyed."""
    out = xu.resolve({"unitRef": "INRPerShare", "decimals": "INF", "raw_value": "28.01"}, units)
    assert out["usable_as_money"] is False
    assert out["reason"] == "compound_unit_is_not_an_aggregate"
    assert out["normalised_value"] is None


def test_shares_and_ratios_are_not_money(units):
    for ref, why in (("shares", "shares_is_not_money"), ("pure", "pure_is_not_money")):
        out = xu.resolve({"unitRef": ref, "raw_value": "1234"}, units)
        assert out["usable_as_money"] is False and out["reason"] == why


def test_a_missing_unitref_fails_closed(units):
    out = xu.resolve({"raw_value": "5000"}, units)
    assert out["usable_as_money"] is False and out["reason"] == "missing_unitRef"


def test_an_undeclared_unitref_fails_closed_rather_than_defaulting(units):
    out = xu.resolve({"unitRef": "LAKHS", "raw_value": "5000"}, units)
    assert out["usable_as_money"] is False
    assert out["reason"].startswith("unitRef_not_declared")


def test_a_foreign_currency_fails_closed(units):
    out = xu.resolve({"unitRef": "USD", "raw_value": "5000"}, units)
    assert out["usable_as_money"] is False
    assert out["reason"] == "currency_not_supported:USD"


def test_inline_xbrl_scale_fails_closed_until_supported(units):
    """No NSE filing surveyed is inline, so scale is refused rather than guessed."""
    out = xu.resolve({"unitRef": "INR", "scale": "6", "raw_value": "2.4"}, units)
    assert out["usable_as_money"] is False
    assert out["reason"] == "inline_xbrl_scale_not_supported"


def test_conflicting_unit_metadata_does_not_resolve_to_a_guess(units):
    """A fact naming one unit while carrying an inline scale is contradictory."""
    out = xu.resolve({"unitRef": "INR", "scale": "3", "decimals": "-7",
                      "raw_value": "1000"}, units)
    assert out["usable_as_money"] is False


def test_a_non_numeric_value_fails_closed(units):
    assert xu.resolve({"unitRef": "INR", "raw_value": "n/a"}, units)["reason"] == "value_not_numeric"


# --- values ---------------------------------------------------------------

def test_a_negative_value_keeps_its_sign(units):
    out = xu.resolve({"unitRef": "INR", "decimals": "-7", "raw_value": "-263589000.00"}, units)
    assert out["normalised_value"] == pytest.approx(-263.589)


def test_the_transformation_is_recorded_so_it_can_be_rechecked(units):
    out = xu.resolve({"unitRef": "INR", "decimals": "-7", "raw_value": "2407150000000.00"}, units)
    assert out["raw_value"] == "2407150000000.00"
    assert out["scale_factor"] == xu.RUPEES_TO_MILLION
    assert [t["step"] for t in out["transform"]] == ["unit_resolved", "to_inr_million"]
    replayed = float(out["raw_value"])
    for step in out["transform"]:
        if "factor" in step:
            replayed *= step["factor"]
    assert replayed == pytest.approx(out["normalised_value"]), "transform must replay"


def test_inline_detection(units):
    assert xu.is_inline_xbrl("<ix:nonFraction scale='6'>2.4</ix:nonFraction>") is True
    assert xu.is_inline_xbrl("<xbrli:xbrl>...</xbrli:xbrl>") is False


def test_it_resolves_against_a_real_filing_on_disk():
    """Guards the regexes against the shape NSE actually files."""
    import glob
    paths = glob.glob("financial_statements_engine/data/raw/*/*.xbrl")
    if not paths:
        pytest.skip("no sample filings available")
    doc = open(paths[0], encoding="utf-8", errors="replace").read()
    units = xu.parse_units(doc)
    assert units.get("INR", {}).get("currency") == "INR"
    assert units.get("INRPerShare", {}).get("kind") == xu.COMPOUND
    assert xu.is_inline_xbrl(doc) is False, "these filings are plain XBRL"


# --- the shadow pass ------------------------------------------------------

def test_the_shadow_applies_nothing_and_says_so():
    from institutional_warehouse import xbrl_shadow as sh
    doc = ('<xbrli:xbrl>' + UNITS_DOC + '<in-bse-fin:Revenue contextRef="OneD"'
           ' unitRef="INR" decimals="-7">2407150000000.00</in-bse-fin:Revenue></xbrli:xbrl>')
    out = sh.scan_document(doc, filing_url="u", provider="nse_india", company="ACME")
    fact = out["facts"][0]
    assert fact["applied"] is False
    assert fact["proposed_normalised_value"] == pytest.approx(2_407_150.0)
    assert fact["raw_value"] == "2407150000000.00", "the raw value is preserved"
    assert fact["decimals"] == "-7"
    assert fact["filing_sha256"] and fact["provider"] == "nse_india"


def test_lineage_is_confirmed_only_by_an_exact_value_match():
    from institutional_warehouse import xbrl_shadow as sh
    doc = ('<xbrli:xbrl>' + UNITS_DOC + '<in-bse-fin:RevenueFromOperations'
           ' contextRef="OneD" unitRef="INR" decimals="-7">580520000000.00'
           '</in-bse-fin:RevenueFromOperations></xbrli:xbrl>')
    index = sh.index_declared_facts([sh.scan_document(doc, company="TCS")])

    rows = [{"row_id": "a", "symbol": "TCS", "source": "financial_connector",
             "revenue": 580520000000.0},                       # exact match
            {"row_id": "b", "symbol": "TCS", "source": "yahoo_finance_statements",
             "revenue": 580520.0},                             # already in millions
            {"row_id": "c", "symbol": "OTHER", "source": "x",
             "revenue": 580520000000.0}]                       # different company
    out = sh.confirm_lineage(rows, index, fields=["revenue"])
    assert out["confirmed_rows"] == 1
    assert "a" in out["rows"], "only the row whose value is the filing fact"
    assert "b" not in out["rows"], "an already-scaled row must not be claimed"


def test_a_document_with_no_declared_units_yields_nothing_usable():
    """Nine such documents sit in the sample corpus: 2.6KB stubs with toy values."""
    from institutional_warehouse import xbrl_shadow as sh
    doc = ('<xbrli:xbrl><in-bse-fin:RevenueFromOperations contextRef="OneD"'
           ' unitRef="INR" decimals="2">400.00</in-bse-fin:RevenueFromOperations></xbrli:xbrl>')
    out = sh.scan_document(doc, company="TCS")
    assert all(f["proposed_normalised_value"] is None for f in out["facts"])
    assert out["counts"]["unknown_fails_closed"] >= 1
