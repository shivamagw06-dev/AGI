"""E05 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E05Flags:
    e05_p0: bool = True
    e05_deal_probability: bool = False
    e05_transcripts: bool = False
    e05_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E05Flags":
        s = settings or get_settings()
        return cls(
            e05_p0=bool(getattr(s, "e05_p0", True)),
            e05_deal_probability=bool(getattr(s, "e05_deal_probability", False)),
            e05_transcripts=bool(getattr(s, "e05_transcripts", False)),
            e05_ml=bool(getattr(s, "e05_ml", False)),
        )
