"""Deterministic ICE renderer — binds InstitutionalAnswer; no new reasoning."""

from __future__ import annotations

from typing import Any

from institutional_communication.citations.bind import render_sources_section
from institutional_communication.planner.plan import plan_communication
from institutional_communication.renderers.confidence import render_confidence_section
from institutional_communication.renderers.evidence import render_evidence_section
from institutional_communication.renderers.framework import render_framework_section
from institutional_communication.renderers.risk import render_risk_section
from institutional_communication.replay.section import render_replay_sections
from institutional_communication.schema import FREEZE_LOCKS, ICE_VERSION, MODULE_CODE, PROGRAMME
from institutional_communication.styles.institutional import bullet, clean_line
from institutional_communication.templates.catalog import get_template


def render_communication(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    plan = plan_communication(institutional_answer)
    template = get_template(plan["template"])
    sections_out: dict[str, dict[str, Any]] = {}

    # Evidence before conclusions
    sections_out["evidence"] = render_evidence_section(institutional_answer)
    sections_out["framework_used"] = render_framework_section(institutional_answer)
    sections_out["risks"] = render_risk_section(institutional_answer)
    sections_out["confidence"] = render_confidence_section(institutional_answer)
    sections_out["sources"] = render_sources_section(institutional_answer)

    # Analysis from existing assembly / bound bullets only
    src_sections = institutional_answer.get("sections") or {}
    analysis_bullets = []
    for key in ("analysis", "conclusion", "executive_summary"):
        for b in (src_sections.get(key) or {}).get("bullets") or []:
            line = clean_line(str(b), max_len=240)
            if not line:
                continue
            # Drop governance scaffolding noise / generic markers
            low = line.lower()
            if low.startswith("governance path:"):
                continue
            if "business strength rated c" in low:
                continue
            if "valuation question blocked" in low:
                continue
            if low.startswith("analyse via") or low.startswith("analyze via"):
                continue
            if "framework input domain" in low or low.startswith("intent:"):
                continue
            if "fill from existing reasoning" in low or "no unsupported certainty" in low:
                continue
            if low.startswith("this matters because"):
                continue
            analysis_bullets.append(bullet(line))

    # AGIB v3.5 — surface Institutional Analytical Playbook checklist / procedure
    playbook = institutional_answer.get("playbook") or {}
    playbook_bullets = _playbook_analysis_bullets(playbook)
    if playbook_bullets:
        # Playbook procedure leads analysis when prior bullets are thin/generic
        if len(analysis_bullets) <= 2:
            analysis_bullets = playbook_bullets + analysis_bullets
        else:
            analysis_bullets = analysis_bullets[:4] + playbook_bullets + analysis_bullets[4:]

    if not analysis_bullets:
        analysis_bullets.append(
            bullet(
                "Analysis limited to retrieved evidence and selected frameworks — "
                "no additional synthesis invented by the communication layer."
            )
        )
    # Evidence-id tags for first few evidence items
    for item in ((institutional_answer.get("evidence") or {}).get("items") or [])[:5]:
        eid = item.get("evidence_id")
        if eid:
            analysis_bullets.append(bullet(f"Supported by evidence id {eid}"))
    sections_out["analysis"] = {
        "section": "analysis",
        "title": "Analysis",
        "bullets": analysis_bullets[:18],
        "visible": True,
        "playbook_id": playbook.get("playbook_id"),
    }

    if playbook.get("playbook_id"):
        sections_out["analytical_checklist"] = {
            "section": "analytical_checklist",
            "title": "Analytical Checklist",
            "bullets": playbook_bullets[:14] or [bullet(f"Playbook: {playbook.get('playbook_name')}")],
            "visible": True,
            "playbook_id": playbook.get("playbook_id"),
        }

    # AGIB v3.6 Sprint 2.2 — Historical Analogues section (validated memories only)
    im = institutional_answer.get("institutional_memory") or {}
    analog_bullets = _analog_bullets(im)
    if analog_bullets:
        sections_out["historical_analogues"] = {
            "section": "historical_analogues",
            "title": "Historical Analogues",
            "bullets": analog_bullets[:12],
            "visible": True,
            "top_memory_ids": im.get("top_memory_ids") or [],
            "have_we_seen_this_before": True,
        }
        # Prefetch analog lessons into analysis when thin
        if len(analysis_bullets) <= 3:
            analysis_bullets = analog_bullets[:4] + analysis_bullets
            sections_out["analysis"]["bullets"] = analysis_bullets[:18]

    # Executive summary — framework-first / evidence-first per template lead
    exec_lines = _executive_summary(institutional_answer, plan, template, sections_out)
    sections_out["executive_summary"] = {
        "section": "executive_summary",
        "title": "Executive Summary",
        "bullets": exec_lines,
        "visible": True,
    }

    if plan["template"] == "historical_replay":
        sections_out.update(render_replay_sections(institutional_answer))

    # Ordered final text — insert analytical checklist after framework when present
    section_names = list(template["sections"])
    if "analytical_checklist" in sections_out and "analytical_checklist" not in section_names:
        if "framework_used" in section_names:
            idx = section_names.index("framework_used") + 1
            section_names.insert(idx, "analytical_checklist")
        else:
            section_names.insert(0, "analytical_checklist")
    if "historical_analogues" in sections_out and "historical_analogues" not in section_names:
        if "evidence" in section_names:
            idx = section_names.index("evidence") + 1
            section_names.insert(idx, "historical_analogues")
        else:
            section_names.append("historical_analogues")

    ordered_sections = []
    for name in section_names:
        sec = sections_out.get(name)
        if not sec:
            continue
        ordered_sections.append(sec)

    prose_blocks = []
    for sec in ordered_sections:
        prose_blocks.append(sec.get("title") or sec.get("section"))
        prose_blocks.extend(sec.get("bullets") or [])
        prose_blocks.append("")

    executive_text = " ".join(
        clean_line(b.lstrip("- ").strip(), max_len=200)
        for b in (sections_out["executive_summary"].get("bullets") or [])[:4]
        if b
    )
    why = []
    for name in (
        "framework_used",
        "analytical_checklist",
        "evidence",
        "historical_analogues",
        "analysis",
        "risks",
        "confidence",
    ):
        for b in (sections_out.get(name) or {}).get("bullets") or []:
            why.append(b.lstrip("- ").strip())
            if len(why) >= 14:
                break
        if len(why) >= 14:
            break

    return {
        "ok": True,
        "ice_version": ICE_VERSION,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "plan": plan,
        "template": template["id"],
        "template_title": template["title"],
        "sections": {s["section"]: s for s in ordered_sections},
        "section_order": [s["section"] for s in ordered_sections],
        "executive_summary": executive_text,
        "summary": executive_text,
        "why": why,
        "prose": "\n".join(prose_blocks).strip(),
        "framework_visible": bool((sections_out.get("framework_used") or {}).get("framework_ids")),
        "playbook_visible": bool(playbook.get("playbook_id")),
        "playbook_id": playbook.get("playbook_id"),
        "evidence_graph_visible": bool(
            ((institutional_answer.get("evidence_graph") or {}).get("graph_id"))
            or ((institutional_answer.get("evidence_graph") or {}).get("n_nodes"))
        ),
        "evidence_graph_id": (institutional_answer.get("evidence_graph") or {}).get("graph_id"),
        "institutional_memory_visible": bool(analog_bullets),
        "top_memory_ids": im.get("top_memory_ids") or [],
        "have_we_seen_this_before": bool(im.get("have_we_seen_this_before")),
        "citation_density": plan.get("citation_density"),
        "narrative_style": plan.get("narrative_style"),
        "consumes_institutional_answer": True,
        "generic_template": False,
        "llm_used": False,
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
        "freeze_locks": FREEZE_LOCKS,
    }


def _analog_bullets(institutional_memory: dict[str, Any]) -> list[str]:
    if not institutional_memory or not institutional_memory.get("have_we_seen_this_before"):
        return []
    lines: list[str] = [
        bullet("Have we seen this before? — validated historical analogues (IMAI)")
    ]
    for b in (institutional_memory.get("surface_bullets") or [])[:5]:
        lines.append(bullet(clean_line(str(b), max_len=280)))
    comp = institutional_memory.get("comparison") or {}
    for lesson in (comp.get("similarities") or [])[:3]:
        lines.append(bullet(clean_line(f"Lesson from history: {lesson}", max_len=240)))
    for diff in (comp.get("differences") or [])[:2]:
        lines.append(bullet(clean_line(f"Difference vs today: {diff}", max_len=220)))
    return lines


def _playbook_analysis_bullets(playbook: dict[str, Any]) -> list[str]:
    if not playbook or not playbook.get("playbook_id"):
        return []
    lines: list[str] = []
    name = playbook.get("playbook_name") or playbook.get("playbook_id")
    lines.append(bullet(f"Analytical playbook: {name}"))
    proc = playbook.get("procedure") or {}
    arrow = proc.get("arrow_text")
    if arrow:
        lines.append(bullet(clean_line(f"Procedure: {arrow}", max_len=320)))
    for step in (playbook.get("checklist") or {}).get("steps") or []:
        label = step.get("label")
        if not label:
            continue
        mark = "□" if step.get("status") == "pending" else "▣"
        lines.append(bullet(f"{mark} {label}"))
        if len(lines) >= 14:
            break
    mistakes = playbook.get("common_mistakes") or []
    if mistakes:
        lines.append(bullet(clean_line(f"Avoid: {mistakes[0]}", max_len=220)))
    return lines


def _executive_summary(
    institutional_answer: dict[str, Any],
    plan: dict[str, Any],
    template: dict[str, Any],
    sections_out: dict[str, dict[str, Any]],
) -> list[str]:
    """User-facing lead: evidence/analysis first. Framework labels stay in framework_used."""
    lines: list[str] = []

    # Prefer substantive analysis / conclusion bullets already bound upstream.
    for key in ("analysis", "conclusion", "executive_summary"):
        for b in ((institutional_answer.get("sections") or {}).get(key) or {}).get("bullets") or []:
            line = clean_line(str(b), max_len=260)
            if not line:
                continue
            low = line.lower()
            if low.startswith("intent:") or low.startswith("frameworks applied"):
                continue
            if "playbook:" in low and "checklist" in low:
                continue
            if low.startswith("governance path:"):
                continue
            if "business strength rated c" in low:
                continue
            if "valuation question blocked" in low:
                continue
            if low.startswith("analyse via") or low.startswith("analyze via"):
                continue
            if "framework input domain" in low or "entity-bound analysis" in low:
                continue
            if "evidence coverage=" in low or "concept mode" == low:
                continue
            if "committee vote" in low or "only when franchise" in low:
                continue
            if "fill from existing reasoning" in low or "no unsupported certainty" in low:
                continue
            if low.startswith("this matters because"):
                continue
            lines.append(bullet(line))
            if len(lines) >= 3:
                break
        if len(lines) >= 3:
            break

    # Prefer evidence titles over framework explanation as the user-facing lead.
    for item in ((institutional_answer.get("evidence") or {}).get("items") or [])[:3]:
        if len(lines) >= 4:
            break
        title = item.get("title") or item.get("evidence_type") or item.get("source")
        if title:
            lines.append(bullet(clean_line(f"Evidence: {title}", max_len=220)))

    expl = ((institutional_answer.get("frameworks") or {}).get("explanation") or {}).get("reason")
    if expl and len(lines) < 3:
        elow = str(expl).lower()
        if "analyse via" not in elow and "frameworks applied" not in elow:
            lines.append(bullet(clean_line(str(expl), max_len=260)))

    im = institutional_answer.get("institutional_memory") or {}
    if im.get("have_we_seen_this_before") and (im.get("top_memory_ids") or im.get("surface_bullets")):
        n_mem = len(im.get("top_memory_ids") or im.get("surface_bullets") or [])
        lines.append(
            bullet(
                clean_line(
                    f"Have we seen this before? — {n_mem} validated historical analogue(s).",
                    max_len=220,
                )
            )
        )

    if plan.get("as_of"):
        lines.append(bullet(f"Historical replay as_of={plan.get('as_of')} — current prices excluded."))

    if institutional_answer.get("concept_mode"):
        lines.append(bullet("Concept mode — no company entity forced into the narrative."))

    # Thin fallback — evidence count only; never Intent/Template/Playbook scaffolding.
    if not lines:
        n_ev = len(((institutional_answer.get("evidence") or {}).get("items") or []))
        q = clean_line(str(institutional_answer.get("question") or ""), max_len=120)
        lines.append(
            bullet(
                clean_line(
                    (
                        f"Retrieved {n_ev} evidence item(s) for the question"
                        + (f" “{q}”" if q else "")
                        + "; synthesis limited to bound evidence."
                    ),
                    max_len=260,
                )
            )
        )

    band = (sections_out.get("confidence") or {}).get("band")
    if band and len(lines) < 5:
        lines.append(bullet(f"Confidence: {band}."))

    return lines[:5]
