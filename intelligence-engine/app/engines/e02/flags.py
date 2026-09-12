"""E02 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E02Flags:
    e02_p0: bool = True
    e02_timing: bool = False
    e02_rotation: bool = False
    e02_smart_beta: bool = False
    e02_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E02Flags":
        s = settings or get_settings()
        return cls(
            e02_p0=bool(getattr(s, "e02_p0", True)),
            e02_timing=bool(getattr(s, "e02_timing", False)),
            e02_rotation=bool(getattr(s, "e02_rotation", False)),
            e02_smart_beta=bool(getattr(s, "e02_smart_beta", False)),
            e02_ml=bool(getattr(s, "e02_ml", False)),
        )
