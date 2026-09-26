from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from app.faa import background
from app.faa.background import due_mode, run_collector_once, schedule_status


IST = ZoneInfo("Asia/Kolkata")


def setup_function():
    background._LAST_RUN_DATE.clear()


def test_nightly_window_is_one_am_ist_once_per_date():
    now = datetime(2026, 8, 16, 1, 15, tzinfo=IST)
    assert due_mode(now) == "nightly"
    background._LAST_RUN_DATE["nightly"] = "2026-08-16"
    assert due_mode(now) is None


def test_evening_filings_window_is_separate():
    now = datetime(2026, 8, 16, 18, 5, tzinfo=IST)
    assert due_mode(now) == "evening_filings"
    background._LAST_RUN_DATE["evening_filings"] = "2026-08-16"
    assert due_mode(now) is None


def test_collector_passes_bounded_mode_configuration():
    faa = MagicMock()
    faa.refresh_snapshots.return_value = {"ok": True}
    with patch.dict("os.environ", {"FAA_EVENING_LIMIT": "2", "FAA_EVENING_MAX_RUNTIME_SEC": "900"}):
        result = run_collector_once(faa, mode="evening_filings")
    assert result["ok"] is True
    faa.refresh_snapshots.assert_called_once_with(
        limit_per_query=2,
        mode="evening_filings",
        max_runtime_sec=900,
    )


def test_schedule_status_documents_operational_windows():
    status = schedule_status()
    assert status["timezone"] == "Asia/Kolkata"
    assert status["nightly"]["hour"] == 1
    assert status["nightly"]["window_minutes"] == 60
    assert status["evening_filings"]["hour"] == 18
