"""AIP feature flags — Architecture v1.0.1 research-programme defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class AipFlags:
    aip: bool = True
    aip_experiments: bool = True
    aip_promotion: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "AipFlags":
        s = settings or get_settings()
        return cls(
            aip=bool(getattr(s, "aip", True)),
            aip_experiments=bool(getattr(s, "aip_experiments", True)),
            aip_promotion=bool(getattr(s, "aip_promotion", False)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "AIP": self.aip,
            "AIP_EXPERIMENTS": self.aip_experiments,
            "AIP_PROMOTION": self.aip_promotion,
        }
