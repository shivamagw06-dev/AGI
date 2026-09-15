"""E11 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E11Flags:
    e11_p0: bool = True
    e11_social: bool = False
    e11_transcripts: bool = False
    e11_llm: bool = False
    e11_ml: bool = False
    e11_altdata: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E11Flags":
        s = settings or get_settings()
        return cls(
            e11_p0=bool(getattr(s, "e11_p0", True)),
            e11_social=bool(getattr(s, "e11_social", False)),
            e11_transcripts=bool(getattr(s, "e11_transcripts", False)),
            e11_llm=bool(getattr(s, "e11_llm", False)),
            e11_ml=bool(getattr(s, "e11_ml", False)),
            e11_altdata=bool(getattr(s, "e11_altdata", False)),
        )
