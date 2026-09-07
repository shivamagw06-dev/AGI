"""ICE quality gates — fail on omitted framework/evidence/risk/confidence/generic."""

from __future__ import annotations

from typing import Any

from institutional_communication.schema import GENERIC_MARKERS, MANDATORY_SECTIONS


def validate_communication(
    rendered: dict[str, Any],
    *,
    institutional_answer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    sections = rendered.get("sections") or {}

    for name in MANDATORY_SECTIONS:
        # historical_replay uses framework_used etc. — mandatory still required
        sec = sections.get(name)
        if name == "framework_used":
            sec = sections.get("framework_used")
        if not sec or not (sec.get("bullets")):
            failures.append(f"omitted:{name}")

    fw = sections.get("framework_used") or {}
    if not fw.get("framework_ids") and not any(
        "framework" in str(b).lower() for b in (fw.get("bullets") or [])
    ):
        failures.append("framework_omitted")

    ev = sections.get("evidence") or {}
    if not ev.get("bullets"):
        failures.append("evidence_omitted")

    if not (sections.get("risks") or {}).get("bullets"):
        failures.append("risk_omitted")
    if not (sections.get("confidence") or {}).get("bullets"):
        failures.append("confidence_omitted")

    text = " ".join(
        [
            str(rendered.get("executive_summary") or ""),
            str(rendered.get("prose") or ""),
            " ".join(rendered.get("why") or []),
        ]
    ).lower()
    for marker in GENERIC_MARKERS:
        if marker in text:
            failures.append(f"generic_template:{marker[:40]}")
            break

    if rendered.get("llm_used"):
        failures.append("llm_narrative_forbidden")
    if rendered.get("fabricated"):
        failures.append("fabricated")

    # Citation missing when evidence items exist
    ia = institutional_answer or {}
    n_ev = len(((ia.get("evidence") or {}).get("items") or []))
    sources = sections.get("sources") or {}
    if n_ev and not (sources.get("bullets")):
        failures.append("citation_missing")

    # Replay contamination — current PE language in historical template
    if (rendered.get("template") == "historical_replay") or ia.get("as_of"):
        if "current pe" in text or "current price" in text:
            failures.append("replay_contamination")

    # Unsupported: executive claiming valuation without frameworks
    if "undervalued" in text and not (fw.get("framework_ids") or ia.get("frameworks", {}).get("framework_ids")):
        failures.append("unsupported_statement")

    failures = sorted(set(failures))
    return {
        "passed": not failures,
        "failures": failures,
        "narrative_completeness": round(
            sum(1 for n in MANDATORY_SECTIONS if (sections.get(n) or {}).get("bullets"))
            / max(len(MANDATORY_SECTIONS), 1),
            4,
        ),
        "fabricated": False,
    }
