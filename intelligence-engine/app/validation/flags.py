"""Validation platform feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class ValidationFlags:
    backtest: bool = True
    live: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ValidationFlags":
        s = settings or get_settings()
        return cls(
            backtest=bool(getattr(s, "backtest", True)),
            live=bool(getattr(s, "live", False)),
        )
