"""KF1 feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class KfFlags:
    kf: bool = True
    kf_auto_build: bool = True
    kf_company: bool = True
    kf_sector: bool = True
    kf_theme: bool = True
    kf_macro: bool = True
    kf_predictions: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "KfFlags":
        s = settings or get_settings()
        return cls(
            kf=bool(getattr(s, "kf", True)),
            kf_auto_build=bool(getattr(s, "kf_auto_build", True)),
            kf_company=bool(getattr(s, "kf_company", True)),
            kf_sector=bool(getattr(s, "kf_sector", True)),
            kf_theme=bool(getattr(s, "kf_theme", True)),
            kf_macro=bool(getattr(s, "kf_macro", True)),
            kf_predictions=bool(getattr(s, "kf_predictions", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "KF": self.kf,
            "KF_AUTO_BUILD": self.kf_auto_build,
            "KF_COMPANY": self.kf_company,
            "KF_SECTOR": self.kf_sector,
            "KF_THEME": self.kf_theme,
            "KF_MACRO": self.kf_macro,
            "KF_PREDICTIONS": self.kf_predictions,
        }
