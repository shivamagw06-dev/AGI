"""Module 5 — Change Detection.

Compares the structured knowledge stored for a company across two periods
(e.g. FY26 vs FY25) and produces structured :class:`~kip_v2.schema.ChangeDelta`
records: new/removed risks & strategy points, capex/debt/dividend changes,
guidance changes, M&A activity. Operates purely on already-stored Facts —
never re-reads or re-parses the original documents.
"""

from __future__ import annotations

import difflib

from kip_v2.schema import ChangeDelta, Fact, sha256_hex

# Categorical (text) knowledge where "new" / "removed" comparisons apply.
_CATEGORICAL_CATEGORIES = ("risks", "strategy", "products", "mna", "capital_allocation")

_SIMILARITY_THRESHOLD = 0.6
_MATERIAL_CHANGE_PCT = 5.0


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _delta_id(company_id: str, category: str, key: str, from_period: str, to_period: str, suffix: str) -> str:
    return sha256_hex(company_id, category, key, from_period, to_period, suffix)[:24]


def detect_categorical_changes(
    company_id: str, category: str, old_facts: list[Fact], new_facts: list[Fact], from_period: str, to_period: str
) -> list[ChangeDelta]:
    deltas: list[ChangeDelta] = []
    matched_old: set[int] = set()
    matched_new: set[int] = set()

    for ni, nf in enumerate(new_facts):
        for oi, of in enumerate(old_facts):
            if oi in matched_old:
                continue
            if _similar(str(nf.value), str(of.value)) >= _SIMILARITY_THRESHOLD:
                matched_old.add(oi)
                matched_new.add(ni)
                break

    for ni, nf in enumerate(new_facts):
        if ni in matched_new:
            continue
        deltas.append(
            ChangeDelta(
                delta_id=_delta_id(company_id, category, nf.key, from_period, to_period, f"new{ni}"),
                company_id=company_id, category=category, key=nf.key, change_type="new",
                from_period=from_period, to_period=to_period, old_value=None, new_value=nf.value,
                new_evidence=nf.evidence.to_dict(),
            )
        )
    for oi, of in enumerate(old_facts):
        if oi in matched_old:
            continue
        deltas.append(
            ChangeDelta(
                delta_id=_delta_id(company_id, category, of.key, from_period, to_period, f"removed{oi}"),
                company_id=company_id, category=category, key=of.key, change_type="removed",
                from_period=from_period, to_period=to_period, old_value=of.value, new_value=None,
                old_evidence=of.evidence.to_dict(),
            )
        )
    return deltas


def detect_numeric_change(
    company_id: str, metric: str, old_fact: Fact | None, new_fact: Fact | None, from_period: str, to_period: str
) -> ChangeDelta | None:
    if old_fact is None and new_fact is None:
        return None
    if old_fact is None:
        return ChangeDelta(
            delta_id=_delta_id(company_id, "financial_metric", metric, from_period, to_period, "new"),
            company_id=company_id, category="financial_metric", key=metric, change_type="new",
            from_period=from_period, to_period=to_period, old_value=None, new_value=new_fact.value,
            new_evidence=new_fact.evidence.to_dict(),
        )
    if new_fact is None:
        return ChangeDelta(
            delta_id=_delta_id(company_id, "financial_metric", metric, from_period, to_period, "removed"),
            company_id=company_id, category="financial_metric", key=metric, change_type="removed",
            from_period=from_period, to_period=to_period, old_value=old_fact.value, new_value=None,
            old_evidence=old_fact.evidence.to_dict(),
        )
    old_v, new_v = float(old_fact.value), float(new_fact.value)
    pct = None if old_v == 0 else round((new_v - old_v) / abs(old_v) * 100.0, 2)
    if pct is None:
        change_type = "changed" if new_v != old_v else "unchanged"
    elif pct > _MATERIAL_CHANGE_PCT:
        change_type = "increased"
    elif pct < -_MATERIAL_CHANGE_PCT:
        change_type = "decreased"
    else:
        change_type = "unchanged"
    return ChangeDelta(
        delta_id=_delta_id(company_id, "financial_metric", metric, from_period, to_period, "cmp"),
        company_id=company_id, category="financial_metric", key=metric, change_type=change_type,
        from_period=from_period, to_period=to_period, old_value=old_v, new_value=new_v,
        old_evidence=old_fact.evidence.to_dict(), new_evidence=new_fact.evidence.to_dict(), magnitude_pct=pct,
    )


def detect_changes(
    company_id: str,
    from_period: str,
    to_period: str,
    old_facts: list[Fact],
    new_facts: list[Fact],
) -> list[ChangeDelta]:
    """Top-level entry: buckets facts by category/key and dispatches to the
    categorical or numeric comparator."""

    deltas: list[ChangeDelta] = []

    for category in _CATEGORICAL_CATEGORIES:
        old_bucket = [f for f in old_facts if f.category == category]
        new_bucket = [f for f in new_facts if f.category == category]
        if old_bucket or new_bucket:
            deltas.extend(detect_categorical_changes(company_id, category, old_bucket, new_bucket, from_period, to_period))

    old_metrics = {f.key: f for f in old_facts if f.category == "financial_metric"}
    new_metrics = {f.key: f for f in new_facts if f.category == "financial_metric"}
    for metric in set(old_metrics) | set(new_metrics):
        delta = detect_numeric_change(company_id, metric, old_metrics.get(metric), new_metrics.get(metric), from_period, to_period)
        if delta and delta.change_type != "unchanged":
            deltas.append(delta)

    return deltas
