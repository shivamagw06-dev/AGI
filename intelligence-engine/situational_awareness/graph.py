"""Propagating a change through a causal graph to the companies it reaches.

The graph holds economic quantities, not companies. "Data-centre power demand"
is a node; NTPC is not. Companies hang off nodes through exposures, so a
company can never sit in the middle of a chain and pass an effect along to
another company -- which is how a dependency graph quietly becomes a
correlation graph.

Three properties the propagation has to have, and each costs something to get:

  A shock decays. Every hop multiplies by an elasticity below one and a
  confidence below one, so an effect four hops out arrives small and uncertain
  rather than arriving as though it were observed.

  Lag accumulates. An edge that takes 12-36 months does not deliver its effect
  next quarter, and a chain of such edges delivers later still. The window is
  carried, not averaged away, because "somewhere between one and five years"
  is the honest answer and a single number would not be.

  Cycles terminate. Real economies have feedback -- power scarcity raises
  prices, which slows datacentre construction, which reduces power demand --
  and a naive walk around that loop never returns.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Optional

PROPAGATION_VERSION = "sa-graph-1"

# Deliberately not called an effect on the share price. What propagates here is
# a change in the demand a company is exposed to, before any of the things that
# decide whether the company captures it -- capacity, backlog, pricing power,
# competition -- and long before it reaches revenue, margin or EPS. Naming it
# "effect_pct" invited a later reader, or another model, to treat a demand
# exposure as an expected return. It is neither a forecast nor a return.

# Below this an effect is not worth carrying further: a 0.5% move on a
# confidence of 0.3 is indistinguishable from the error in the elasticity that
# produced it.
MIN_EFFECT_PCT = 0.25
MIN_CONFIDENCE = 0.15
# A chain longer than this is not a thesis, it is a chain of guesses.
MAX_HOPS = 5


class GraphError(ValueError):
    pass


def build_index(edges: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Edges keyed by their origin, newest vintage only.

    The tables are append-only, so a node pair can carry several vintages. The
    latest is what the engine currently believes; the older rows exist so a
    past belief can be reconstructed, not so it can be propagated twice.
    """
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for e in edges:
        key = (str(e["from_node"]), str(e["to_node"]))
        prev = latest.get(key)
        if prev is None or str(e.get("as_of", "")) > str(prev.get("as_of", "")):
            latest[key] = e
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (frm, _), e in latest.items():
        out[frm].append(e)
    return dict(out)


def _elasticities(edge: dict[str, Any]) -> tuple[float, float, float]:
    """Low, base and high for one edge.

    An elasticity of 0.54 is not precise, and propagating it as a point produces
    a confident-looking single number four hops away. Where a range is supplied
    it is carried; where it is not, the base fills all three, so an edge that
    never stated a range does not silently widen the answer.
    """
    base = float(edge["elasticity"])
    lo, hi = edge.get("elasticity_low"), edge.get("elasticity_high")
    return (float(lo) if lo is not None else base, base,
            float(hi) if hi is not None else base)


def propagate(origin: str, shock_pct: float,
              edges: Iterable[dict[str, Any]], *,
              origin_confidence: float = 1.0,
              max_hops: int = MAX_HOPS) -> dict[str, dict[str, Any]]:
    """Where a percentage change at one node ends up, and how sure we are.

    Breadth-first, keeping the strongest path to each node rather than summing
    every path. Summing double-counts: two routes from compute demand to power
    are usually the same economics described at different granularity, and
    adding them would report twice the effect for having drawn the graph in
    more detail.
    """
    index = build_index(edges)
    if origin not in index and not any(
            str(e.get("to_node")) == origin for e in edges):
        raise GraphError(f"{origin!r} is not in the graph")

    reached: dict[str, dict[str, Any]] = {
        origin: {"exposure_effect_pct": float(shock_pct),
                 "exposure_effect_low": float(shock_pct),
                 "exposure_effect_high": float(shock_pct),
                 "confidence": float(origin_confidence),
                 "lag_min": 0, "lag_max": 0, "hops": 0, "path": [origin]},
    }
    frontier = [origin]

    for hop in range(1, max_hops + 1):
        nxt: list[str] = []
        for node in frontier:
            here = reached[node]
            for edge in index.get(node, []):
                to = str(edge["to_node"])
                lo_e, base_e, hi_e = _elasticities(edge)
                effect = here["exposure_effect_pct"] * base_e
                # The range compounds along the whole path: a bear case is the
                # low elasticity applied at every hop, not once at the last.
                ends = [here["exposure_effect_low"] * lo_e,
                        here["exposure_effect_low"] * hi_e,
                        here["exposure_effect_high"] * lo_e,
                        here["exposure_effect_high"] * hi_e]
                conf = here["confidence"] * float(edge["confidence"])
                if abs(effect) < MIN_EFFECT_PCT or conf < MIN_CONFIDENCE:
                    continue
                cand = {
                    "exposure_effect_pct": round(effect, 4),
                    "exposure_effect_low": round(min(ends), 4),
                    "exposure_effect_high": round(max(ends), 4),
                    "confidence": round(conf, 4),
                    "lag_min": here["lag_min"] + int(edge.get("lag_months_min") or 0),
                    "lag_max": here["lag_max"] + int(edge.get("lag_months_max") or 0),
                    "hops": hop,
                    "path": here["path"] + [to],
                }
                prev = reached.get(to)
                # Strongest path wins, measured on the effect actually carried
                # rather than on raw size: a large effect at low confidence is
                # a worse account of what happens than a smaller certain one.
                if prev is None or abs(cand["exposure_effect_pct"]) * cand["confidence"] > \
                                   abs(prev["exposure_effect_pct"]) * prev["confidence"]:
                    reached[to] = cand
                    nxt.append(to)
        if not nxt:
            break
        frontier = nxt
    return reached


def company_impacts(reached: dict[str, dict[str, Any]],
                    exposures: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Which companies the propagation touches, and through what.

    A company exposed to several affected nodes gets the sum, because those are
    genuinely separate revenue lines -- unlike two paths to the same node,
    which are one economic effect described twice. The contributing nodes are
    listed so the arithmetic can be checked rather than trusted.
    """
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for x in exposures:
        key = (str(x["symbol"]), str(x["node_id"]))
        prev = latest.get(key)
        if prev is None or str(x.get("as_of", "")) > str(prev.get("as_of", "")):
            latest[key] = x

    per: dict[str, dict[str, Any]] = {}
    for (symbol, node), x in latest.items():
        hit = reached.get(node)
        if not hit:
            continue
        exposure = float(x["exposure"])
        contribution = hit["exposure_effect_pct"] * exposure
        conf = hit["confidence"] * float(x["confidence"])
        if abs(contribution) < MIN_EFFECT_PCT or conf < MIN_CONFIDENCE:
            continue
        row = per.setdefault(symbol, {
            "symbol": symbol, "exposure_effect_pct": 0.0, "via": [],
            "lag_min": hit["lag_min"], "lag_max": hit["lag_max"],
        })
        row["exposure_effect_pct"] += contribution
        row["via"].append({
            "node": node, "exposure": exposure,
            "node_exposure_effect_pct": hit["exposure_effect_pct"],
            "contribution_pct": round(contribution, 4),
            "confidence": round(conf, 4),
            "hops": hit["hops"], "path": hit["path"],
        })
        row["lag_min"] = min(row["lag_min"], hit["lag_min"])
        row["lag_max"] = max(row["lag_max"], hit["lag_max"])

    out = []
    for row in per.values():
        # A thesis is only as good as its weakest necessary link, so confidence
        # is the geometric mean of the contributing paths rather than the
        # arithmetic one -- one shaky leg should drag the whole thesis down,
        # not be averaged away by three confident ones.
        confs = [v["confidence"] for v in row["via"]]
        row["confidence"] = round(math.exp(sum(math.log(c) for c in confs) / len(confs)), 4)
        row["exposure_effect_pct"] = round(row["exposure_effect_pct"], 4)
        row["via"].sort(key=lambda v: -abs(v["contribution_pct"]))
        row["version"] = PROPAGATION_VERSION
        out.append(row)
    out.sort(key=lambda r: -abs(r["exposure_effect_pct"]) * r["confidence"])
    return out
