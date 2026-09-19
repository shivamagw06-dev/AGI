"""E10 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E10Flags:
    e10_p0: bool = True
    e10_optimizer: bool = False
    e10_hrp: bool = False
    e10_mvo: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E10Flags":
        s = settings or get_settings()
        return cls(
            e10_p0=bool(getattr(s, "e10_p0", True)),
            e10_optimizer=bool(getattr(s, "e10_optimizer", False)),
            e10_hrp=bool(getattr(s, "e10_hrp", False)),
            e10_mvo=bool(getattr(s, "e10_mvo", False)),
        )
