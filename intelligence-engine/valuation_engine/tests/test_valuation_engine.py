"""Unified Valuation Engine contract."""

from __future__ import annotations

import pytest

from institutional_warehouse import units
from valuation_engine import attribution, engine, graph, service


def _record(**overrides):
    """A warehouse record as production.read_company returns one."""
    record = {
        "ok": True,
        "symbol": "AAA",
        "master": {"company_name": "Alpha", "sector": "Industrials", "industry": "machinery"},
        "latest_price": {
            "close": 100.0, "shares_outstanding": 1_000_000.0, "dividend": 2.0,
            "source": "groww", "_meta": {"updated_at": "2026-08-04T09:00:00Z", "version": 3},
        },
        # Aggregates in INR million, as the warehouse stores them.
        "latest_annual": {
            "revenue": 5_000.0, "ebitda": 1_000.0, "pat": 500.0, "equity": 2_000.0,
            "debt": 800.0, "cash": 300.0, "eps": 5.0, "book_value": 20.0,
            "source": "upstox_fundamentals",
            "_meta": {"updated_at": "2026-07-01T00:00:00Z", "reported_unit": "crore"},
        },
        "consensus": {"target_price": 130.0, "source": "capital_iq", "_meta": {}},
        "ratios": {},
    }
    record.update(overrides)
    return record


# -- dependency graph ------------------------------------------------------


def test_computation_order_never_precedes_a_dependency():
    order = graph.topological()
    seen: set[str] = set()
    for node in order:
        for dependency in graph.inputs_of(node):
            assert dependency in seen, f"{node} computed before {dependency}"
        seen.add(node)


def test_a_price_tick_only_dirties_downstream_nodes():
    dirty = set(graph.dependents_of("cmp"))
    assert {"market_cap", "enterprise_value", "pe", "pb", "dividend_yield"} <= dirty
    # A quote refresh must not invalidate statement inputs that did not move.
    assert "revenue" not in dirty
    assert "ebitda" not in dirty
    assert "shares_outstanding" not in dirty


def test_recompute_after_price_skips_untouched_inputs():
    values = engine.recompute_after(_record(), "cmp")
    assert "market_cap" in values
    assert "revenue" not in values


# -- computation -----------------------------------------------------------


def test_multiples_are_computed_in_one_scale():
    values = engine.compute(_record())
    # 100 x 1,000,000 shares
    assert values["market_cap"].value == pytest.approx(100_000_000.0)
    # market cap + debt - cash, aggregates converted from INR million
    assert values["enterprise_value"].value == pytest.approx(
        100_000_000.0 + (800.0 - 300.0) * units.MILLION
    )
    assert values["pe"].value == pytest.approx(20.0)     # 100 / 5
    assert values["pb"].value == pytest.approx(5.0)      # 100 / 20
    assert values["ev_ebitda"].value == pytest.approx(
        (100_000_000.0 + 500 * units.MILLION) / (1_000.0 * units.MILLION)
    )
    assert values["roe"].value == pytest.approx(25.0)    # 500 / 2,000
    assert values["dividend_yield"].value == pytest.approx(2.0)
    assert values["upside"].value == pytest.approx(30.0)


def test_a_missing_value_names_the_input_it_lacked():
    record = _record()
    record["latest_annual"] = {**record["latest_annual"], "ebitda": None}
    values = engine.compute(record)
    ev_ebitda = values["ev_ebitda"]
    assert ev_ebitda.value is None
    assert "ebitda" in ev_ebitda.missing
    assert "needs ebitda" in ev_ebitda.note


def test_negative_earnings_do_not_produce_a_pe():
    """A loss-making company has no meaningful P/E; it must not render as one."""
    record = _record()
    record["latest_annual"] = {**record["latest_annual"], "eps": -4.0}
    values = engine.compute(record)
    assert values["pe"].value is None
    assert values["pe"].note == "earnings not positive"


def test_every_value_carries_its_sources():
    values = engine.compute(_record())
    assert "groww" in values["market_cap"].sources
    assert "upstox_fundamentals" in values["ev_ebitda"].sources
    assert "capital_iq" in values["upside"].sources


# -- service layer ---------------------------------------------------------


def test_company_valuation_answers_in_one_call():
    out = service.get_company_valuation("AAA", record=_record())
    assert out["ok"] is True
    for block in ("metrics", "context", "coverage", "provenance", "lens"):
        assert block in out


def test_provenance_is_read_from_metadata_not_hardcoded():
    out = service.get_company_valuation("AAA", record=_record())
    prov = out["provenance"]
    assert prov["price"]["source"] == "groww"
    assert prov["financials"]["source"] == "upstox_fundamentals"
    assert prov["financials"]["reported_unit"] == "crore"
    assert prov["price"]["version"] == 3
    assert prov["formula_version"] == service.VERSION


def test_sector_context_uses_peers_and_history():
    peers = [{"pe": 15.0}, {"pe": 25.0}, {"pe": 30.0}]
    history = [{"pe": v} for v in (10.0, 12.0, 14.0, 18.0, 22.0)]
    out = service.get_company_valuation("AAA", record=_record(), peers=peers, history=history)
    pe_context = out["context"]["pe"]
    assert pe_context["sector_median"] == pytest.approx(25.0)
    assert pe_context["premium_pct"] == pytest.approx(-20.0)  # 20 vs 25
    assert pe_context["historical_percentile"] is not None


def test_coverage_counts_only_metrics_that_apply():
    out = service.get_company_valuation("AAA", record=_record())
    coverage = out["coverage"]
    assert coverage["available"] > 0
    assert coverage["applicable"] >= coverage["available"]
    assert 0 <= coverage["pct"] <= 100


def test_a_bank_hides_enterprise_multiples():
    """A bank has no conventional enterprise value; showing one would be noise."""
    record = _record()
    record["master"] = {**record["master"], "industry": "banks", "sector": "Financials"}
    out = service.get_company_valuation("AAA", record=record)
    assert out["metrics"]["ev_ebitda"]["meaningful"] is False
    assert out["metrics"]["pb"]["meaningful"] is True


# -- valuation change log --------------------------------------------------


def test_a_price_move_alone_is_attributed_to_price():
    before = {"pe": 18.4, "cmp": 100.0, "eps": 5.435}
    after = {"pe": 17.9, "cmp": 97.28, "eps": 5.435}
    out = attribution.explain_change("pe", before, after)
    assert [d["input"] for d in out["drivers"]] == ["cmp"]
    assert "eps" in out["unchanged"]
    assert "cmp declined" in out["summary"]


def test_a_balance_sheet_move_is_attributed_to_the_balance_sheet():
    before = {"enterprise_value": 1000.0, "market_cap": 900.0, "debt": 200.0, "cash": 100.0}
    after = {"enterprise_value": 900.0, "market_cap": 900.0, "debt": 150.0, "cash": 150.0}
    out = attribution.explain_change("enterprise_value", before, after)
    drivers = {d["input"] for d in out["drivers"]}
    assert drivers == {"debt", "cash"}
    assert "market_cap" in out["unchanged"]


def test_noise_is_not_narrated_as_a_cause():
    before = {"pe": 18.40, "cmp": 100.0, "eps": 5.435}
    after = {"pe": 18.41, "cmp": 100.05, "eps": 5.435}
    out = attribution.explain_change("pe", before, after)
    assert out["drivers"] == []
    assert "effectively unchanged" in out["summary"]


def test_change_log_ranks_the_biggest_moves_first():
    before = {"pe": 20.0, "cmp": 100.0, "eps": 5.0, "pb": 5.0, "book_value_per_share": 20.0}
    after = {"pe": 10.0, "cmp": 50.0, "eps": 5.0, "pb": 2.5, "book_value_per_share": 20.0}
    log = attribution.change_log(before, after)
    assert log["changed"] == 2
    assert abs(log["entries"][0]["change_pct"]) >= abs(log["entries"][1]["change_pct"])


def test_health_reports_the_contract():
    out = service.health()
    assert out["reads"] == "institutional_warehouse"
    assert "pe" in out["metrics"]
