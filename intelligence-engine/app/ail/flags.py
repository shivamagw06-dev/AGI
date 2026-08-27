"""AIL feature flags — additive; never redesign FAA/FRE/CAE."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class AilFlags:
    ail: bool = True
    ail_cde: bool = True
    ail_ede: bool = True
    ail_te: bool = True
    ail_pe: bool = True
    ail_cme: bool = True
    ail_el: bool = True
    ail_graph: bool = True
    ail_timeline: bool = True
    ail_ask_agi: bool = True
    ail_redis_cache: bool = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "AilFlags":
        s = settings or get_settings()
        return cls(
            ail=bool(getattr(s, "ail", True)),
            ail_cde=bool(getattr(s, "ail_cde", True)),
            ail_ede=bool(getattr(s, "ail_ede", True)),
            ail_te=bool(getattr(s, "ail_te", True)),
            ail_pe=bool(getattr(s, "ail_pe", True)),
            ail_cme=bool(getattr(s, "ail_cme", True)),
            ail_el=bool(getattr(s, "ail_el", True)),
            ail_graph=bool(getattr(s, "ail_graph", True)),
            ail_timeline=bool(getattr(s, "ail_timeline", True)),
            ail_ask_agi=bool(getattr(s, "ail_ask_agi", True)),
            ail_redis_cache=bool(getattr(s, "ail_redis_cache", False)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "AIL": self.ail,
            "AIL_CDE": self.ail_cde,
            "AIL_EDE": self.ail_ede,
            "AIL_TE": self.ail_te,
            "AIL_PE": self.ail_pe,
            "AIL_CME": self.ail_cme,
            "AIL_EL": self.ail_el,
            "AIL_GRAPH": self.ail_graph,
            "AIL_TIMELINE": self.ail_timeline,
            "AIL_ASK_AGI": self.ail_ask_agi,
            "AIL_REDIS_CACHE": self.ail_redis_cache,
        }
