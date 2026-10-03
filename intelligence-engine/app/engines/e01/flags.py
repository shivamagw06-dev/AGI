"""E01 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E01Flags:
    e01_p0: bool = True
    e01_hmm: bool = False
    e01_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E01Flags":
        s = settings or get_settings()
        return cls(
            e01_p0=bool(getattr(s, "e01_p0", True)),
            e01_hmm=bool(getattr(s, "e01_hmm", False)),
            e01_ml=bool(getattr(s, "e01_ml", False)),
        )
