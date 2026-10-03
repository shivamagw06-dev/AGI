"""Coverage matrix — operational view of why a company isn't ICC yet."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", "/tmp/cm_test_store")


def test_matrix_for_company_has_expected_columns():
    from coverage_matrix.matrix import COLUMNS, matrix_for_company

    row = matrix_for_company("RELIANCE")
    assert row["ok"] is True
    for col in COLUMNS:
        assert col in row
        assert isinstance(row[col], bool)
    assert "research_ready" in row
    assert row["source"] in {
        "institutional_coverage_factory",
        "institutional_knowledge_tables_fallback",
    }


def test_matrix_for_universe_bounded_scan():
    from coverage_matrix.matrix import matrix_for_universe

    out = matrix_for_universe(scope="nifty50", limit=3)
    assert out["ok"] is True
    assert out["scanned"] == 3
    assert out["universe_size"] == 50
    assert out["truncated"] is True
    assert len(out["rows"]) == 3


def test_fallback_never_reports_true_without_ikt_data():
    from coverage_matrix.matrix import _from_ikt
    from institutional_knowledge_tables.store import delete_company

    delete_company("CMTESTCO")
    row = _from_ikt("CMTESTCO")
    assert all(row[c] is False for c in ("financials", "shareholding", "corporate_actions"))
    assert row["research_ready"] is False
