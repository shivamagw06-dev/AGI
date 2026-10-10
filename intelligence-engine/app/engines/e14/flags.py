"""E14 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E14Flags:
    e14_p0: bool = True
    e14_ml: bool = False
    e14_bayes: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E14Flags":
        s = settings or get_settings()
        return cls(
            e14_p0=bool(getattr(s, "e14_p0", True)),
            e14_ml=bool(getattr(s, "e14_ml", False)),
            e14_bayes=bool(getattr(s, "e14_bayes", False)),
        )
