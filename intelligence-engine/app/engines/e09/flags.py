"""E09 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E09Flags:
    e09_p0: bool = True
    e09_breakout: bool = False
    e09_cross_asset: bool = False
    e09_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E09Flags":
        s = settings or get_settings()
        return cls(
            e09_p0=bool(getattr(s, "e09_p0", True)),
            e09_breakout=bool(getattr(s, "e09_breakout", False)),
            e09_cross_asset=bool(getattr(s, "e09_cross_asset", False)),
            e09_ml=bool(getattr(s, "e09_ml", False)),
        )
