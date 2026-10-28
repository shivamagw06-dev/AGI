from strategy_lab.contracts import InvestmentStage, RunManifest, capital_decision_for, content_hash, stage_assessment
from strategy_lab.definitions import all_definitions, definition
from strategy_lab.execution import IndiaCashCostSchedule, event_gate, simulate_order
from strategy_lab.point_in_time import total_return_series, universe_on, visible_observations
from strategy_lab.research import evaluate_factor, spearman, walk_forward_partitions


def test_definitions_are_versioned_unique_and_immutable_by_hash():
    rows = all_definitions()
    assert len(rows) == 14
    assert len({row.strategy_id for row in rows}) == len(rows)
    assert all(row.strategy_id.endswith(f"_v{row.version}") for row in rows)
    assert definition("relative_value_v1").definition_hash == definition("relative_value_v1").definition_hash


def test_formula_change_requires_a_new_hash():
    item = definition("relative_value_v1")
    changed = {**item.to_dict(include_hash=False), "signal_definition": {"formula": "different"}}
    assert content_hash(changed) != item.definition_hash


def test_run_manifest_binds_every_reproducibility_input():
    item = definition("quality_v1")
    manifest = RunManifest(
        strategy_id=item.strategy_id,
        strategy_version=item.version,
        definition_hash=item.definition_hash,
        code_commit="abc", dataset_hash="data", universe_hash="universe",
        feature_hash="features", corporate_action_hash="actions",
        cost_model_hash="cost", parameters_hash="parameters",
        start_date="2020-01-01", end_date="2025-12-31",
        information_cutoff=item.information_cutoff, created_at="2026-08-23T00:00:00Z",
    )
    assert manifest.run_id == manifest.run_id
    assert manifest.to_dict()["run_id"] == manifest.run_id


def test_capital_fails_closed_until_all_stages_and_declared_production():
    item = definition("momentum_v1")
    evidence = {gate: "PASSED" for _, gates in __import__("strategy_lab.contracts", fromlist=["STAGE_GATES"]).STAGE_GATES for gate in gates}
    assessed = stage_assessment(evidence)
    assert assessed["stage"] == InvestmentStage.PRODUCTION.value
    assert capital_decision_for(item, evidence)["decision"] == "BLOCKED"


def test_health_can_move_a_strategy_backward():
    assert stage_assessment({}, health="STALE")["stage"] == InvestmentStage.SUSPENDED.value
    assert stage_assessment({}, invalidated=True)["stage"] == InvestmentStage.INVALIDATED.value


def test_point_in_time_selects_only_known_latest_revision():
    rows = [
        {"company_id": "A", "metric_id": "revenue", "period_end": "2024-03-31", "available_from": "2024-05-20", "revision_id": "1", "value": 100},
        {"company_id": "A", "metric_id": "revenue", "period_end": "2024-03-31", "available_from": "2024-07-01", "revision_id": "2", "value": 110},
    ]
    assert visible_observations(rows, "2024-04-30") == []
    assert visible_observations(rows, "2024-06-01")[0]["value"] == 100
    assert visible_observations(rows, "2024-08-01")[0]["value"] == 110


def test_historical_universe_does_not_backfill_current_members():
    rows = [{"company_id": "DELISTED", "index_id": "NSE", "effective_from": "2019-01-01", "effective_to": "2021-06-30", "investable": True}]
    assert universe_on(rows, "2020-01-01", index_id="NSE") == ["DELISTED"]
    assert universe_on(rows, "2022-01-01", index_id="NSE") == []


def test_total_return_adds_cash_and_requires_corroboration_for_structural_actions():
    prices = [{"date": "2024-01-01", "close": 100}, {"date": "2024-01-02", "close": 50}]
    actions = [{"action_type": "split", "ex_date": "2024-01-02", "ratio": 2, "corroborated": True}]
    assert total_return_series(prices, actions)[-1]["period_total_return"] == 0


def test_factor_engine_reports_ic_and_deciles_without_claiming_validation():
    rows = [
        {"signal_date": "2024-01-01", "feature_id": "pe", "feature_value": value, "forward_return_21d": value / 100}
        for value in range(1, 21)
    ]
    result = evaluate_factor(rows, feature_id="pe")
    assert result["horizons"]["21d"]["mean_ic"] == 1.0
    assert result["validated"] is False


def test_execution_models_partial_fills_and_event_blocks():
    schedule = IndiaCashCostSchedule.conservative_research_default()
    result = simulate_order(
        {"order_id": "o1", "symbol": "ABC", "side": "BUY", "quantity": 100, "adv": 1000},
        [{"timestamp": "2026-08-23T09:15:01", "ask": 101, "ask_size": 30, "bid": 100, "bid_size": 30, "adv": 1000}],
        schedule=schedule,
    )
    assert result["status"] == "PARTIAL"
    assert event_gate([{"event_type": "earnings", "material": True}], {"mode": "block", "block": ["earnings"]})["allowed"] is False


def test_walk_forward_is_chronological():
    parts = walk_forward_partitions([f"2024-01-{day:02d}" for day in range(1, 11)])
    assert max(parts["train"]) < min(parts["validation"])
    assert max(parts["validation"]) < min(parts["test"])
