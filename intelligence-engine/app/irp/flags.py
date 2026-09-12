"""IRP feature flags — Architecture v1.0.1 programme defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class IrpFlags:
    irp: bool = True
    irp_learning: bool = True
    irp_validation: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "IrpFlags":
        s = settings or get_settings()
        return cls(
            irp=bool(getattr(s, "irp", True)),
            irp_learning=bool(getattr(s, "irp_learning", True)),
            irp_validation=bool(getattr(s, "irp_validation", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "IRP": self.irp,
            "IRP_LEARNING": self.irp_learning,
            "IRP_VALIDATION": self.irp_validation,
        }
