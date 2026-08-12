import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from cid import worker
from cid.persistence import generated_age_seconds


def test_generated_age_seconds():
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    row = {"generated_at": (now - timedelta(days=2)).isoformat()}
    assert generated_age_seconds(row, now=now) == 2 * 86400


def test_queue_skips_fresh_versions(monkeypatch):
    monkeypatch.setattr(worker, "warehouse_universe", lambda: ["INFY", "TCS"])
    monkeypatch.setattr(
        worker,
        "latest_versions",
        lambda: {
            "INFY": {"generated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    queue, fresh = worker.eligible_queue(refresh_days=30)
    assert queue == ["TCS"]
    assert fresh == 1


def test_worker_count_is_hard_capped_at_four(monkeypatch, tmp_path):
    monkeypatch.setenv("CID_DOSSIER_WORKERS", "20")
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(worker, "openai_status", lambda: {"enabled": True})
    monkeypatch.setattr(worker, "eligible_queue", lambda refresh_days: ([], 10))

    def stop_after_status(payload):
        if payload.get("status") == "idle":
            assert payload["workers"] == 4
            worker.STOP.set()

    worker.STOP.clear()
    monkeypatch.setattr(worker, "write_status", stop_after_status)
    worker.run_forever()
    worker.STOP.clear()
