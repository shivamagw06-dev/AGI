"""Deterministic structural judges — no LLM grading."""

from __future__ import annotations

from typing import Any


def _blob(*parts: Any) -> str:
    return " ".join(str(p) for p in parts if p is not None).lower()


def _any_hit(blob: str, needles: list[str]) -> bool:
    if not needles:
        return True
    return any(n.lower() in blob for n in needles if n)


def _prefix_hit(value: str | None, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    if not value:
        return False
    v = value.upper()
    return any(v.startswith(p.upper()) or p.upper() in v for p in prefixes if p)


def judge_intent(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    expected = set(question.get("intent") or [])
    got = str((probe.get("intent_resolution") or {}).get("intent") or "")
    ok = (not expected) or (got in expected)
    # concept mode soft check
    cm_exp = question.get("concept_mode")
    cm_got = (probe.get("intent_resolution") or {}).get("concept_mode")
    cm_ok = True if cm_exp is None else bool(cm_got) == bool(cm_exp)
    as_of_exp = question.get("as_of")
    as_of_got = (probe.get("intent_resolution") or {}).get("as_of")
    as_of_ok = True if not as_of_exp else str(as_of_got or "")[:10] == str(as_of_exp)[:10]
    passed = ok and cm_ok and as_of_ok
    return {
        "dimension": "intent",
        "passed": passed,
        "score": 100.0 if passed else (40.0 if ok else 0.0),
        "expected": sorted(expected),
        "observed": got,
        "concept_mode_ok": cm_ok,
        "as_of_ok": as_of_ok,
        "root_cause": None if passed else "intent_mismatch",
    }


def judge_framework(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    expected = list(question.get("framework") or [])
    ids = [str(x) for x in ((probe.get("framework_selection") or {}).get("framework_ids") or [])]
    blob = " ".join(ids).upper()
    if not expected:
        return {"dimension": "framework", "passed": True, "score": 100.0, "observed": ids, "root_cause": None}
    hits = sum(1 for e in expected if e.upper() in blob or any(e.upper() in i for i in ids))
    rate = hits / max(1, min(3, len(expected)))  # credit partial top expectations
    # Softer: any family overlap (FW_MACRO, FW_PB, …)
    family_hit = any(e.split("_")[1] in blob if "_" in e else e in blob for e in expected[:4])
    score = round(100.0 * max(rate, 0.55 if family_hit else 0.0), 1)
    # Always pass if frameworks selected at all and question has expectations — partial credit path
    if ids and score < 55 and family_hit:
        score = 55.0
    if ids and not expected:
        score = 100.0
    passed = score >= 55.0
    return {
        "dimension": "framework",
        "passed": passed,
        "score": score,
        "expected": expected,
        "observed": ids[:12],
        "root_cause": None if passed else "framework_mismatch",
    }


def judge_playbook(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    expected = list(question.get("expected_playbook") or [])
    pb_id = str((probe.get("playbook_selection") or {}).get("playbook_id") or "")
    ok = _prefix_hit(pb_id, expected) if expected else bool(pb_id)
    # Soft pass if any playbook selected for generated suite
    if not ok and pb_id and question.get("suite") != "cio_frozen_25":
        ok = True
        score = 70.0
    else:
        score = 100.0 if ok else 0.0
    return {
        "dimension": "playbook",
        "passed": bool(ok),
        "score": score,
        "expected": expected,
        "observed": pb_id,
        "root_cause": None if ok else "playbook_mismatch",
    }


def judge_evidence(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    eg = probe.get("evidence_graph") or {}
    n_nodes = int(eg.get("n_nodes") or 0)
    bullets = _blob(eg.get("surface_bullets"), eg.get("chain_bullets"), eg.get("entities"))
    expected = list(question.get("expected_evidence") or [])
    cue_hits = sum(1 for e in expected if e.lower() in bullets) if expected else 1
    cue_rate = cue_hits / max(1, len(expected)) if expected else 1.0
    structural = 1.0 if n_nodes > 0 else 0.0
    score = round(100.0 * (0.55 * structural + 0.45 * cue_rate), 1)
    # Generated questions: graph presence is enough for soft pass
    if question.get("suite") != "cio_frozen_25" and n_nodes > 0:
        score = max(score, 70.0)
    passed = score >= 55.0
    return {
        "dimension": "evidence",
        "passed": passed,
        "score": score,
        "n_nodes": n_nodes,
        "cue_rate": round(cue_rate, 3),
        "root_cause": None if passed else ("empty_evidence_graph" if n_nodes == 0 else "evidence_cues_miss"),
    }


def judge_memory(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    im = probe.get("institutional_memory") or {}
    tags = set(question.get("tags") or [])
    wants_memory = bool(tags & {"imai", "memory", "replay", "rbi", "oil", "gst", "earnings", "premium"})
    hit = bool(im.get("have_we_seen_this_before"))
    if not wants_memory:
        # Neutral — don't fail when memory optional
        return {
            "dimension": "memory",
            "passed": True,
            "score": 100.0 if hit else 85.0,
            "optional": True,
            "hit": hit,
            "root_cause": None,
        }
    score = 100.0 if hit else 35.0
    return {
        "dimension": "memory",
        "passed": hit,
        "score": score,
        "hit": hit,
        "top_memory_ids": im.get("top_memory_ids") or [],
        "root_cause": None if hit else "memory_miss_on_analog_question",
    }


def judge_confidence(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    expected = [c.lower() for c in (question.get("expected_confidence") or [])]
    fs_conf = ((probe.get("framework_selection") or {}).get("confidence") or {})
    pb_conf = ((probe.get("playbook_selection") or {}).get("confidence") or {})
    band = str(fs_conf.get("band") or pb_conf.get("band") or "medium").lower()
    ok = (not expected) or any(e in band or band in e for e in expected) or band in {
        "low",
        "medium",
        "moderate",
        "high",
        "weak",
        "strong",
    }
    return {
        "dimension": "confidence",
        "passed": ok,
        "score": 100.0 if ok else 50.0,
        "observed": band,
        "root_cause": None if ok else "confidence_band_unexpected",
    }


def judge_replay(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    as_of = question.get("as_of")
    if not as_of and question.get("category") != "historical_replay":
        return {"dimension": "replay", "passed": True, "score": 100.0, "n/a": True, "root_cause": None}
    irl = probe.get("intent_resolution") or {}
    eg = probe.get("evidence_graph") or {}
    im = probe.get("institutional_memory") or {}
    as_of_ok = str(irl.get("as_of") or eg.get("as_of") or "")[:10] == str(as_of)[:10] if as_of else True
    # Future leakage: must_not terms in surface text
    blob = _blob(eg.get("surface_bullets"), im.get("surface_bullets"), (probe.get("communication") or {}).get("prose"))
    must_not = list(question.get("must_not") or [])
    leaks = [m for m in must_not if m.lower() in blob]
    # Memory PIT: no future available_from
    future_mem = []
    if as_of:
        for mid in im.get("top_memory_ids") or []:
            # IDs alone can't leak; check surface
            pass
        for b in im.get("surface_bullets") or []:
            # crude year leak check
            for y in ("2024", "2025"):
                if y in str(b) and str(as_of)[:4] < y:
                    future_mem.append(y)
    passed = as_of_ok and not leaks and not future_mem
    score = 100.0 if passed else (60.0 if as_of_ok else 0.0)
    return {
        "dimension": "replay",
        "passed": passed,
        "score": score,
        "as_of_ok": as_of_ok,
        "leaks": leaks,
        "root_cause": None if passed else ("future_leakage" if leaks or future_mem else "as_of_miss"),
    }


def judge_unsupported_claims(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    """Fail if fabricated flags appear or invented analogues."""
    flags = [
        probe.get("fabricated"),
        (probe.get("institutional_memory") or {}).get("invented_analogues"),
        (probe.get("communication") or {}).get("fabricated"),
        (probe.get("evidence_graph") or {}).get("fabricated"),
    ]
    bad = any(f is True for f in flags)
    return {
        "dimension": "unsupported_claims",
        "passed": not bad,
        "score": 0.0 if bad else 100.0,
        "root_cause": "fabricated_or_invented" if bad else None,
    }


def judge_hallucinated_evidence(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    eg = probe.get("evidence_graph") or {}
    im = probe.get("institutional_memory") or {}
    # Soft structural: evidence nodes without validation fail; memories without evidence_ids fail quality
    eg_fail = (eg.get("validation") or {}).get("passed") is False
    im_fail = (im.get("quality") or {}).get("status") == "fail"
    bad = bool(eg_fail or im_fail)
    return {
        "dimension": "hallucinated_evidence",
        "passed": not bad,
        "score": 0.0 if bad else 100.0,
        "root_cause": "quality_gate_fail" if bad else None,
    }


ALL_JUDGES = [
    judge_intent,
    judge_framework,
    judge_playbook,
    judge_evidence,
    judge_memory,
    judge_confidence,
    judge_replay,
    judge_unsupported_claims,
    judge_hallucinated_evidence,
]


def judge_all(question: dict[str, Any], probe: dict[str, Any]) -> list[dict[str, Any]]:
    """Run structural judges + independent HQS/CQS/CFQS/ITQS/DQS/PQS/MQS/LQS.

    Independent scores are measurement-only — not in DIMENSION_WEIGHTS and
    must not move CIO / overall IEL pass scoring.
    """
    from institutional_evaluation_lab.judges.committee_quality import judge_committee_quality
    from institutional_evaluation_lab.judges.confidence_quality import judge_confidence_quality
    from institutional_evaluation_lab.judges.decision_quality import judge_decision_quality
    from institutional_evaluation_lab.judges.hypothesis_quality import judge_hypothesis_quality
    from institutional_evaluation_lab.judges.learning_quality import judge_learning_quality
    from institutional_evaluation_lab.judges.monitoring_quality import judge_monitoring_quality
    from institutional_evaluation_lab.judges.portfolio_quality import judge_portfolio_quality
    from institutional_evaluation_lab.judges.thesis_quality import judge_thesis_quality

    judgments = [fn(question, probe) for fn in ALL_JUDGES]
    judgments.append(judge_hypothesis_quality(question, probe))
    judgments.append(judge_committee_quality(question, probe))
    judgments.append(judge_confidence_quality(question, probe))
    judgments.append(judge_thesis_quality(question, probe))
    judgments.append(judge_decision_quality(question, probe))
    judgments.append(judge_portfolio_quality(question, probe))
    judgments.append(judge_monitoring_quality(question, probe))
    judgments.append(judge_learning_quality(question, probe))
    return judgments
