"""KCV1 feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class KcFlags:
    kc: bool = True
    kc_auto_populate: bool = True
    kc_broker: bool = True
    kc_earnings: bool = True
    kc_gaps: bool = True
    kc_learning: bool = True
    kc_quality: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "KcFlags":
        s = settings or get_settings()
        return cls(
            kc=bool(getattr(s, "kc", True)),
            kc_auto_populate=bool(getattr(s, "kc_auto_populate", True)),
            kc_broker=bool(getattr(s, "kc_broker", True)),
            kc_earnings=bool(getattr(s, "kc_earnings", True)),
            kc_gaps=bool(getattr(s, "kc_gaps", True)),
            kc_learning=bool(getattr(s, "kc_learning", True)),
            kc_quality=bool(getattr(s, "kc_quality", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "KC": self.kc,
            "KC_AUTO_POPULATE": self.kc_auto_populate,
            "KC_BROKER": self.kc_broker,
            "KC_EARNINGS": self.kc_earnings,
            "KC_GAPS": self.kc_gaps,
            "KC_LEARNING": self.kc_learning,
            "KC_QUALITY": self.kc_quality,
        }
