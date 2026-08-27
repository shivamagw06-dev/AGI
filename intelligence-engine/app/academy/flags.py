"""Finance Academy feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class AcademyFlags:
    academy: bool = True
    academy_provenance: bool = True
    academy_exams: bool = True
    academy_production: bool = True  # FAPI v1.0

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "AcademyFlags":
        s = settings or get_settings()
        return cls(
            academy=bool(getattr(s, "academy", True)),
            academy_provenance=bool(getattr(s, "academy_provenance", True)),
            academy_exams=bool(getattr(s, "academy_exams", True)),
            academy_production=bool(getattr(s, "academy_production", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "ACADEMY": self.academy,
            "ACADEMY_PROVENANCE": self.academy_provenance,
            "ACADEMY_EXAMS": self.academy_exams,
            "ACADEMY_PRODUCTION": self.academy_production,
        }
