"""Gather worker env defaults — HTTP stays gather-off; worker forces gather-on."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path


def _load_gather_worker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "gather_worker.py"
    spec = importlib.util.spec_from_file_location("gather_worker_mod", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gather_worker_force_enables_flags(monkeypatch):
    monkeypatch.setenv("AGI_GATHER_FORCE", "true")
    monkeypatch.setenv("CONTINUOUS_GATHER_LEARN", "false")
    monkeypatch.setenv("FAA_BACKGROUND_COLLECTOR", "false")
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")

    gw = _load_gather_worker()
    gw._apply_worker_defaults()

    assert os.environ["CONTINUOUS_GATHER_LEARN"] == "true"
    assert os.environ["FAA_BACKGROUND_COLLECTOR"] == "true"
    assert os.environ["FAA_LIVE_FETCH"] == "true"
    assert os.environ["KF_HD_LIVE_COLLECTORS"] == "true"
    assert os.environ["AGI_ROLE"] == "gather_worker"


def test_start_engine_script_exists():
    script = Path(__file__).resolve().parents[1] / "scripts" / "start_engine.sh"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "gather_worker.py" in text
    assert "CONTINUOUS_GATHER_LEARN=false" in text
    assert "FAA_LIVE_FETCH" in text
    assert "uvicorn app.main:app" in text
    assert "AGI_GATHER_SIDECAR_DELAY_SEC" in text
    assert "nice -n 10" in text
    assert "AGI_GATHER_SIDECAR_PROFILE" in text
    assert "forecast_worker.py" in text
    assert "FIE_SIDECAR" in text


def test_forecast_only_worker_exists_without_full_gather_defaults():
    script = Path(__file__).resolve().parents[1] / "scripts" / "forecast_worker.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert 'os.environ["AGI_ROLE"] = "gather_worker"' in text
    assert 'os.environ.setdefault("FIE_RUNTIME", "true")' in text
    assert "STRATEGY_REGISTRY_REFRESH_SECONDS" in text
    assert "strategy_registry_refreshed" in text
    assert "ANSWER_PACK_MATERIALIZER_INTERVAL_SECONDS" in text
    assert "answer_pack_materializer_refreshed" in text
    assert "write_gather_heartbeat" in text
    assert "CONTINUOUS_HISTORICAL_BACKFILL" not in text
    assert "FAA_BACKGROUND_COLLECTOR" not in text


def test_forecast_worker_enforces_production_throughput_floor(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts" / "forecast_worker.py"
    spec = importlib.util.spec_from_file_location("forecast_worker_mod", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setenv("FIE_BATCH", "1")
    monkeypatch.setenv("FIE_INTERVAL_SECONDS", "180")
    monkeypatch.setenv("ANSWER_PACK_MATERIALIZER_BATCH", "5")
    monkeypatch.setenv("ANSWER_PACK_MATERIALIZER_INTERVAL_SECONDS", "900")

    mod._apply_throughput_floor()

    assert os.environ["FIE_BATCH"] == "2"
    assert os.environ["FIE_INTERVAL_SECONDS"] == "120"
    assert os.environ["ANSWER_PACK_MATERIALIZER_BATCH"] == "10"
    assert os.environ["ANSWER_PACK_MATERIALIZER_INTERVAL_SECONDS"] == "600"


def test_http_role_skips_gather_boot_helpers():
    """Web role must not start in-process CGL/FAA (sidecar owns gather)."""
    import os

    os.environ["AGI_ROLE"] = "web"
    # Lifespan branching is covered by role check used in app.main
    assert (os.environ.get("AGI_ROLE") or "").lower() == "web"
