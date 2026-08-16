from __future__ import annotations


def test_completed_phases_seed_editable_missing_data_matrix(monkeypatch, tmp_path):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db
    db.reset_backend()

    from institutional_warehouse.sector_evidence import sync
    from institutional_warehouse.production import sheet

    result = sync()
    assert result["ok"] is True
    assert result["requirements"] > 2_000
    page = sheet("sector_evidence_matrix", limit=5)
    assert page["total"] == result["requirements"]
    assert {row["phase"] for row in sheet("sector_evidence_matrix", limit=5000)["rows"]} == {
        "Phase 1 - Financials", "Phase 2 - Technology", "Phase 3 - Consumer",
        "Phase 4 - Industrials", "Phase 5 - Energy",
    }
    assert all(row["status"] in {"SUPPORTED", "DATA_REQUIRED"} for row in page["rows"])
    assert all(row["company_name"] for row in page["rows"])
    assert all(row["metric_label"] and row["definition"] for row in page["rows"])
    assert all(row["expected_unit"] and row["source_guidance"] for row in page["rows"])


def test_sync_does_not_overwrite_manual_evidence(monkeypatch, tmp_path):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    from institutional_warehouse import db
    db.reset_backend()

    from institutional_warehouse.sector_evidence import sync
    from institutional_warehouse.production import edit, sheet

    sync()
    row = sheet("sector_evidence_matrix", limit=1)["rows"][0]
    result = edit("sector_evidence_matrix", [
        {"row_id": row["row_id"], "column": "value", "value": 123.45},
        {"row_id": row["row_id"], "column": "status", "value": "PARTIAL"},
        {"row_id": row["row_id"], "column": "source", "value": "manual primary filing"},
    ], actor="admin", recalc=False)
    assert result["applied"] == 3

    sync()
    current = sheet("sector_evidence_matrix", limit=1)["rows"][0]
    assert current["value"] == 123.45
    assert current["status"] == "PARTIAL"
    assert current["source"] == "manual primary filing"
