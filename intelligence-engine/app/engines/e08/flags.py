"""E08 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E08Flags:
    e08_p0: bool = True
    e08_gamma: bool = False
    e08_dealer: bool = False
    e08_surface: bool = False
    e08_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E08Flags":
        s = settings or get_settings()
        return cls(
            e08_p0=bool(getattr(s, "e08_p0", True)),
            e08_gamma=bool(getattr(s, "e08_gamma", False)),
            e08_dealer=bool(getattr(s, "e08_dealer", False)),
            e08_surface=bool(getattr(s, "e08_surface", False)),
            e08_ml=bool(getattr(s, "e08_ml", False)),
        )
