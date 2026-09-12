"""IIE feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class IieFlags:
    iie: bool = True
    iie_auto_analyse: bool = True
    iie_scenarios: bool = True
    iie_catalysts: bool = True
    iie_risks: bool = True
    iie_compare: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "IieFlags":
        s = settings or get_settings()
        return cls(
            iie=bool(getattr(s, "iie", True)),
            iie_auto_analyse=bool(getattr(s, "iie_auto_analyse", True)),
            iie_scenarios=bool(getattr(s, "iie_scenarios", True)),
            iie_catalysts=bool(getattr(s, "iie_catalysts", True)),
            iie_risks=bool(getattr(s, "iie_risks", True)),
            iie_compare=bool(getattr(s, "iie_compare", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "IIE": self.iie,
            "IIE_AUTO_ANALYSE": self.iie_auto_analyse,
            "IIE_SCENARIOS": self.iie_scenarios,
            "IIE_CATALYSTS": self.iie_catalysts,
            "IIE_RISKS": self.iie_risks,
            "IIE_COMPARE": self.iie_compare,
        }
