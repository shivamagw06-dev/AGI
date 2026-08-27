from strategy_lab.validation_registry import evaluate


def _passed(*gates):
    return {gate: {"status": "PASSED", "receipt_id": f"receipt-{gate}"} for gate in gates}


def test_strategy_cannot_self_promote_without_evidence():
    result = evaluate("momentum", requested_lifecycle="PRODUCTION", evidence={})
    assert result["lifecycle"] == "EXPERIMENTAL"
    assert result["execution"] == "BLOCKED"
    assert result["automatic_demotion"] is True


def test_operational_requires_implementation_and_current_data():
    result = evaluate(
        "momentum",
        requested_lifecycle="OPERATIONAL",
        evidence=_passed("implementation", "data_freshness", "data_completeness"),
    )
    assert result["lifecycle"] == "OPERATIONAL"
    assert result["execution"] == "BLOCKED"


def test_stale_health_blocks_claims_and_execution_even_with_full_evidence():
    from strategy_lab.validation_registry import GATES

    result = evaluate(
        "momentum",
        requested_lifecycle="PRODUCTION",
        evidence=_passed(*GATES),
        health="STALE",
        health_reason="Latest market session is missing.",
    )
    assert result["lifecycle"] == "PRODUCTION"
    assert result["execution"] == "BLOCKED"
    assert result["historical_alpha_claims_allowed"] is False
    assert result["automatic_demotion"] is True

