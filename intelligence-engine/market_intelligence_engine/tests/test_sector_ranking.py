"""Sector leaders and laggards, which were broken in opposite directions.

Leaders sorted by market_cap. That is null for 92% of the universe - it
reaches the price table only for the companies Yahoo happened to return, and
the largest of those is a 979 million rupee micro-cap - so every sort key
collapsed to 0, the sort did nothing, and the page showed the first eight
companies alphabetically under the heading "largest constituents first".

Laggards filtered on the stored percentile, written by the formula engine's
valuation stage. That stage runs on import and never after a sweep, so the
field was null everywhere and the list was empty in every sector.
"""

from __future__ import annotations

from market_intelligence_engine.service import _rank_within_sector

LENS = {"primary_metric": "pe", "primary_metric_label": "P/E"}


def _m(symbol, pe=None, **extra):
    return {"symbol": symbol, "pe": pe, "sector": "Test", **extra}


def test_it_ranks_by_the_metric_not_the_alphabet():
    members = [_m("ZZZ", 10.0), _m("AAA", 40.0), _m("MMM", 25.0)]
    ranked, _ = _rank_within_sector(members, LENS)

    assert [r["symbol"] for r in ranked] == ["AAA", "MMM", "ZZZ"]
    assert [r["sector_rank"] for r in ranked] == [1, 2, 3]


def test_laggards_are_no_longer_always_empty():
    """The whole list was empty in every sector because percentile was null."""
    members = [_m("AAA", 40.0), _m("BBB", 10.0), _m("CCC", 25.0)]
    ranked, _ = _rank_within_sector(members, LENS)
    laggards = [r for r in reversed(ranked) if r.get("sector_rank") is not None][:8]

    assert [r["symbol"] for r in laggards] == ["BBB", "CCC", "AAA"]


def test_a_negative_multiple_is_not_the_cheapest_company():
    """A loss-making company must not surface as the sector's best value."""
    members = [_m("LOSS", -12.0), _m("CHEAP", 8.0), _m("RICH", 40.0)]
    ranked, basis = _rank_within_sector(members, LENS)
    laggards = [r for r in reversed(ranked) if r.get("sector_rank") is not None][:8]

    assert laggards[0]["symbol"] == "CHEAP"
    assert ranked[-1]["symbol"] == "LOSS"
    assert ranked[-1]["sector_rank"] is None
    assert basis["unranked"] == 1


def test_a_company_without_the_metric_is_kept_and_marked():
    """Dropping it would shrink the sector; ranking it zero would rank it last
    as though that were a measurement."""
    members = [_m("AAA", 20.0), _m("NODATA")]
    ranked, basis = _rank_within_sector(members, LENS)

    assert {r["symbol"] for r in ranked} == {"AAA", "NODATA"}
    nodata = next(r for r in ranked if r["symbol"] == "NODATA")
    assert nodata["sector_rank"] is None and nodata["sector_percentile"] is None
    assert basis["ranked"] == 1 and basis["unranked"] == 1


def test_the_percentile_runs_the_way_the_label_says():
    members = [_m(s, pe) for s, pe in (("A", 10.0), ("B", 20.0), ("C", 30.0), ("D", 40.0))]
    ranked, _ = _rank_within_sector(members, LENS)

    assert ranked[0]["sector_percentile"] == 100.0     # most expensive
    assert ranked[-1]["sector_percentile"] == 25.0     # cheapest


def test_the_basis_is_reported_so_the_page_can_say_what_it_shows():
    """The old heading claimed "largest constituents", which was never true."""
    _, basis = _rank_within_sector([_m("AAA", 20.0)], LENS)

    assert basis["metric"] == "pe"
    assert basis["metric_label"] == "P/E"
    assert "market cap" in basis["note"].lower() or "capitalisation" in basis["note"].lower()


def test_the_sector_view_no_longer_sorts_by_market_cap():
    import inspect

    from market_intelligence_engine import service

    src = inspect.getsource(service)
    assert 'key=lambda r: -(r.get("market_cap") or 0)' not in src


def test_an_empty_sector_does_not_explode():
    ranked, basis = _rank_within_sector([], LENS)
    assert ranked == [] and basis["ranked"] == 0


def test_the_service_excludes_unranked_names_from_laggards():
    """Guards the fix: reversing the full list put an unranked company first."""
    import inspect

    from market_intelligence_engine import service

    src = inspect.getsource(service)
    assert 'if r.get("sector_rank") is not None' in src
