"""E03 feature flags — Architecture v1.0.1 P0/M0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E03Flags:
    e03_p0: bool = True
    e03_parity: bool = True
    e03_composite: bool = False
    e03_xs_mode: bool = False
    e03_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E03Flags":
        s = settings or get_settings()
        return cls(
            e03_p0=bool(getattr(s, "e03_p0", True)),
            e03_parity=bool(getattr(s, "e03_parity", True)),
            e03_composite=bool(getattr(s, "e03_composite", False)),
            e03_xs_mode=bool(getattr(s, "e03_xs_mode", False)),
            e03_ml=bool(getattr(s, "e03_ml", False)),
        )
