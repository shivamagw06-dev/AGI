"""RMS feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class RmsFlags:
    rms: bool = True
    rms_review: bool = True
    rms_approval: bool = True
    rms_publish: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "RmsFlags":
        s = settings or get_settings()
        return cls(
            rms=bool(getattr(s, "rms", True)),
            rms_review=bool(getattr(s, "rms_review", True)),
            rms_approval=bool(getattr(s, "rms_approval", True)),
            rms_publish=bool(getattr(s, "rms_publish", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "RMS": self.rms,
            "RMS_REVIEW": self.rms_review,
            "RMS_APPROVAL": self.rms_approval,
            "RMS_PUBLISH": self.rms_publish,
        }
