"""E04 feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class E04Flags:
    e04_p0: bool = True
    e04_kalman: bool = False
    e04_dynamic_hedge: bool = False
    e04_etf_basis: bool = False
    e04_ml: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "E04Flags":
        s = settings or get_settings()
        return cls(
            e04_p0=bool(getattr(s, "e04_p0", True)),
            e04_kalman=bool(getattr(s, "e04_kalman", False)),
            e04_dynamic_hedge=bool(getattr(s, "e04_dynamic_hedge", False)),
            e04_etf_basis=bool(getattr(s, "e04_etf_basis", False)),
            e04_ml=bool(getattr(s, "e04_ml", False)),
        )
