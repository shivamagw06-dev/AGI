"""UI aggregation feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class UiFlags:
    ui: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "UiFlags":
        s = settings or get_settings()
        return cls(ui=bool(getattr(s, "ui", True)))

    def as_dict(self) -> dict[str, bool]:
        return {"UI": self.ui}
