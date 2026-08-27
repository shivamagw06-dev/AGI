"""KIP feature flags — Architecture v1.0.1 P0 + P1 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class KipFlags:
    # P0
    kip: bool = True
    kip_rag: bool = True
    kip_graph: bool = True
    kip_versioning: bool = True
    kip_ocr: bool = True
    kip_llm_summary: bool = True
    # P1 — Continuous Knowledge Acquisition & House Intelligence
    kip_auto_ingest: bool = True
    kip_house_view: bool = True
    kip_prediction_tracking: bool = True
    kip_timeline: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "KipFlags":
        s = settings or get_settings()
        return cls(
            kip=bool(getattr(s, "kip", True)),
            kip_rag=bool(getattr(s, "kip_rag", True)),
            kip_graph=bool(getattr(s, "kip_graph", True)),
            kip_versioning=bool(getattr(s, "kip_versioning", True)),
            kip_ocr=bool(getattr(s, "kip_ocr", True)),
            kip_llm_summary=bool(getattr(s, "kip_llm_summary", True)),
            kip_auto_ingest=bool(getattr(s, "kip_auto_ingest", True)),
            kip_house_view=bool(getattr(s, "kip_house_view", True)),
            kip_prediction_tracking=bool(getattr(s, "kip_prediction_tracking", True)),
            kip_timeline=bool(getattr(s, "kip_timeline", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "KIP": self.kip,
            "KIP_RAG": self.kip_rag,
            "KIP_GRAPH": self.kip_graph,
            "KIP_VERSIONING": self.kip_versioning,
            "KIP_OCR": self.kip_ocr,
            "KIP_LLM_SUMMARY": self.kip_llm_summary,
            "KIP_AUTO_INGEST": self.kip_auto_ingest,
            "KIP_HOUSE_VIEW": self.kip_house_view,
            "KIP_PREDICTION_TRACKING": self.kip_prediction_tracking,
            "KIP_TIMELINE": self.kip_timeline,
        }
