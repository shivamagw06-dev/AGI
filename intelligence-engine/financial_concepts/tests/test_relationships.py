"""Module 9 — Concept Relationships graph."""

from __future__ import annotations

import pytest

from financial_concepts.concepts import all_concept_keys
from financial_concepts.relationships import (
    graph_summary,
    isolated_concepts,
    neighbors,
    shortest_path,
)

ALL_KEYS = all_concept_keys()


def test_graph_has_no_isolated_concepts():
    isolated = isolated_concepts()
    assert isolated == [], f"{len(isolated)} concepts have zero connections: {isolated}"


def test_graph_summary_reports_sane_totals():
    summary = graph_summary()
    assert summary["nodes"] == len(ALL_KEYS)
    assert summary["edges"] > 100
    assert summary["isolated_nodes"] == 0
    assert summary["avg_degree"] > 1.0


@pytest.mark.parametrize("key", ALL_KEYS)
def test_every_concept_has_at_least_one_neighbor(key):
    assert len(neighbors(key)) >= 1, f"{key} is isolated in the relationship graph"


def test_illustrative_brief_chain_ev_to_credit_risk():
    # "Enterprise Value -> Net Debt -> Interest Expense -> Coverage ->
    # Credit Risk -> Cost of Capital -> Valuation" (Phase 2.6 brief, Module 9)
    path = shortest_path("enterprise_value", "default_risk")
    assert path is not None
    assert path[0] == "enterprise_value"
    assert path[-1] == "default_risk"
    assert len(path) <= 6


def test_illustrative_brief_chain_roe_to_leverage():
    # "ROE -> DuPont -> Margin -> Turnover -> Leverage" (Phase 2.6 brief, Module 9)
    path = shortest_path("roe_decomposition", "financial_leverage")
    assert path is not None
    assert "roe_decomposition" in path
    assert "financial_leverage" in path


def test_path_to_self_is_trivial():
    assert shortest_path("wacc", "wacc") == ["wacc"]


def test_path_between_unknown_keys_is_none():
    assert shortest_path("not_a_real_concept", "wacc") is None
    assert shortest_path("wacc", "not_a_real_concept") is None


def test_neighbors_are_bidirectional():
    for key in ("wacc", "roic", "enterprise_value"):
        for neighbor in neighbors(key):
            assert key in neighbors(neighbor), f"{key} -> {neighbor} is not reciprocated"
