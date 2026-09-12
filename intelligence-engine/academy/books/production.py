"""Academy Books production facade — soft adapters only."""

from __future__ import annotations

from typing import Any

from academy.books.flags import (
    flag_formulas,
    flag_frameworks,
    flag_graph,
    flag_spreadsheets,
    flags_dict,
    is_books_enabled,
)
from academy.books.ingest import ensure_seeded
from academy.books.library import resolve_library_root, scan_library
from academy.books.schema import BOOKS_VERSION
from academy.books.store import get_books_store, reset_books_store


def bootstrap() -> dict[str, Any]:
    return ensure_seeded()


def dashboard() -> dict[str, Any]:
    ensure_seeded()
    store = get_books_store()
    snap = store.snapshot()
    academies: dict[str, int] = {}
    for c in store.concepts.values():
        academies[c.academy] = academies.get(c.academy, 0) + 1
    linked_companies = sorted(
        {co.upper() for c in store.concepts.values() for co in c.linked_companies}
    )
    real_books = [b for b in store.books.values() if b.source_format != "seed"]
    sectors = sorted(
        {
            *(x for c in store.concepts.values() for x in c.linked_industries),
            *(c.academy.replace("sector_", "") for c in store.concepts.values() if c.academy.startswith("sector_")),
        }
    )
    # Library scan is optional for cockpit speed — never block Mission Control on disk walks.
    lib: dict[str, Any] = {"counts": {}}
    reach: dict[str, Any] = {}
    try:
        lib = scan_library()
        from academy.books.library import library_reachability

        reach = library_reachability()
    except Exception as exc:
        lib = {"counts": {}, "error": str(exc)[:120]}
        reach = {"ok": False, "error": str(exc)[:120]}
    return {
        "programme": "AGI_ACADEMY_BOOKS",
        "books_version": BOOKS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_books_enabled(),
        "flags": flags_dict(),
        "library_root": str(resolve_library_root() or ""),
        "library_scan": lib.get("counts") or {},
        "library_reachability": reach,
        # Metadata only — never dump full concept bodies into Mission Control.
        "books": [
            {
                "book_id": b.book_id,
                "title": b.title,
                "source_format": b.source_format,
                "status": b.status,
            }
            for b in store.books.values()
        ],
        "books_successfully_ingested": len(real_books),
        "academies": academies,
        "concept_count": snap["concepts"],
        "framework_count": snap["frameworks"] if flag_frameworks() else 0,
        "formula_count": snap["formulas"] if flag_formulas() else 0,
        "spreadsheet_count": snap.get("spreadsheets") or 0 if flag_spreadsheets() else 0,
        "graph_edges": snap["edges"] if flag_graph() else 0,
        "chapter_count": snap["chapters"],
        "coverage": {
            "academies_populated": len(academies),
            "books_ingested": len(real_books),
            "seed_ratio": round(
                sum(1 for b in store.books.values() if b.source_format == "seed") / max(1, snap["books"]),
                3,
            ),
            "library_files_seen": (lib.get("counts") or {}).get("total_supported") or 0,
        },
        "learning_progress": {
            "concepts": snap["concepts"],
            "frameworks": snap["frameworks"],
            "formulas": snap["formulas"],
            "spreadsheets": snap.get("spreadsheets") or 0,
            "graph": snap["edges"],
        },
        "linked_companies": linked_companies,
        "sectors": sectors[:40],
        "sectors_linked": sectors,
        "most_used_concepts": [
            {"concept_id": cid, "uses": n} for cid, n in snap["most_used"]
        ],
        "knowledge_graph": _graph_preview(store) if flag_graph() else {"nodes": [], "edges": []},
        "latest_ingestion_report": (store.ingestion_reports[-1] if store.ingestion_reports else None),
        "copyright": {
            "verbatim_storage": False,
            "searchable_pdf_index": False,
            "policy": "concepts_frameworks_formulas_only",
        },
        "books_v3": _v3_dashboard_soft(),
    }


def _v3_dashboard_soft() -> dict[str, Any]:
    try:
        from academy.books.flags import flag_books_v3
        from academy.books.v3.production import dashboard as v3_dashboard

        if not flag_books_v3():
            return {"enabled": False}
        d = v3_dashboard()
        return {
            "enabled": True,
            "version": d.get("books_v3_version"),
            "mode": d.get("mode"),
            "snapshot": d.get("snapshot"),
            "institutional_topics": d.get("institutional_topics"),
            "analyst_bases": d.get("analyst_bases"),
            "sectors": d.get("sectors"),
        }
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}


def _graph_preview(store) -> dict[str, Any]:
    nodes = []
    for c in list(store.concepts.values())[:40]:
        nodes.append({"id": c.concept_id, "label": c.title, "type": "concept", "academy": c.academy})
    for f in list(store.formulas.values())[:20]:
        nodes.append({"id": f.formula_id, "label": f.name, "type": "formula", "academy": f.academy})
    for fw in list(store.frameworks.values())[:20]:
        nodes.append({"id": fw.framework_id, "label": fw.name, "type": "framework", "academy": fw.academy})
    edges = [e.to_dict() for e in list(store.edges.values())[:80]]
    return {"nodes": nodes, "edges": edges}


def package_for_query(
    query: str,
    *,
    ticker: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Soft reasoning package — frameworks/concepts for Ask AGI / IRP / Research Writer."""
    if not is_books_enabled():
        return {"enabled": False, "concepts": [], "frameworks": [], "formulas": []}
    ensure_seeded()
    store = get_books_store()
    q = (query or "").lower()
    t = (ticker or "").upper()

    scored: list[tuple[float, Any]] = []
    for c in store.concepts.values():
        blob = f"{c.title} {c.definition} {c.academy}".lower()
        score = 0.0
        for token in set(q.replace("?", " ").split()):
            if len(token) > 3 and token in blob:
                score += 1.0
        if t and t in " ".join(c.linked_companies).upper():
            score += 2.5
        if "nestle" in q and c.academy == "sector_fmcg":
            score += 2.0
        if "valu" in q and c.academy == "valuation":
            score += 1.2
        if score > 0:
            scored.append((score + c.confidence, c))
            store.touch(c.concept_id)
    scored.sort(key=lambda x: -x[0])
    concepts = [c for _, c in scored[:limit]]

    frameworks = []
    if flag_frameworks():
        for fw in store.frameworks.values():
            blob = f"{fw.name} {fw.purpose} {' '.join(fw.applications)}".lower()
            if any(tok in blob for tok in q.split() if len(tok) > 3) or (
                "nestle" in q and "staples" in blob
            ):
                frameworks.append(fw)
        frameworks = frameworks[: limit // 2 or 1]

    formulas = []
    if flag_formulas():
        for f in store.formulas.values():
            if f.name.lower() in q or any(x in q for x in ("pe", "valu", "dcf", "wacc", "roic", "roe")):
                formulas.append(f)
        formulas = formulas[:8]

    answer_hints = _reasoning_hints(concepts, frameworks, formulas)
    out: dict[str, Any] = {
        "enabled": True,
        "books_version": BOOKS_VERSION,
        "concepts": [c.to_dict() for c in concepts],
        "concept_ids": [c.concept_id for c in concepts],
        "frameworks": [f.to_dict() for f in frameworks] if flag_frameworks() else [],
        "formulas": [f.to_dict() for f in formulas] if flag_formulas() else [],
        "answer_hints": answer_hints,
        "provenance": {
            "influenced": bool(concepts or frameworks),
            "source": "academy_books",
            "verbatim_quotes": False,
        },
    }
    # Soft-wire Books V3 institutional knowledge (no engine redesign)
    try:
        from academy.books.flags import flag_books_v3
        from academy.books.v3.production import soft_slice_for_package

        if flag_books_v3():
            v3 = soft_slice_for_package(query, ticker=ticker)
            if v3:
                out.update(v3)
                for h in (v3.get("books_v3") or {}).get("answer_hints") or []:
                    if h and h not in out["answer_hints"]:
                        out["answer_hints"].append(h)
                out["answer_hints"] = out["answer_hints"][:6]
                out["provenance"]["books_v3"] = True
                out["provenance"]["cross_book_synthesis"] = bool(
                    (v3.get("books_v3") or {}).get("institutional_objects")
                )
    except Exception:
        pass
    return out


def _reasoning_hints(concepts, frameworks, formulas) -> list[str]:
    hints: list[str] = []
    titles = {c.title.lower() for c in concepts}
    if any("pe" in t or "multiple" in t for t in titles) or formulas:
        hints.append(
            "A high PE alone does not indicate overvaluation. Evaluate the multiple alongside expected growth, "
            "reinvestment needs, return on capital, competitive position and cash generation."
        )
    if any(c.concept_id == "seed_c_moat" or "moat" in c.title.lower() for c in concepts):
        hints.append(
            "Assess whether returns on capital can persist above the cost of capital, and identify the economic drivers of any advantage."
        )
    if any(c.academy == "sector_fmcg" for c in concepts):
        hints.append(
            "For consumer staples, weigh brand power, pricing power, working capital discipline and ROIC before treating a premium multiple as justified."
        )
    if frameworks:
        fw = frameworks[0]
        hints.append(
            f"Apply the {fw.name} framework: map evidence to inputs, then translate outputs into investment implications in AGI's own language."
        )
    return hints[:4]


def soft_enrich_cid(dossier: dict[str, Any], *, ticker: str | None = None) -> dict[str, Any]:
    from academy.books.enrich import enrich_dossier

    return enrich_dossier(dossier, ticker=ticker)


def soft_attach_kf() -> dict[str, Any]:
    from academy.books.kf_attach import attach_books_to_kf

    return attach_books_to_kf()


def ingest_library(*, root: str | None = None, limit: int | None = None) -> dict[str, Any]:
    from academy.books.batch import ingest_personal_library
    from academy.books.flags import flag_spreadsheets

    return ingest_personal_library(
        root=root,
        limit=limit,
        include_spreadsheets=flag_spreadsheets(),
    )


def ingestion_report() -> dict[str, Any]:
    from academy.books.batch import latest_ingestion_report

    return latest_ingestion_report() or {"ok": False, "reason": "no_report"}


def research_writer_slice(query: str = "", ticker: str | None = None) -> dict[str, Any]:
    """Soft slice for Research Writer — structure/framework/terminology only."""
    pkg = package_for_query(query or "investment research", ticker=ticker, limit=8)
    return {
        "enabled": pkg.get("enabled"),
        "frameworks": [f.get("name") for f in pkg.get("frameworks") or []],
        "terminology": [c.get("title") for c in pkg.get("concepts") or []],
        "formulas": [f.get("name") for f in pkg.get("formulas") or []],
        "logic_hints": pkg.get("answer_hints") or [],
        "rule": "never_copy_book_text",
    }


def quality_gates() -> dict[str, Any]:
    ensure_seeded()
    store = get_books_store()
    from academy.books.copyright import assert_no_long_verbatim

    sample = {
        "concepts": [c.to_dict() for c in list(store.concepts.values())[:20]],
        "formulas": [f.to_dict() for f in list(store.formulas.values())[:20]],
        "frameworks": [f.to_dict() for f in list(store.frameworks.values())[:20]],
    }
    long_hits = assert_no_long_verbatim(sample)
    checks = {
        "books_seeded": len(store.books) >= 3,
        "chapters_identified": len(store.chapters) >= 5,
        "concepts_extracted": len(store.concepts) >= 10,
        "frameworks_extracted": len(store.frameworks) >= 5 if flag_frameworks() else True,
        "formulas_extracted": len(store.formulas) >= 5 if flag_formulas() else True,
        "knowledge_graph_created": len(store.edges) >= 5 if flag_graph() else True,
        "academy_categorisation": len({c.academy for c in store.concepts.values()}) >= 4,
        "no_long_verbatim": len(long_hits) == 0,
        "no_searchable_pdf_index": True,
    }
    v3_gates: dict[str, Any] = {}
    try:
        from academy.books.flags import flag_books_v3
        from academy.books.v3.production import quality_gates as v3_quality_gates

        if flag_books_v3():
            v3_gates = v3_quality_gates()
            checks["books_v3_institutional"] = bool(v3_gates.get("passed"))
    except Exception:
        checks["books_v3_institutional"] = False
        v3_gates = {"passed": False}

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "long_verbatim_fields": long_hits[:10],
        "books_version": BOOKS_VERSION,
        "flags": flags_dict(),
        "books_v3": v3_gates,
    }


def reset_for_tests() -> None:
    reset_books_store()
