"""IOC feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class IocFlags:
    ioc: bool = True
    ioc_alerts: bool = True
    ioc_reports: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "IocFlags":
        s = settings or get_settings()
        return cls(
            ioc=bool(getattr(s, "ioc", True)),
            ioc_alerts=bool(getattr(s, "ioc_alerts", True)),
            ioc_reports=bool(getattr(s, "ioc_reports", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "IOC": self.ioc,
            "IOC_ALERTS": self.ioc_alerts,
            "IOC_REPORTS": self.ioc_reports,
        }
