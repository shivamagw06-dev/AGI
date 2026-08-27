"""Propagation through the causal graph, and what it refuses to do."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from situational_awareness import graph as g


def edge(a, b, el, conf=0.9, lo=0, hi=0, as_of="2026-08-28"):
    return {"from_node": a, "to_node": b, "as_of": as_of, "elasticity": el,
            "confidence": conf, "lag_months_min": lo, "lag_months_max": hi,
            "basis": "test"}


def exp(sym, node, e, conf=0.9, as_of="2026-08-28"):
    return {"symbol": sym, "node_id": node, "as_of": as_of,
            "exposure": e, "confidence": conf, "basis": "test"}


CHAIN = [
    edge("ai_compute_demand", "dc_buildout", 0.80, 0.90, 0, 6),
    edge("dc_buildout", "dc_power_demand", 0.90, 0.85, 6, 18),
    edge("dc_power_demand", "transformer_demand", 0.55, 0.78, 12, 36),
    edge("dc_buildout", "cooling_demand", 0.70, 0.82, 3, 12),
]


class Propagation(unittest.TestCase):
    def test_a_shock_reaches_the_far_end_of_the_chain(self):
        out = g.propagate("ai_compute_demand", 20.0, CHAIN)
        self.assertIn("transformer_demand", out)
        self.assertEqual(out["transformer_demand"]["hops"], 3)

    def test_the_effect_decays_with_distance(self):
        out = g.propagate("ai_compute_demand", 20.0, CHAIN)
        chain = ["ai_compute_demand", "dc_buildout", "dc_power_demand", "transformer_demand"]
        sizes = [abs(out[n]["effect_pct"]) for n in chain]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_confidence_decays_too(self):
        # Four hops of estimated elasticities is not knowledge.
        out = g.propagate("ai_compute_demand", 20.0, CHAIN)
        self.assertLess(out["transformer_demand"]["confidence"],
                        out["dc_buildout"]["confidence"])

    def test_lag_accumulates_rather_than_averaging(self):
        # "Somewhere between eighteen months and five years" is the honest
        # answer; a single number would not be.
        out = g.propagate("ai_compute_demand", 20.0, CHAIN)
        t = out["transformer_demand"]
        self.assertEqual((t["lag_min"], t["lag_max"]), (18, 60))

    def test_a_negative_edge_carries_its_sign(self):
        neg = [edge("agent_capability", "it_services_demand", -0.30, 0.55, 24, 60)]
        out = g.propagate("agent_capability", 30.0, neg)
        self.assertLess(out["it_services_demand"]["effect_pct"], 0)

    def test_a_cycle_terminates(self):
        # Power scarcity raises prices, which slows buildout, which reduces
        # power demand. Real feedback; a naive walk never returns.
        loop = CHAIN + [edge("dc_power_demand", "ai_compute_demand", -0.20, 0.6)]
        out = g.propagate("ai_compute_demand", 20.0, loop)
        self.assertLessEqual(max(v["hops"] for v in out.values()), g.MAX_HOPS)

    def test_a_negligible_effect_is_not_carried_further(self):
        faint = [edge("a", "b", 0.01, 0.9), edge("b", "c", 0.9, 0.9)]
        out = g.propagate("a", 10.0, faint)
        self.assertNotIn("c", out)

    def test_an_unknown_origin_is_refused(self):
        with self.assertRaises(g.GraphError):
            g.propagate("not_a_node", 10.0, CHAIN)

    def test_only_the_latest_vintage_of_an_edge_is_used(self):
        # The table is append-only so a pair carries several vintages. Older
        # rows exist to reconstruct a past belief, not to be propagated again.
        vintages = [edge("a", "b", 0.10, 0.9, as_of="2026-01-01"),
                    edge("a", "b", 0.90, 0.9, as_of="2026-08-01")]
        out = g.propagate("a", 10.0, vintages)
        self.assertAlmostEqual(out["b"]["effect_pct"], 9.0, places=3)

    def test_two_paths_to_one_node_do_not_add_up(self):
        # Both routes usually describe the same economics at different
        # granularity; summing reports twice the effect for drawing the graph
        # in more detail.
        two = [edge("a", "b", 0.5, 0.9), edge("a", "c", 0.5, 0.9),
               edge("b", "d", 0.5, 0.9), edge("c", "d", 0.5, 0.9)]
        out = g.propagate("a", 100.0, two)
        self.assertAlmostEqual(out["d"]["effect_pct"], 25.0, places=3)


class CompanyImpact(unittest.TestCase):
    def _reached(self):
        return g.propagate("ai_compute_demand", 20.0, CHAIN)

    def test_a_company_is_reached_through_its_exposure(self):
        out = g.company_impacts(self._reached(), [exp("POWERGRID", "dc_power_demand", 0.6)])
        self.assertEqual(out[0]["symbol"], "POWERGRID")
        self.assertGreater(out[0]["effect_pct"], 0)

    def test_exposure_to_several_nodes_adds_up(self):
        # Genuinely separate revenue lines, unlike two paths to one node.
        out = g.company_impacts(self._reached(), [
            exp("SIEMENS", "transformer_demand", 0.5),
            exp("SIEMENS", "cooling_demand", 0.3)])
        via = out[0]["via"]
        self.assertEqual(len(via), 2)
        self.assertAlmostEqual(out[0]["effect_pct"],
                               sum(v["contribution_pct"] for v in via), places=3)

    def test_a_negative_exposure_produces_a_negative_impact(self):
        out = g.company_impacts(self._reached(),
                                [exp("TCS", "dc_power_demand", -0.4)])
        self.assertLess(out[0]["effect_pct"], 0)

    def test_confidence_is_dragged_down_by_the_weakest_leg(self):
        # A thesis is only as good as its weakest necessary link. An
        # arithmetic mean would let three confident legs bury one shaky one.
        strong = g.company_impacts(self._reached(),
                                   [exp("A", "dc_buildout", 0.5, conf=0.9)])
        mixed = g.company_impacts(self._reached(), [
            exp("B", "dc_buildout", 0.5, conf=0.9),
            exp("B", "cooling_demand", 0.5, conf=0.35)])
        self.assertEqual(len(mixed[0]["via"]), 2, "both legs must survive the floor")
        self.assertLess(mixed[0]["confidence"], strong[0]["confidence"])

    def test_a_leg_below_the_confidence_floor_is_dropped_with_its_effect(self):
        # Dropping it does not flatter the thesis: the contribution goes too,
        # so the result is narrower rather than more confident than it earned.
        out = g.company_impacts(self._reached(), [
            exp("C", "dc_buildout", 0.5, conf=0.9),
            exp("C", "cooling_demand", 0.5, conf=0.05)])
        self.assertEqual(len(out[0]["via"]), 1)
        self.assertEqual(out[0]["via"][0]["node"], "dc_buildout")

    def test_the_path_is_reported_so_the_arithmetic_can_be_checked(self):
        out = g.company_impacts(self._reached(),
                                [exp("VOLTAMP", "transformer_demand", 0.7)])
        via = out[0]["via"][0]
        self.assertEqual(via["path"][0], "ai_compute_demand")
        self.assertEqual(via["path"][-1], "transformer_demand")

    def test_a_company_on_an_unaffected_node_is_absent(self):
        out = g.company_impacts(self._reached(), [exp("NOBODY", "unrelated_node", 0.9)])
        self.assertEqual(out, [])

    def test_results_rank_by_effect_weighted_by_confidence(self):
        out = g.company_impacts(self._reached(), [
            exp("SURE", "dc_buildout", 0.5, conf=0.95),
            exp("SHAKY", "dc_buildout", 0.55, conf=0.2)])
        self.assertEqual(out[0]["symbol"], "SURE")


if __name__ == "__main__":
    unittest.main()
