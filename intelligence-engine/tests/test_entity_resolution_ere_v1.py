"""RQ1 Sprint 2 — Entity Resolution Engine regression tests."""

from entity_resolution.canonical_resolver import resolve_question
from entity_resolution.production import quality_gates
from entity_resolution.schema import CONFIDENCE_THRESHOLD


def test_hdfc_bank_canonical():
    row = resolve_question("HDFC Bank", {"use_cache": False})
    assert row["needs_clarification"] is False
    assert row["ticker"] == "HDFCBANK"
    assert row["entity_type"] == "Company"
    assert row["canonical_entity"]["canonical_name"] == "HDFC Bank Limited"
    assert float(row["confidence"]) >= CONFIDENCE_THRESHOLD
    assert row["research_blocked"] is False


def test_hdfc_bare_requires_clarification():
    row = resolve_question("HDFC", {"use_cache": False})
    assert row["needs_clarification"] is True
    assert row["research_blocked"] is True
    assert len(row["possible_matches"]) >= 3
    assert row["canonical_entity"] is None


def test_infosys_aliases():
    for q in ("INFY", "Infosys", "Infosys Limited"):
        row = resolve_question(q, {"use_cache": False})
        assert row["needs_clarification"] is False
        assert row["ticker"] == "INFY"


def test_nifty_it_is_sector_index_not_company():
    row = resolve_question("Nifty IT", {"use_cache": False})
    assert row["needs_clarification"] is False
    assert row["entity_type"] == "Sector Index"
    assert row["entity_type"] != "Company"


def test_banking_sector():
    row = resolve_question("Banking", {"use_cache": False})
    assert row["entity_type"] == "Sector"
    assert row["needs_clarification"] is False


def test_macro_and_commodities():
    assert resolve_question("Oil", {"use_cache": False})["entity_type"] == "Commodity"
    assert resolve_question("Brent", {"use_cache": False})["entity_type"] == "Commodity"
    assert resolve_question("Gold", {"use_cache": False})["entity_type"] == "Commodity"
    assert resolve_question("USDINR", {"use_cache": False})["entity_type"] == "Currency"


def test_portfolio_and_theme():
    assert resolve_question("My Portfolio", {"use_cache": False})["entity_type"] == "Portfolio"
    assert resolve_question("AI", {"use_cache": False})["entity_type"] == "Theme"
    assert resolve_question("Defence", {"use_cache": False})["entity_type"] == "Theme"


def test_tata_ambiguity():
    row = resolve_question("Tata", {"use_cache": False})
    assert row["needs_clarification"] is True
    assert len(row["possible_matches"]) >= 4


def test_context_resolves_icici_to_bank():
    row = resolve_question(
        "ICICI",
        {"prior_entity_id": "COMP_HDFCBANK", "use_cache": False},
    )
    assert row["needs_clarification"] is False
    assert row["ticker"] == "ICICIBANK"


def test_icici_alone_clarifies():
    row = resolve_question("ICICI", {"use_cache": False})
    assert row["needs_clarification"] is True


def test_relationships_attached_for_hdfc_bank():
    row = resolve_question("HDFC Bank", {"use_cache": False})
    rel = row.get("relationships") or {}
    assert isinstance(rel.get("peers"), list)
    assert row.get("knowledge_graph_linked") in {True, False}


def test_quality_gates_scale():
    gates = quality_gates()
    assert gates["total"] >= 1000
    assert gates["accuracy"] >= 0.99
    assert gates["ambiguity_flag_rate"] >= 0.99
    assert gates["avg_resolution_ms"] < 100  # generous CI bound; target 20ms locally
