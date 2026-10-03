"""IKT Capital IQ seed — durability across ephemeral Render deploys.

Render's filesystem is ephemeral without a persistent disk (see
app/kip/persist.py). This seed re-derives the IKT company facts from the
committed capital_iq_exports/*.xlsx source files on every boot, so the
full Indian public-company dataset (~7,800+ unique tickers across the
three CapIQ exports) never depends on the mutable JSON-per-ticker store
surviving a redeploy. These tests validate the idempotent skip logic and
the seed's actual effect on a fresh store, without running the full
multi-minute ingestion in the default test suite.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["IKT_STORE_ROOT"] = "/tmp/ikt_seed_capital_iq_test_store"

from institutional_knowledge_tables import seed_capital_iq
from institutional_knowledge_tables.store import delete_company


def test_exports_directory_and_files_are_committed_to_the_repo():
    assert seed_capital_iq._EXPORTS_DIR.exists(), (
        f"capital_iq_exports/ missing at {seed_capital_iq._EXPORTS_DIR} — "
        "the seed cannot work without the committed source spreadsheets."
    )
    for filename in seed_capital_iq._FILES:
        path = seed_capital_iq._EXPORTS_DIR / filename
        assert path.exists(), f"missing committed export: {filename}"
        assert path.stat().st_size > 100_000, f"{filename} looks too small to be a real export"


def test_already_seeded_skips_without_touching_the_store():
    with mock.patch.object(seed_capital_iq, "_already_seeded", return_value=True):
        result = seed_capital_iq.seed_if_needed()
    assert result == {"ok": True, "skipped": True, "reason": "already_seeded"}


def test_force_bypasses_the_skip_check():
    """force=True must attempt ingestion even if _already_seeded() would
    normally skip — verified by mocking the actual (slow) ingest call so
    this test stays fast, and asserting it was invoked."""

    with mock.patch.object(seed_capital_iq, "_already_seeded", return_value=True):
        with mock.patch(
            "institutional_knowledge_tables.bulk_sheet.ingest_company_sheet",
            return_value={"ok": True, "resolved_count": 1, "unresolved_count": 0},
        ) as mocked_ingest:
            with mock.patch(
                "institutional_knowledge_tables.bulk_sheet.read_sheet_rows",
                return_value=mock.Mock(columns=["Ticker", "Company Name"]),
            ):
                result = seed_capital_iq.seed_if_needed(force=True)
    assert result["skipped"] is False
    assert mocked_ingest.called


def test_missing_exports_directory_reports_error_not_a_crash():
    with mock.patch.object(seed_capital_iq, "_EXPORTS_DIR", Path("/tmp/does_not_exist_capital_iq")):
        with mock.patch.object(seed_capital_iq, "_already_seeded", return_value=False):
            result = seed_capital_iq.seed_if_needed()
    assert result["ok"] is False
    assert result["error"] == "capital_iq_exports_dir_missing"


def test_min_expected_companies_threshold_is_realistic():
    """The skip threshold must be well below the real ~7,800-company
    3-file corpus (so a genuinely completed prior seed is recognized),
    above the old 2-file corpus (~2,027 — so a deploy that only has the
    first two files still re-seeds once the third lands), and well above
    zero/a handful of unrelated test tickers (so a fresh/wiped disk is
    not mistaken for already-seeded)."""

    assert 3000 <= seed_capital_iq._MIN_EXPECTED_COMPANIES <= 7000
    assert len(seed_capital_iq._FILES) == 3
    assert "capiq_export_7000.xlsx" in seed_capital_iq._FILES


def test_already_seeded_reflects_real_store_state():
    for t in ("SEEDTEST1", "SEEDTEST2"):
        delete_company(t)
    assert seed_capital_iq._already_seeded() is False

    from institutional_knowledge_tables.store import upsert_fact

    upsert_fact("SEEDTEST1", "company_master", "company_name", "Seed Test One", source="test")
    assert seed_capital_iq._already_seeded() is False  # still far below threshold
    delete_company("SEEDTEST1")
