"""FIML feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class FimlFlags:
    fiml: bool = True
    fiml_persist_analyses: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "FimlFlags":
        s = settings or get_settings()
        return cls(
            fiml=bool(getattr(s, "fiml", True)),
            fiml_persist_analyses=bool(getattr(s, "fiml_persist_analyses", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {"FIML": self.fiml, "FIML_PERSIST_ANALYSES": self.fiml_persist_analyses}
