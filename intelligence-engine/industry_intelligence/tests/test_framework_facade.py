from industry_intelligence.framework import coverage_report, framework_for


def test_bank_framework_combines_economics_and_underwriting():
    out = framework_for("banking")
    assert out["status"] == "COMPLETE"
    assert out["industry_key"] == "banks"
    assert "nim" in out["kpis"]["required"]
    assert "residual_income" in out["valuation"]["methods"]
    assert out["business_model"]["revenue_drivers"]
    assert out["causal_context"]["why_roic"]
    assert out["fabricated"] is False


def test_cross_registry_alias_is_governed():
    out = framework_for("consumer internet")
    assert out["industry_key"] == "internet_platforms"
    assert out["classification"]["sector_framework_key"] == "consumer_internet"
    assert out["coverage"]["industry_dna"] is True


def test_missing_industry_fails_closed():
    out = framework_for("interplanetary teleportation")
    assert out["status"] == "INDUSTRY_UNAVAILABLE"
    assert out["fabricated"] is False


def test_coverage_report_exposes_partial_layers():
    report = coverage_report()
    assert report["industries"] >= 36
    assert report["complete"] >= 27
    assert report["partial"] > 0
    assert report["fabricated"] is False
