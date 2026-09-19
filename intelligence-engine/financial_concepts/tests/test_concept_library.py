"""Structural validation of every concept card in the library.

Parametrized across all 193 cards — each card gets independently checked
for the Quality-Contract-style requirements the Phase 2.6 brief specifies
(definition, business meaning, evidence level, confidence, no dangling
related-concept references), so a single bad card can never hide inside an
aggregate pass/fail.
"""

from __future__ import annotations

import pytest

from financial_concepts.concepts import (
    ALL_CONCEPTS,
    all_concept_keys,
    concept_count,
    concept_count_by_module,
    get_concept,
    validate_related_concepts,
)
from financial_concepts.schema import EVIDENCE_LEVELS, MODULES

ALL_KEYS = all_concept_keys()


def test_library_has_no_dangling_related_concept_references():
    errors = validate_related_concepts()
    assert errors == [], f"{len(errors)} dangling references: {errors[:10]}"


def test_library_has_no_duplicate_keys_across_modules():
    # ALL_CONCEPTS construction itself raises on duplicates; this just
    # re-confirms the invariant explicitly as a regression guard.
    assert len(ALL_KEYS) == len(set(ALL_KEYS))


def test_concept_count_meets_minimum_bar():
    # Every explicitly named term across all 8 Phase 2.6 modules is covered
    # (verified by test_mission_questions.py), plus substantial legitimate
    # extensions. 150 is a firm floor well above that named-term count.
    assert concept_count() >= 150


def test_every_module_has_at_least_five_concepts():
    counts = concept_count_by_module()
    for module in MODULES:
        assert counts.get(module, 0) >= 5, f"module {module} has too few concepts: {counts.get(module, 0)}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_concept_has_required_fields(key):
    card = get_concept(key)
    assert card is not None
    assert card.key == key
    assert card.module in MODULES
    assert card.title.strip()
    assert card.definition.strip()
    assert card.business_meaning.strip()
    assert card.evidence_level in EVIDENCE_LEVELS
    assert 0.0 <= card.confidence <= 1.0


@pytest.mark.parametrize("key", ALL_KEYS)
def test_concept_definition_is_substantive(key):
    card = get_concept(key)
    assert len(card.definition) >= 20, f"{key} definition too short: {card.definition!r}"
    assert len(card.business_meaning) >= 20, f"{key} business_meaning too short: {card.business_meaning!r}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_concept_related_links_point_to_real_concepts(key):
    card = get_concept(key)
    for related in card.related_concepts:
        assert related in ALL_CONCEPTS, f"{key} references unknown concept {related!r}"
        assert related != key, f"{key} references itself in related_concepts"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_concept_to_dict_roundtrips(key):
    card = get_concept(key)
    d = card.to_dict()
    assert d["key"] == key
    assert d["fabricated"] is False
    assert isinstance(d["related_concepts"], list)


def test_get_concept_returns_none_for_unknown_key():
    assert get_concept("this_concept_does_not_exist") is None
