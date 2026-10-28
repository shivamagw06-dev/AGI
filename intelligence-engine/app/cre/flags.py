"""CRE feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class CREFlags:
    cre: bool = True
    promotion: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "CREFlags":
        s = settings or get_settings()
        return cls(
            cre=bool(getattr(s, "cre", True)),
            promotion=bool(getattr(s, "promotion", False)),
        )
