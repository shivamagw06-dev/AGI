"""In-memory Academy access metrics (optional persistence later)."""

from __future__ import annotations

from pydantic import BaseModel


class AcademyMetrics(BaseModel):
    concept_reads: int = 0
    teaches: int = 0
    exams_run: int = 0
    consumer_calls: int = 0
    searches: int = 0
    fapi_calls: int = 0


class AcademyStore:
    def __init__(self) -> None:
        self.metrics = AcademyMetrics()
        self.recent: list[dict] = []

    def observe(self, kind: str, payload: dict | None = None) -> None:
        if kind == "concept":
            self.metrics.concept_reads += 1
        elif kind == "teach":
            self.metrics.teaches += 1
        elif kind == "exam":
            self.metrics.exams_run += 1
        elif kind == "consumer":
            self.metrics.consumer_calls += 1
        elif kind == "search":
            self.metrics.searches += 1
        elif kind == "fapi":
            self.metrics.fapi_calls += 1
        if payload:
            self.recent.append({"kind": kind, **payload})
            self.recent = self.recent[-50:]

    def snapshot(self) -> dict:
        return {"metrics": self.metrics.model_dump(), "recent": list(self.recent)}
