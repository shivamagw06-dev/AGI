"""Unit and provider evidence must survive the historical-depth bridge."""

from institutional_warehouse.refresh import _statement_row


def test_statement_row_preserves_unit_and_document_provenance():
    record = {
        "period": "FY2026",
        "source": "financial_connector",
        "payload": {
            "statement": "income",
            "revenue": 123.4,
            "units_in": "inr_million",
            "provider": "nse_india",
            "parser_path": "nse_xbrl_fact",
            "source_document": "https://example.test/filing.xbrl",
        },
    }

    row = _statement_row("TCS", record, annual=True)

    assert row is not None
    assert row["units_in"] == "inr_million"
    assert row["statement_version"] == "nse_india:nse_xbrl_fact"
    assert row["source_document"] == "https://example.test/filing.xbrl"
