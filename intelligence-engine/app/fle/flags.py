"""FLE feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class FleFlags:
    fle: bool = True
    fle_auto_resolve: bool = True
    fle_learning: bool = True
    fle_calibration: bool = True
    fle_scenarios: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "FleFlags":
        s = settings or get_settings()
        return cls(
            fle=bool(getattr(s, "fle", True)),
            fle_auto_resolve=bool(getattr(s, "fle_auto_resolve", True)),
            fle_learning=bool(getattr(s, "fle_learning", True)),
            fle_calibration=bool(getattr(s, "fle_calibration", True)),
            fle_scenarios=bool(getattr(s, "fle_scenarios", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "FLE": self.fle,
            "FLE_AUTO_RESOLVE": self.fle_auto_resolve,
            "FLE_LEARNING": self.fle_learning,
            "FLE_CALIBRATION": self.fle_calibration,
            "FLE_SCENARIOS": self.fle_scenarios,
        }
