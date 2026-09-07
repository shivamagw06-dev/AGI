"""Cluster failures so one patch can fix many questions."""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import uuid4

from root_cause_intelligence.schema import SEVERITY_RANK


def _framework_family(ids: list[str] | None) -> str:
    if not ids:
        return "none"
    # Prefer expected family token after FW_
    tokens: list[str] = []
    for fid in ids[:4]:
        parts = str(fid).upper().split("_")
        if len(parts) >= 2:
            tokens.append(parts[1])
        else:
            tokens.append(parts[0])
    if not tokens:
        return "none"
    return Counter(tokens).most_common(1)[0][0]


def _playbook_family(pb: str | None, expected: list[str] | None) -> str:
    raw = pb or (expected[0] if expected else "") or "none"
    raw = str(raw).upper()
    if raw.startswith("PB_"):
        bits = raw.split("_")
        return "_".join(bits[:3]) if len(bits) >= 3 else raw[:16]
    return raw[:16] or "none"


def cluster_key(failure: dict[str, Any]) -> str:
    """
    Cluster signature:

    root_cause × sector × framework_family × category × playbook_family
    """
    cause = str(failure.get("root_cause") or "unspecified")
    sector = str(failure.get("sector") or "generic")
    # Prefer expected framework family for "wrong rule" diagnosis
    fam = _framework_family(failure.get("expected_framework") or failure.get("actual_framework"))
    cat = str(failure.get("category") or "unknown")
    pb = _playbook_family(failure.get("actual_playbook"), failure.get("expected_playbook"))
    return f"{cause}|{sector}|{fam}|{cat}|{pb}"


def cluster_failures(failures: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = {}
    for f in failures:
        key = cluster_key(f)
        f["cluster"] = key
        b = buckets.get(key)
        if not b:
            b = {
                "cluster_id": f"clu-{uuid4().hex[:10]}",
                "cluster_key": key,
                "root_cause": f.get("root_cause"),
                "sector": f.get("sector") or "generic",
                "framework_family": _framework_family(
                    f.get("expected_framework") or f.get("actual_framework")
                ),
                "category": f.get("category"),
                "playbook_family": _playbook_family(
                    f.get("actual_playbook"), f.get("expected_playbook")
                ),
                "count": 0,
                "failure_ids": [],
                "question_ids": [],
                "severities": Counter(),
                "expected_frameworks_sample": [],
                "actual_frameworks_sample": [],
                "expected_intents_sample": [],
                "actual_intents_sample": [],
                "owner": f.get("owner"),
                "status": "open",
            }
            buckets[key] = b
        b["count"] += 1
        b["severities"][str(f.get("severity") or "medium")] += 1
        if len(b["failure_ids"]) < 40:
            b["failure_ids"].append(f.get("failure_id"))
            b["question_ids"].append(f.get("question_id"))
        # samples
        for exp in (f.get("expected_framework") or [])[:2]:
            if exp not in b["expected_frameworks_sample"] and len(b["expected_frameworks_sample"]) < 6:
                b["expected_frameworks_sample"].append(exp)
        for act in (f.get("actual_framework") or [])[:2]:
            if act not in b["actual_frameworks_sample"] and len(b["actual_frameworks_sample"]) < 6:
                b["actual_frameworks_sample"].append(act)
        for exp in (f.get("expected_intent") or [])[:1]:
            if exp not in b["expected_intents_sample"] and len(b["expected_intents_sample"]) < 4:
                b["expected_intents_sample"].append(exp)
        act_i = f.get("actual_intent")
        if act_i and act_i not in b["actual_intents_sample"] and len(b["actual_intents_sample"]) < 4:
            b["actual_intents_sample"].append(act_i)

    ranked = sorted(
        buckets.values(),
        key=lambda x: (
            -int(x["count"]),
            SEVERITY_RANK.get(_dominant_severity(x["severities"]), 9),
            x["cluster_key"],
        ),
    )
    for b in ranked:
        sev = _dominant_severity(b["severities"])
        b["severity"] = sev
        b["severities"] = dict(b["severities"])
        b["impact_statement"] = (
            f"{b['count']} questions ↓ {b['root_cause']} ↓ "
            f"{b['sector']} ↓ {b['framework_family']} ↓ one patch"
        )
    return {
        "n_failures": len(failures),
        "n_clusters": len(ranked),
        "top_10": ranked[:10],
        "top_20": ranked[:20],
        "all": ranked,
    }


def _dominant_severity(severities: Counter | dict) -> str:
    if not severities:
        return "medium"
    return sorted(
        severities.items(),
        key=lambda kv: (SEVERITY_RANK.get(kv[0], 9), -kv[1]),
    )[0][0]
