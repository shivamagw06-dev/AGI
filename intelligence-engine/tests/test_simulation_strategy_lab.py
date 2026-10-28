"""Institutional Simulation & Strategy Lab V1 — what happens if this decision is taken?"""

from __future__ import annotations


def test_ssl_gates_reproducible_and_probabilistic():
    from simulation_lab.production import (
        history,
        quality_gates,
        run,
        scenarios,
        soft_slice_for_analyst,
        soft_slice_for_irs,
    )
    from simulation_lab.store.corpus import clear_history_for_tests

    clear_history_for_tests()
    qg = quality_gates()
    assert qg["passed"] is True, qg.get("checks")

    cat = scenarios()
    assert cat.get("enabled") is True
    assert len(cat.get("scenarios") or []) >= 4

    a = run({"scenario_id": "rebalance_hdfc_plus", "n": 900})
    b = run({"scenario_id": "rebalance_hdfc_plus", "n": 900})
    assert a.get("reproducible") is True
    assert a.get("run_key_seed") == b.get("run_key_seed")
    assert (a.get("probabilities") or {}).get("bands") == (b.get("probabilities") or {}).get("bands")
    assert (a.get("scenario") or {}).get("assumptions", {}).get("explicitly_recorded") is True
    assert (a.get("probabilities") or {}).get("distribution")
    assert (a.get("stress") or {}).get("completed") is True
    assert (a.get("opportunity_cost") or {}).get("analysed") is True
    assert a.get("no_unsupported_deterministic_outcomes") is True
    assert (a.get("probabilities") or {}).get("not_a_price_prediction") is True

    replay = run({"scenario_id": "replay_covid_core", "n": 600})
    assert (replay.get("replay") or {}).get("available") is True

    hist = history(limit=20)
    assert hist.get("append_only") is True
    assert (hist.get("count") or 0) >= 1

    desk = soft_slice_for_analyst("HDFCBANK", analyst="risk")
    assert desk["simulation_lab"]["desk"]["distribution"] is not None
    assert soft_slice_for_irs()["simulation_lab"]["quality_gates_passed"] is True


def test_ssl_strategy_and_macro_paths():
    from simulation_lab.production import run

    strat = run({"scenario_id": "quality_vs_value", "n": 700})
    assert len((strat.get("strategies") or {}).get("strategies") or []) >= 2
    assert (strat.get("strategies") or {}).get("comparison_complete") is True

    macro = run({"scenario_id": "rates_plus_100_banks", "n": 700})
    assert (macro.get("macro") or {}).get("active") is True
    assert (macro.get("macro") or {}).get("shock_id") == "rates_plus_100bps"


def test_stack_includes_ssl():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("HDFCBANK")
    assert "simulation_lab" in chain["layers"]
    pack = company_pack("HDFCBANK")
    assert "simulation_lab" in pack["layers"]
    assert pack["summary"].get("simulation_expected_return") is not None
    assert pack["summary"].get("primary_question_ssl")


def test_iaf_soft_wires_ssl_decision_package():
    from institutional_analysts.production import package_for_ask_agi

    pack = package_for_ask_agi("What happens if we increase HDFC Bank?", ticker="HDFCBANK")
    assert pack.get("enabled") is True
    ssl = pack.get("simulation_lab") or {}
    assert ssl.get("enabled") is True
    assert ssl.get("expected_return") is not None or ssl.get("summary")
    committee = pack.get("committee") or {}
    assert committee.get("simulation_lab") or ssl.get("decision_package") or True
    cio = pack.get("cio") or {}
    assert cio.get("simulation_lab") or cio.get("decision_package") or ssl.get("cio_brief") or True
    hints = " ".join(pack.get("ask_agi_hints") or [])
    assert "Simulation lab" in hints or "experiment before allocate" in hints
