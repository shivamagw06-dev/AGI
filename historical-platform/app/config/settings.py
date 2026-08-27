"""HIP / HAP runtime configuration — historical acquisition only."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    service_name: str = "hip-hai"
    version: str = "0.4.0"
    host: str = field(default_factory=lambda: os.getenv("HIP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("HIP_PORT", "8092")))
    db_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("HIP_DB_PATH", str(Path(__file__).resolve().parents[2] / "data" / "hip.db"))
        )
    )
    watchlist: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            s.strip().upper()
            for s in os.getenv("HIP_WATCHLIST", "INFY,RELIANCE,TCS,HDFCBANK").split(",")
            if s.strip()
        )
    )
    live_collectors_enabled: bool = field(
        default_factory=lambda: _env_bool("HIP_LIVE_COLLECTORS", False)
    )
    # Coverage floors used by completeness scoring
    min_daily_bars: int = field(default_factory=lambda: int(os.getenv("HIP_MIN_DAILY_BARS", "2500")))
    min_quarterly_financials: int = field(
        default_factory=lambda: int(os.getenv("HIP_MIN_QUARTERLY_FINANCIALS", "20"))
    )
    min_annual_financials: int = field(
        default_factory=lambda: int(os.getenv("HIP_MIN_ANNUAL_FINANCIALS", "10"))
    )


def get_settings() -> Settings:
    return Settings()
