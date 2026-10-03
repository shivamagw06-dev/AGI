from strategy_lab.prospective import CONFIRMATION, _availability


def test_legacy_fact_is_available_when_agi_observed_it_not_at_period_end():
    row = {
        "period_end": "2019-03-31",
        "filing_date": "2019-05-20",
        "sys_created_at": "2026-08-22T11:06:22+00:00",
        "sys_updated_at": "2026-08-22T11:06:22+00:00",
    }
    assert _availability(row) == "2026-08-22T11:06:22+00:00"


def test_capture_confirmation_is_a_deliberate_literal():
    assert CONFIRMATION == "CAPTURE_PROSPECTIVE_EVIDENCE"
