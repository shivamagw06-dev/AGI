"""MEE feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class MeeFlags:
    mee: bool = True
    mee_auto_detect: bool = True
    mee_propagate: bool = True
    mee_impact: bool = True
    mee_similar: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "MeeFlags":
        s = settings or get_settings()
        return cls(
            mee=bool(getattr(s, "mee", True)),
            mee_auto_detect=bool(getattr(s, "mee_auto_detect", True)),
            mee_propagate=bool(getattr(s, "mee_propagate", True)),
            mee_impact=bool(getattr(s, "mee_impact", True)),
            mee_similar=bool(getattr(s, "mee_similar", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "MEE": self.mee,
            "MEE_AUTO_DETECT": self.mee_auto_detect,
            "MEE_PROPAGATE": self.mee_propagate,
            "MEE_IMPACT": self.mee_impact,
            "MEE_SIMILAR": self.mee_similar,
        }
