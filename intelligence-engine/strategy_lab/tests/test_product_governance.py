from strategy_lab.governance_view import PRODUCT_STRATEGY_ALIASES, governance_for


def test_every_product_alias_is_mapped_and_fail_closed():
    for product_id in PRODUCT_STRATEGY_ALIASES:
        record = governance_for(product_id)
        assert record["mapped"] is True
        assert record["stage"] == "DEFINED"
        assert record["declared_status"] == "RESEARCH_ONLY"
        assert record["capital_allowed"] is False
        assert record["alpha_claims_permitted"] is False


def test_unknown_product_cannot_claim_governance_or_capital():
    record = governance_for("unknown_product")
    assert record["mapped"] is False
    assert record["stage"] == "UNMAPPED"
    assert record["evidence_status"] == "MAPPING_REQUIRED"
    assert record["capital_allowed"] is False
