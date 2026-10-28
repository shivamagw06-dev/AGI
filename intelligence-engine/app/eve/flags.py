"""EVE feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class EveFlags:
    eve: bool = True
    eve_auto_verify: bool = True
    eve_gate_publish: bool = True
    eve_conflicts: bool = True
    eve_timeline: bool = True
    eve_daily_jobs: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "EveFlags":
        s = settings or get_settings()
        return cls(
            eve=bool(getattr(s, "eve", True)),
            eve_auto_verify=bool(getattr(s, "eve_auto_verify", True)),
            eve_gate_publish=bool(getattr(s, "eve_gate_publish", True)),
            eve_conflicts=bool(getattr(s, "eve_conflicts", True)),
            eve_timeline=bool(getattr(s, "eve_timeline", True)),
            eve_daily_jobs=bool(getattr(s, "eve_daily_jobs", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "EVE": self.eve,
            "EVE_AUTO_VERIFY": self.eve_auto_verify,
            "EVE_GATE_PUBLISH": self.eve_gate_publish,
            "EVE_CONFLICTS": self.eve_conflicts,
            "EVE_TIMELINE": self.eve_timeline,
            "EVE_DAILY_JOBS": self.eve_daily_jobs,
        }
