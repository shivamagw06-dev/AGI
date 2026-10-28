"""FRE feature flags."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class FreFlags:
    fre: bool = True
    fre_query_planner: bool = True
    fre_acquisition: bool = True
    fre_hybrid_search: bool = True
    fre_rerank: bool = True
    fre_evidence: bool = True
    fre_graph: bool = True
    fre_scheduler: bool = True
    fre_soft_publish_kip: bool = True
    fre_ask_agi: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "FreFlags":
        s = settings or get_settings()
        return cls(
            fre=bool(getattr(s, "fre", True)),
            fre_query_planner=bool(getattr(s, "fre_query_planner", True)),
            fre_acquisition=bool(getattr(s, "fre_acquisition", True)),
            fre_hybrid_search=bool(getattr(s, "fre_hybrid_search", True)),
            fre_rerank=bool(getattr(s, "fre_rerank", True)),
            fre_evidence=bool(getattr(s, "fre_evidence", True)),
            fre_graph=bool(getattr(s, "fre_graph", True)),
            fre_scheduler=bool(getattr(s, "fre_scheduler", True)),
            fre_soft_publish_kip=bool(getattr(s, "fre_soft_publish_kip", True)),
            fre_ask_agi=bool(getattr(s, "fre_ask_agi", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "FRE": self.fre,
            "FRE_QUERY_PLANNER": self.fre_query_planner,
            "FRE_ACQUISITION": self.fre_acquisition,
            "FRE_HYBRID_SEARCH": self.fre_hybrid_search,
            "FRE_RERANK": self.fre_rerank,
            "FRE_EVIDENCE": self.fre_evidence,
            "FRE_GRAPH": self.fre_graph,
            "FRE_SCHEDULER": self.fre_scheduler,
            "FRE_SOFT_PUBLISH_KIP": self.fre_soft_publish_kip,
            "FRE_ASK_AGI": self.fre_ask_agi,
        }
