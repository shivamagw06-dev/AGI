"""Finance Academy service facade."""

from __future__ import annotations

from typing import Any

from academy.service import AcademyCore
from app.academy.flags import AcademyFlags
from app.academy.store import AcademyStore
from app.core.config import get_settings


class AcademyService:
    """Library access layer for the AGI Finance Academy curriculum."""

    def __init__(
        self,
        *,
        flags: AcademyFlags | None = None,
        store: AcademyStore | None = None,
        core: AcademyCore | None = None,
    ) -> None:
        self.flags = flags or AcademyFlags.from_settings(get_settings())
        self.store = store or AcademyStore()
        self.core = core or AcademyCore()

    def _require(self) -> None:
        if not self.flags.academy:
            raise RuntimeError("Finance Academy is disabled (ACADEMY=false)")

    def health(self) -> dict[str, Any]:
        body = self.core.health(enabled=self.flags.academy)
        body["flags"] = self.flags.as_dict()
        body["snapshot"] = self.store.snapshot() if self.flags.academy else {}
        return body

    def dashboard(self) -> dict[str, Any]:
        self._require()
        out = self.core.dashboard()
        out["flags"] = self.flags.as_dict()
        out["metrics"] = self.store.metrics.model_dump()
        return out

    def courses(self) -> dict[str, Any]:
        self._require()
        return self.core.courses()

    def course(self, course_id: str | None = None) -> dict[str, Any]:
        self._require()
        return self.core.course(course_id)

    def list_concepts(self, tag: str | None = None, course_id: str | None = None) -> dict[str, Any]:
        self._require()
        return self.core.list_concepts(tag=tag, course_id=course_id)

    def get_concept(self, concept_id: str) -> dict[str, Any]:
        self._require()
        out = self.core.get_concept(concept_id)
        self.store.observe("concept", {"concept_id": concept_id})
        return out

    def teach(self, concept_id: str) -> dict[str, Any]:
        self._require()
        out = self.core.teach(concept_id)
        self.store.observe("teach", {"concept_id": concept_id})
        return out

    def graph(self, course_id: str | None = None) -> dict[str, Any]:
        self._require()
        return self.core.graph(course_id)

    def neighborhood(self, concept_id: str) -> dict[str, Any]:
        self._require()
        return self.core.neighborhood(concept_id)

    def causal_models(self) -> dict[str, Any]:
        self._require()
        return self.core.causal_models()

    def mental_models(self) -> dict[str, Any]:
        self._require()
        return self.core.mental_models()

    def quality(self, course_id: str | None = None) -> dict[str, Any]:
        self._require()
        return self.core.quality(course_id)

    def provenance(self) -> dict[str, Any]:
        self._require()
        if not self.flags.academy_provenance:
            return {"enabled": False}
        return self.core.provenance()

    def enrich(self, concept_id: str) -> dict[str, Any]:
        self._require()
        return self.core.enrich(concept_id)

    def exams(self, course_id: str | None = None) -> dict[str, Any]:
        self._require()
        if not self.flags.academy_exams:
            return {"enabled": False}
        out = self.core.exams(course_id)
        self.store.observe("exam", {"suite": True})
        return out

    def answer(self, question_id: str) -> dict[str, Any]:
        self._require()
        out = self.core.answer(question_id)
        self.store.observe("exam", {"question_id": question_id})
        return out

    def consumer(self, engine: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        out = self.core.consumer(engine, payload)
        self.store.observe("consumer", {"engine": engine})
        return out

    def search(self, q: str, limit: int = 20, course_id: str | None = None) -> dict[str, Any]:
        self._require()
        out = self.core.search(q, limit=limit, course_id=course_id)
        self.store.observe("search", {"q": q})
        return out

    def red_flags(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        return self.core.red_flags(payload)

    def earnings_quality(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        return self.core.earnings_quality(payload)

    def accounting(self) -> dict[str, Any]:
        self._require()
        return self.core.accounting()

    def corporate_finance(self) -> dict[str, Any]:
        self._require()
        return self.core.corporate_finance()

    def completion(self, course_id: str | None = None) -> dict[str, Any]:
        self._require()
        return self.core.completion(course_id)

    def metrics(self) -> dict[str, Any]:
        self._require()
        return self.store.snapshot()

    # --- FAPI v1.0 — production integration (not a new engine) ---

    def _production_enabled(self) -> bool:
        return bool(self.flags.academy and self.flags.academy_production)

    def production_package(self, query: str, *, engine: str = "cae", ticker: str | None = None) -> dict[str, Any]:
        """Retrieve + package Academy knowledge for a production query."""
        if not self._production_enabled():
            return {"enabled": False, "bypassed": True, "concept_ids": []}
        from academy.fapi.production import package_for_query

        out = package_for_query(query, engine=engine, ticker=ticker)
        self.store.observe("fapi", {"engine": engine, "concepts": len(out.get("concept_ids") or [])})
        return out

    def production_dashboard(self) -> dict[str, Any]:
        self._require()
        from academy.fapi.production import production_dashboard

        return production_dashboard()

    def production_ab(self, question: str | None = None) -> dict[str, Any]:
        self._require()
        from academy.fapi.production import run_ab_probe

        return run_ab_probe(question or "Why does ROIC matter more than revenue growth?")

    def production_quality_gates(self) -> dict[str, Any]:
        self._require()
        from academy.fapi.production import quality_gates

        return quality_gates()

    def production_attach(self, engine: str, query: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._production_enabled():
            return {"attached": False, "enabled": False}
        from academy.fapi.production import attach_for_engine

        return attach_for_engine(engine, query, payload=payload)
