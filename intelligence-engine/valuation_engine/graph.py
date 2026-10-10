"""Valuation dependency graph.

Every valuation figure is derived from other figures. Market capitalisation
needs a price and a share count; enterprise value needs market capitalisation,
debt and cash; EV/EBITDA needs enterprise value and EBITDA; the sector
percentile needs every peer's multiple.

Holding that as an explicit graph rather than as call order buys three things:

* when a price ticks, only the nodes downstream of ``cmp`` recompute, so a
  quote refresh does not rebuild the market
* a null is explainable — a missing node names the input it lacked, rather
  than rendering as a blank cell
* the order of computation is derived, so adding a metric cannot silently
  depend on something computed after it
"""

from __future__ import annotations

from typing import Iterable

#: node -> the nodes it reads. Inputs (leaves) have no dependencies.
DEPENDENCIES: dict[str, tuple[str, ...]] = {
    # Inputs, straight from the warehouse.
    "cmp": (),
    "shares_outstanding": (),
    "eps": (),
    "book_value_per_share": (),
    "revenue": (),
    "ebitda": (),
    "debt": (),
    "cash": (),
    "dividend_per_share": (),
    "equity": (),
    "pat": (),
    "target_price": (),
    "forward_eps": (),
    # Provider-owned profitability ratios (Upstox key-ratios). Not derived here.
    "roa": (),
    "roce": (),
    # Derived (skipped when Upstox already supplies the multiple).
    "market_cap": ("cmp", "shares_outstanding"),
    "enterprise_value": ("market_cap", "debt", "cash"),
    "pe": ("cmp", "eps"),
    "forward_pe": ("cmp", "forward_eps"),
    "pb": ("cmp", "book_value_per_share"),
    "ev_ebitda": ("enterprise_value", "ebitda"),
    "ev_sales": ("enterprise_value", "revenue"),
    "ps": ("market_cap", "revenue"),
    "dividend_yield": ("dividend_per_share", "cmp"),
    "roe": ("pat", "equity"),
    "upside": ("target_price", "cmp"),
    # Context, computed once the company's own multiples exist.
    "sector_premium": ("pe", "pb", "ev_ebitda"),
    "historical_percentile": ("pe", "pb", "ev_ebitda"),
    "relative_score": ("sector_premium", "historical_percentile", "roe"),
}

#: Multiples/ratios Upstox reports — never recompute when provider value exists.
PROVIDER_OWNED_RATIOS: frozenset[str] = frozenset({
    "pe", "pb", "roa", "roe", "roce", "ev_ebitda",
})

#: Nodes a consumer may ask for. Inputs are reachable too, deliberately: a desk
#: that wants the share count should not have to read the warehouse itself.
METRICS: tuple[str, ...] = tuple(DEPENDENCIES)


def dependents_of(node: str) -> list[str]:
    """Every node that must recompute when ``node`` changes, transitively."""
    dirty: set[str] = set()
    frontier = [node]
    while frontier:
        current = frontier.pop()
        for candidate, inputs in DEPENDENCIES.items():
            if current in inputs and candidate not in dirty:
                dirty.add(candidate)
                frontier.append(candidate)
    return topological(dirty)


def topological(nodes: Iterable[str] | None = None) -> list[str]:
    """Computation order: a node never appears before something it reads."""
    wanted = set(nodes) if nodes is not None else set(DEPENDENCIES)
    ordered: list[str] = []
    placed: set[str] = set()

    def visit(node: str, seen: frozenset[str]) -> None:
        if node in placed or node in seen:
            return
        for dependency in DEPENDENCIES.get(node, ()):
            visit(dependency, seen | {node})
        placed.add(node)
        if node in wanted:
            ordered.append(node)

    for node in DEPENDENCIES:
        visit(node, frozenset())
    return ordered


def inputs_of(node: str) -> tuple[str, ...]:
    return DEPENDENCIES.get(node, ())
