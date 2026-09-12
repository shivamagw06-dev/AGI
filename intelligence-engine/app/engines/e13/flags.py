"""E13 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E13Flags:
    e13_p0: bool = True
    e13_revisions: bool = False
    e13_moat: bool = False
    e13_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E13Flags":
        s = settings or get_settings()
        return cls(
            e13_p0=bool(getattr(s, "e13_p0", True)),
            e13_revisions=bool(getattr(s, "e13_revisions", False)),
            e13_moat=bool(getattr(s, "e13_moat", False)),
            e13_ml=bool(getattr(s, "e13_ml", False)),
        )
