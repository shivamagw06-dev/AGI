"""Research Memory Regression — structured memory updates without history rewrite.

Verifies AGI:
  - remembers previously structured research
  - updates rather than duplicating
  - preserves historical context
  - never rewrites history without evidence
"""

from __future__ import annotations

from typing import Any, Dict, List

from research_intelligence.corpus import CORPUS, get_corpus
from research_intelligence.engines import research_memory

MEMORY_REGRESSION: List[Dict[str, Any]] = []


def _add(prompt: str, entity: str, *, kind: str, must_any: List[str]):
    MEMORY_REGRESSION.append(
        {
            "id": f"RMR-{len(MEMORY_REGRESSION)+1:02d}",
            "prompt": prompt,
            "entity": entity,
            "kind": kind,
            "must_any": must_any,
            "section": "research_memory",
            "category": kind,
        }
    )


for key, c in CORPUS.items():
    name = c["name"]
    _add(
        f"What does research memory store for {name}?",
        key,
        kind="remember",
        must_any=["memory", "conclusion", "theme"],
    )
    _add(
        f"What changed since last quarter in {name} research memory?",
        key,
        kind="update_not_duplicate",
        must_any=["memory", "change", "quarter"],
    )
    _add(
        f"Explain why {name} research should never be duplicated.",
        key,
        kind="no_duplication",
        must_any=["duplicate", "memory", "update"],
    )
    _add(
        f"List research conclusions and recurring themes for {name}.",
        key,
        kind="preserve_context",
        must_any=["conclusion", "theme", "recur"],
    )
    _add(
        f"How has management evolved for {name} according to research memory?",
        key,
        kind="no_history_rewrite",
        must_any=["management", "memory", "history"],
    )

assert len(MEMORY_REGRESSION) == 25, len(MEMORY_REGRESSION)


def evaluate_memory_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    c = get_corpus(case["entity"])
    assert c is not None
    mem = c.get("memory") or {}
    engine = research_memory(c)
    summary = (payload.get("executive_summary") or payload.get("summary") or "").lower()
    blob = summary + " " + str(payload.get("memory") or "").lower() + " " + str(engine.get("summary") or "").lower()

    must = case["must_any"]
    hits = sum(1 for m in must if m.lower() in blob)
    topic_ok = hits >= min(2, len(must))

    # Must expose structured memory fields (remembers prior research)
    remembers = bool(mem.get("conclusions")) and bool(mem.get("recurring_themes"))

    # Update rather than duplicate
    dedupe = str(mem.get("dedupe_policy") or "").lower()
    no_dup_policy = any(tok in dedupe for tok in ("duplicate", "update", "not re-create", "never duplicate"))
    no_dup_in_answer = any(tok in blob for tok in ("duplicate", "update", "persist", "memory"))

    # Preserve historical context
    history_ok = bool(mem.get("company_history") or mem.get("management_history") or mem.get("guidance_history_note"))

    # Never rewrite history without evidence — corpus must stay non-fabricated;
    # answer must not claim invented quotes / rewritten history.
    no_rewrite = payload.get("fabricated") is not True and not any(
        bad in summary
        for bad in ("rewrote history", "invented quote", "fabricated transcript")
    )
    evidence_ok = bool(payload.get("evidence")) or bool(c.get("documents"))

    no_reco = payload.get("recommendation") in (None, "", "none")
    passed = (
        topic_ok
        and remembers
        and no_dup_policy
        and no_dup_in_answer
        and history_ok
        and no_rewrite
        and evidence_ok
        and no_reco
        and bool(summary)
    )
    return {
        "id": case["id"],
        "kind": case["kind"],
        "prompt": case["prompt"],
        "entity": case["entity"],
        "pass": passed,
        "remembers": remembers,
        "no_duplication": no_dup_policy and no_dup_in_answer,
        "preserves_history": history_ok,
        "no_history_rewrite": no_rewrite,
        "topic_ok": topic_ok,
        "summary": (payload.get("summary") or "")[:220],
        "failed_assertions": [
            k
            for k, v in {
                "topic_ok": topic_ok,
                "remembers": remembers,
                "no_duplication": no_dup_policy and no_dup_in_answer,
                "preserves_history": history_ok,
                "no_history_rewrite": no_rewrite,
                "evidence_ok": evidence_ok,
                "no_reco": no_reco,
            }.items()
            if not v
        ],
    }
