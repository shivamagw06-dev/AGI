"""L4 feature flags — Architecture v1.0.1 P0 Shadow defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class L4Flags:
    l4_shadow: bool = True
    l4_primary: bool = False
    l4_bayes: bool = False
    l4_ml: bool = False
    l4_probability: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "L4Flags":
        s = settings or get_settings()
        return cls(
            l4_shadow=bool(getattr(s, "l4_shadow", True)),
            l4_primary=bool(getattr(s, "l4_primary", False)),
            l4_bayes=bool(getattr(s, "l4_bayes", False)),
            l4_ml=bool(getattr(s, "l4_ml", False)),
            l4_probability=bool(getattr(s, "l4_probability", False)),
        )
