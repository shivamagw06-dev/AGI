from pathlib import Path

from macro_intelligence_engine import licensed_capiq


def test_parser_quarantines_zeros_and_never_publishes(monkeypatch):
    fixture = Path("/tmp/agi-macro-audit/India_Macroeconomics Overview.xlsx")
    if not fixture.exists():
        return
    monkeypatch.setattr(licensed_capiq, "WORKBOOK", fixture)
    result = licensed_capiq.parse_workbook()
    assert result["ok"] is True
    assert result["publish_allowed"] is False
    assert result["observation_rows"]
    assert len(result["forecast_rows"]) == 91
    assert all(row["value_numeric"] != 0 for row in result["observation_rows"])
    assert all(row["value_numeric"] != 0 for row in result["forecast_rows"])
    assert all(row["publish_allowed"] is False for row in result["forecast_rows"])
