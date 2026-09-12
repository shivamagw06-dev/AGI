"""IB feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class IbFlags:
    ib: bool = True
    ib_persist: bool = True
    ib_retry: bool = True
    ib_dlq: bool = True
    ib_replay: bool = True
    ib_cache_invalidate: bool = True
    ib_soft_handlers: bool = True
    ib_ask_agi_emit: bool = True  # soft-emit bus events from Ask AGI activity

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "IbFlags":
        s = settings or get_settings()
        return cls(
            ib=bool(getattr(s, "ib", True)),
            ib_persist=bool(getattr(s, "ib_persist", True)),
            ib_retry=bool(getattr(s, "ib_retry", True)),
            ib_dlq=bool(getattr(s, "ib_dlq", True)),
            ib_replay=bool(getattr(s, "ib_replay", True)),
            ib_cache_invalidate=bool(getattr(s, "ib_cache_invalidate", True)),
            ib_soft_handlers=bool(getattr(s, "ib_soft_handlers", True)),
            ib_ask_agi_emit=bool(getattr(s, "ib_ask_agi_emit", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "IB": self.ib,
            "IB_PERSIST": self.ib_persist,
            "IB_RETRY": self.ib_retry,
            "IB_DLQ": self.ib_dlq,
            "IB_REPLAY": self.ib_replay,
            "IB_CACHE_INVALIDATE": self.ib_cache_invalidate,
            "IB_SOFT_HANDLERS": self.ib_soft_handlers,
            "IB_ASK_AGI_EMIT": self.ib_ask_agi_emit,
        }
