"""Classify company_metadata_routing failures. A score is not a diagnosis.

The suite scores 51.47% and the register called it P0 on that alone. The
per-case artifact says something more useful: of 33 failing cases, 37 failure
labels resolve to four different problems with different owners and different
severities.

    not_routed_to_metadata   25   the ask never reached the metadata engine
    wrong_intent              6   routed, wrong intent
    wrong_sources             6   routed, wrong sources
    expected_value_missing    6   reached it, no value came back
    bound_namesake            2   bound to the wrong company

Only the last is wrong-company in the sense that makes a release unsafe. The
first three are one routing defect seen from three angles. Treating all 33 as
P0 would put most of the effort into a category that is a routing bug, and the
two cases that actually bind the wrong entity would compete with them for
attention.
"""

from __future__ import annotations

import collections
from typing import Any, Dict, Iterable, List

WRONG_COMPANY = "wrong_company"
MISSING_METADATA = "missing_metadata"
INCOMPLETE_COMPARISON = "incomplete_comparison"
FORMATTING = "formatting"
ROUTING = "routing"
HALLUCINATION = "hallucination"
REGISTRY_GAP = "registry_gap"
UNCLASSIFIED = "unclassified"

#: Label prefix -> category. Prefixes because several labels carry a value
#: after a colon (`wrong_value:X!=Y`, `field_not_answered:sector`).
LABEL_CATEGORY: Dict[str, str] = {
    # bound to the wrong entity - the release-unsafe case
    "bound_namesake": WRONG_COMPANY,
    "wrong_value": WRONG_COMPANY,
    "wrong_entity": WRONG_COMPANY,
    "unknown_entity_refusal": WRONG_COMPANY,
    # reached the right place, nothing came back
    "expected_value_missing": MISSING_METADATA,
    "field_not_answered": MISSING_METADATA,
    "metadata_field_missing": MISSING_METADATA,
    # the registry itself does not carry it - a coverage gap, not a defect in
    # the answer path
    "field_missing_in_registry": REGISTRY_GAP,
    # never reached the metadata engine, or reached it as the wrong thing
    "not_routed_to_metadata": ROUTING,
    "not_metadata_route": ROUTING,
    "wrong_intent": ROUTING,
    "wrong_sources": ROUTING,
    "metadata_wrong_sources": ROUTING,
    # comparison that silently drops a side
    "comparison_omits_entity": INCOMPLETE_COMPARISON,
    "comparison_both": INCOMPLETE_COMPARISON,
    # invented an answer to an unanswerable ask, or hedged nothing
    "no_honest_uncertainty": HALLUCINATION,
    "fabricated_specifics": HALLUCINATION,
    # presentation only
    "thin_answer": FORMATTING,
    "empty_answer": FORMATTING,
}

#: Which categories make a release unsafe, as distinct from which are common.
RELEASE_CRITICAL = (HALLUCINATION, WRONG_COMPANY, INCOMPLETE_COMPARISON)


def categorise(label: str) -> str:
    return LABEL_CATEGORY.get(str(label or "").split(":", 1)[0], UNCLASSIFIED)


def classify(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Group a suite's failing cases by what actually went wrong."""
    by_category: collections.Counter = collections.Counter()
    by_label: collections.Counter = collections.Counter()
    cases: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    failing = 0

    for result in results:
        labels = result.get("failed") or []
        if not labels:
            continue
        failing += 1
        for label in labels:
            category = categorise(label)
            by_category[category] += 1
            by_label[str(label).split(":", 1)[0]] += 1
            cases[category].append({
                "id": result.get("id"),
                "label": label,
                "question": result.get("question"),
            })

    critical = sum(by_category[c] for c in RELEASE_CRITICAL)
    return {
        "failing_cases": failing,
        "labels_total": sum(by_category.values()),
        "by_category": dict(by_category.most_common()),
        "by_label": dict(by_label.most_common()),
        "release_critical_labels": critical,
        "release_critical_categories": list(RELEASE_CRITICAL),
        "examples": {k: v[:5] for k, v in cases.items()},
        "note": ("category counts label occurrences, not cases; one case can "
                 "carry several labels"),
    }
