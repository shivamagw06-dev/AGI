"""KAIP runtime configuration — acquisition only."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    service_name: str = "kaip"
    version: str = "0.5.0"
    host: str = field(default_factory=lambda: os.getenv("KAIP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("KAIP_PORT", "8091")))
    db_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("KAIP_DB_PATH", str(Path(__file__).resolve().parents[2] / "data" / "kaip.db"))
        )
    )
    # Scheduler intervals (seconds). Daily jobs use 86400.
    yahoo_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("KAIP_YAHOO_INTERVAL_SECONDS", "30"))
    )
    nse_announcement_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("KAIP_NSE_ANNOUNCEMENT_INTERVAL_SECONDS", "30"))
    )
    nse_bhavcopy_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("KAIP_NSE_BHAVCOPY_INTERVAL_SECONDS", "86400"))
    )
    bse_corporate_action_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("KAIP_BSE_CA_INTERVAL_SECONDS", "86400"))
    )
    company_ir_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("KAIP_COMPANY_IR_INTERVAL_SECONDS", "86400"))
    )
    # Universe for Sprint 6.1 demo / continuous acquisition seed
    watchlist: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            s.strip().upper()
            for s in os.getenv("KAIP_WATCHLIST", "INFY,RELIANCE,TCS,HDFCBANK").split(",")
            if s.strip()
        )
    )
    # Change-detection materiality thresholds
    pe_material_abs: float = field(default_factory=lambda: _env_float("KAIP_PE_MATERIAL_ABS", 1.0))
    revenue_growth_material_pp: float = field(
        default_factory=lambda: _env_float("KAIP_REVENUE_GROWTH_MATERIAL_PP", 5.0)
    )
    price_material_pct: float = field(
        default_factory=lambda: _env_float("KAIP_PRICE_MATERIAL_PCT", 3.0)
    )
    # Live collectors may be disabled for offline tests
    live_collectors_enabled: bool = field(
        default_factory=lambda: _env_bool("KAIP_LIVE_COLLECTORS", True)
    )
    scheduler_enabled: bool = field(default_factory=lambda: _env_bool("KAIP_SCHEDULER", True))
    # Sprint 6.5 — Adaptive Knowledge Orchestrator (primary). Set KAIP_AKO=false
    # to fall back to the fixed AcquisitionScheduler.
    ako_enabled: bool = field(default_factory=lambda: _env_bool("KAIP_AKO", True))
    ako_tick_seconds: float = field(default_factory=lambda: _env_float("KAIP_AKO_TICK_SECONDS", 1.0))
    duplicate_window_seconds: int = field(
        default_factory=lambda: int(os.getenv("KAIP_DUPLICATE_WINDOW_SECONDS", "300"))
    )
    # Sprint 8.2 — soft bridge to HIP Timeline Intelligence (store-only history)
    hip_base_url: str | None = field(
        default_factory=lambda: (os.getenv("KAIP_HIP_BASE_URL") or os.getenv("HIP_BASE_URL") or "").strip()
        or None
    )


def get_settings() -> Settings:
    return Settings()
