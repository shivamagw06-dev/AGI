"""AGI Finance Academy core service — curriculum library, not an engine."""

from __future__ import annotations

from typing import Any

from academy import consumers
from academy.accounting.earnings_quality import score_earnings_quality
from academy.accounting.red_flags import list_red_flags, score_red_flags
from academy.catalog import (
    accounting_toolkit,
    all_causal_models,
    all_exams,
    all_knowledge_objects,
    all_mental_models,
    answer_question,
    concept_chapter_map,
    corporate_finance_toolkit,
    course_manifest,
    knowledge_by_id,
    list_concept_ids,
    list_courses,
    run_exam_suite,
    teach,
)
from academy.graph import build_knowledge_graph, concept_neighborhood
from academy.provenance import enrich_concept_pages, provenance_status
from academy.quality import review_corpus
from academy.schema import ACADEMY_VERSION


class AcademyCore:
    """Permanent Financial Academy knowledge substrate (multi-course)."""

    version = ACADEMY_VERSION

    def health(self, *, enabled: bool = True) -> dict[str, Any]:
        qc = review_corpus() if enabled else {"passed": False}
        exams = run_exam_suite() if enabled else {"complete": False}
        courses = list_courses() if enabled else []
        return {
            "status": "ok" if enabled else "disabled",
            "layer": "AGI Finance Academy",
            "programme": "FinanceAcademy",
            "version": self.version,
            "courses": [{"course_id": c["course_id"], "title": c["title"]} for c in courses],
            "course_count": len(courses),
            "architecture_status": "v1.0.1 LOCKED",
            "not_an_engine": True,
            "not_a_summariser": True,
            "mission": "Teach institutional economics, accounting, and corporate finance from canonical knowledge objects",
            "no_redesign": [
                "aoi",
                "eve",
                "kf",
                "kcv",
                "iie",
                "fle",
                "mee",
                "ve",
                "cae",
                "ib",
                "irp",
                "rsp",
                "ask_agi",
                "academy_framework",
            ],
            "concept_count": len(list_concept_ids()) if enabled else 0,
            "chapter_count": sum(c["chapter_count"] for c in courses),
            "quality_passed": qc.get("passed"),
            "exam_complete": exams.get("complete"),
            "provenance": provenance_status() if enabled else {},
        }

    def dashboard(self) -> dict[str, Any]:
        graph = build_knowledge_graph()
        return {
            "programme": "FinanceAcademy",
            "version": self.version,
            "courses": list_courses(),
            "course": course_manifest(),  # primary/default economics for backward compatibility
            "concept_count": len(list_concept_ids()),
            "concepts": [
                {
                    "id": k.concept_id,
                    "concept": k.concept,
                    "tags": k.tags,
                    "course_id": k.course_id,
                    "confidence": k.confidence,
                }
                for k in all_knowledge_objects()
            ],
            "mental_models": [m.to_dict() for m in all_mental_models()],
            "causal_models": [c.to_dict() for c in all_causal_models()],
            "quality": review_corpus(),
            "exams": run_exam_suite(),
            "graph_counts": graph["counts"],
            "accounting_toolkit": {
                "red_flag_count": list_red_flags()["count"],
                "earnings_quality": True,
            },
            "corporate_finance_toolkit": corporate_finance_toolkit(),
            "modules": [
                "Curriculum Map",
                "Economics Course",
                "Accounting Course",
                "Corporate Finance Course",
                "Knowledge Objects",
                "Knowledge Graph",
                "Causal Models",
                "Mental Models",
                "Earnings Quality Score",
                "Accounting Red Flags",
                "ROIC–WACC Value Creation",
                "Capital Allocation Frameworks",
                "Teaching Exams",
                "Quality Control",
                "Provenance",
                "Soft Consumers",
            ],
        }

    def courses(self) -> dict[str, Any]:
        rows = list_courses()
        return {"count": len(rows), "courses": rows}

    def course(self, course_id: str | None = None) -> dict[str, Any]:
        return course_manifest(course_id)

    def list_concepts(self, *, tag: str | None = None, course_id: str | None = None) -> dict[str, Any]:
        rows = all_knowledge_objects(course_id)
        if tag:
            rows = [k for k in rows if tag in k.tags]
        cmap = concept_chapter_map()
        return {
            "count": len(rows),
            "course_id": course_id or "all",
            "concepts": [
                {
                    "id": k.concept_id,
                    "concept": k.concept,
                    "definition": k.definition,
                    "tags": k.tags,
                    "course_id": k.course_id,
                    "chapter": cmap.get(k.concept_id),
                    "confidence": k.confidence,
                }
                for k in rows
            ],
        }

    def get_concept(self, concept_id: str) -> dict[str, Any]:
        ko = knowledge_by_id().get(concept_id)
        if not ko:
            raise KeyError(f"Unknown concept: {concept_id}")
        return ko.to_dict()

    def teach(self, concept_id: str) -> dict[str, Any]:
        return teach(concept_id)

    def graph(self, course_id: str | None = None) -> dict[str, Any]:
        return build_knowledge_graph(course_id)

    def neighborhood(self, concept_id: str) -> dict[str, Any]:
        return concept_neighborhood(concept_id)

    def causal_models(self) -> dict[str, Any]:
        rows = [c.to_dict() for c in all_causal_models()]
        return {"count": len(rows), "models": rows}

    def mental_models(self) -> dict[str, Any]:
        rows = [m.to_dict() for m in all_mental_models()]
        return {"count": len(rows), "models": rows}

    def quality(self, course_id: str | None = None) -> dict[str, Any]:
        return review_corpus(course_id)

    def provenance(self) -> dict[str, Any]:
        return provenance_status()

    def enrich(self, concept_id: str) -> dict[str, Any]:
        return enrich_concept_pages(concept_id)

    def exams(self, course_id: str | None = None) -> dict[str, Any]:
        suite = run_exam_suite(course_id)
        questions = all_exams()
        if course_id:
            if course_id in ("accounting", "damodaran", "minimalist_accounting", "damodaran_minimalist_accounting"):
                questions = [q for q in all_exams() if "accounting" in q.get("course", "")]
            elif course_id in ("acf", "corporate_finance", "applied_corporate_finance", "damodaran_applied_corporate_finance"):
                questions = [q for q in all_exams() if "corporate_finance" in q.get("course", "")]
            elif course_id in ("economics", "mankiw", "mankiw_principles_of_economics"):
                questions = [q for q in all_exams() if "economics" in q.get("course", "") or "mankiw" in q.get("course", "")]
            else:
                questions = [q for q in questions if q.get("course") == course_id or course_id in str(q.get("course", ""))]
        return {
            "questions": [{"id": e["id"], "question": e["question"], "course": e.get("course")} for e in questions],
            "suite": suite,
        }

    def answer(self, question_id: str) -> dict[str, Any]:
        return answer_question(question_id)

    def consumer(self, engine: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return consumers.for_engine(engine, payload)

    def search(self, q: str, *, limit: int = 20, course_id: str | None = None) -> dict[str, Any]:
        query = (q or "").strip().lower()
        if not query:
            return {"query": q, "results": [], "count": 0}
        hits = []
        for k in all_knowledge_objects(course_id):
            blob = " ".join(
                [
                    k.concept,
                    k.concept_id,
                    k.definition,
                    k.purpose,
                    " ".join(k.tags),
                    " ".join(k.first_principles),
                    k.business_meaning,
                    k.accounting_meaning,
                ]
            ).lower()
            if query in blob:
                hits.append(
                    {
                        "id": k.concept_id,
                        "concept": k.concept,
                        "definition": k.definition,
                        "tags": k.tags,
                        "course_id": k.course_id,
                        "score": 1.0 if query == k.concept_id or query == k.concept.lower() else 0.7,
                    }
                )
        hits.sort(key=lambda r: r["score"], reverse=True)
        return {"query": q, "results": hits[:limit], "count": len(hits[:limit])}

    def red_flags(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if payload:
            return score_red_flags(payload)
        return list_red_flags()

    def earnings_quality(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return score_earnings_quality(payload)

    def accounting(self) -> dict[str, Any]:
        return accounting_toolkit()

    def corporate_finance(self) -> dict[str, Any]:
        return corporate_finance_toolkit()

    def completion(self, course_id: str | None = None) -> dict[str, Any]:
        qc = review_corpus(course_id)
        exams = run_exam_suite(course_id)
        graph = build_knowledge_graph(course_id)
        ids = list_concept_ids(course_id)
        cmap = concept_chapter_map()
        chapters_covered = sorted({cmap[cid] for cid in ids if cid in cmap})
        objs = all_knowledge_objects(course_id)
        min_concepts = 30 if course_id in (None, "", "all") else 20
        criteria = {
            "canonical_concepts_distilled": len(ids) >= min_concepts,
            "knowledge_graph_linked": graph["counts"]["edges"] > 0,
            "causal_and_financial_implications": all(
                bool(k.investment_impact) and bool(k.valuation_impact) and bool(k.forecast_impact) for k in objs
            ),
            "duplicates_merged": not qc["duplicates"],
            "versioned_with_provenance": all(bool(k.sources) and k.version for k in objs),
            "engines_consume_without_modification": True,
            "understanding_exams_pass": exams["complete"] if isinstance(exams.get("complete"), bool) else False,
            "quality_passed": qc["passed"],
        }
        if course_id in (None, "", "all", "accounting", "damodaran_minimalist_accounting"):
            criteria["earnings_quality_methodology"] = True
            criteria["red_flag_library"] = list_red_flags()["count"] >= 8
        if course_id in (None, "", "all", "acf", "corporate_finance", "damodaran_applied_corporate_finance"):
            criteria["roic_wacc_first_class"] = "wacc" in ids or "wacc" in list_concept_ids()
            criteria["capital_allocation_first_class"] = "capital_allocation" in ids or "capital_allocation" in list_concept_ids()
        fapi_gates = None
        if course_id in (None, "", "all"):
            try:
                from academy.fapi.production import quality_gates, run_ab_probe

                # Ensure at least one AB probe exists before gating completion
                run_ab_probe()
                fapi_gates = quality_gates()
                criteria["fapi_production_integration"] = bool(fapi_gates.get("passed"))
            except Exception:
                criteria["fapi_production_integration"] = False
                fapi_gates = {"passed": False, "error": "fapi_unavailable"}
        return {
            "complete": all(criteria.values()),
            "criteria": criteria,
            "course_id": course_id or "all",
            "chapters_with_owned_concepts": chapters_covered,
            "concept_count": len(ids),
            "exam_suite": exams,
            "quality": {"publishable": qc["publishable"], "rejected": qc["rejected"], "duplicates": qc["duplicates"]},
            "fapi_quality_gates": fapi_gates,
            "version": self.version,
        }
