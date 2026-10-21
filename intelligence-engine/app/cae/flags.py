"""CAE feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class CaeFlags:
    cae: bool = True
    cae_cache: bool = True
    cae_compress: bool = True
    cae_parallel: bool = True
    cae_ask_agi_gateway: bool = True  # Ask AGI uses single CAE call when True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "CaeFlags":
        s = settings or get_settings()
        return cls(
            cae=bool(getattr(s, "cae", True)),
            cae_cache=bool(getattr(s, "cae_cache", True)),
            cae_compress=bool(getattr(s, "cae_compress", True)),
            cae_parallel=bool(getattr(s, "cae_parallel", True)),
            cae_ask_agi_gateway=bool(getattr(s, "cae_ask_agi_gateway", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "CAE": self.cae,
            "CAE_CACHE": self.cae_cache,
            "CAE_COMPRESS": self.cae_compress,
            "CAE_PARALLEL": self.cae_parallel,
            "CAE_ASK_AGI_GATEWAY": self.cae_ask_agi_gateway,
        }
