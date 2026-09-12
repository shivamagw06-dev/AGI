"""VE feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class VeFlags:
    ve: bool = True
    ve_auto_value: bool = True
    ve_scenarios: bool = True
    ve_sensitivity: bool = True
    ve_relative: bool = True
    ve_ibus_updates: bool = True  # recalculate on soft IB events when wired

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "VeFlags":
        s = settings or get_settings()
        return cls(
            ve=bool(getattr(s, "ve", True)),
            ve_auto_value=bool(getattr(s, "ve_auto_value", True)),
            ve_scenarios=bool(getattr(s, "ve_scenarios", True)),
            ve_sensitivity=bool(getattr(s, "ve_sensitivity", True)),
            ve_relative=bool(getattr(s, "ve_relative", True)),
            ve_ibus_updates=bool(getattr(s, "ve_ibus_updates", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "VE": self.ve,
            "VE_AUTO_VALUE": self.ve_auto_value,
            "VE_SCENARIOS": self.ve_scenarios,
            "VE_SENSITIVITY": self.ve_sensitivity,
            "VE_RELATIVE": self.ve_relative,
            "VE_IBUS_UPDATES": self.ve_ibus_updates,
        }
