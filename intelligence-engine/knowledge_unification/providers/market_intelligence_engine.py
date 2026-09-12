"""KUL provider — Market & Sector Intelligence Engine."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_MARKERS = (
    "market",
    "breadth",
    "sector rotation",
    "rotation",
    "institutional flows",
    "fii",
    "dii",
    "today's",
    "indian market",
    "nifty",
    "sensex",
    "heatmap",
    "which sectors",
    "rate cut",
    "rate hike",
    "macro",
    "screen",
    "compounder",
    "universe",
)


class MarketIntelligenceEngineProvider:
    spec = ProviderSpec(
        id="market_intelligence_engine",
        label="Market & Sector Intelligence",
        coverage=(
            "Market breadth, sector rotation, institutional flows and valuation overview "
            "from the warehouse-backed Market Intelligence Engine"
        ),
        priority=5,
        supported_question_types=(
            "market", "macro", "screen", "investment", "valuation", "company",
        ),
        typical_latency_ms=350,
        confidence_ceiling=0.85,
    )

    def health_check(self) -> str:
        try:
            from market_intelligence_engine.service import dashboard  # noqa: F401

            return "ok"
        except Exception:
            return "degraded"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        qlow = (plan.question or "").lower()
        if not any(m in qlow for m in _MARKERS):
            return empty_result(self.spec.id, t0, "not_a_market_question")
        try:
            from market_intelligence_engine.service import dashboard

            pack = dashboard(universe_limit=5000)
        except Exception as exc:
            return empty_result(self.spec.id, t0, str(exc)[:160])
        if not pack.get("ok"):
            # Still return an institutional market frame — never silent on breadth/flows.
            breadth_note = "Market breadth unavailable — insufficient warehouse price history."
            flow_note = "Institutional flows (FII/DII) unavailable — warehouse flow table empty."
            rotate_note = "Sector rotation unavailable — no valuation universe to rank leaders/laggards."
            try:
                from market_intelligence_engine import breadth as breadth_mod
                from market_intelligence_engine import flows as flows_mod

                b = breadth_mod.market_breadth() or {}
                f = flows_mod.institutional_flows() or {}
                if b.get("ok") and b.get("advance_decline_ratio") is not None:
                    breadth_note = (
                        f"Market breadth — advance/decline={b.get('advance_decline_ratio')}, "
                        f"stance={b.get('stance') or b.get('sentiment') or 'n/a'}."
                    )
                if f.get("available"):
                    flow_note = (
                        f"Institutional flows — latest net={f.get('net_institutional_flow')}, "
                        f"as of {f.get('latest_date')}."
                    )
                elif f.get("note"):
                    flow_note = str(f.get("note"))
            except Exception:
                pass
            summary = (
                "Indian market intelligence — warehouse coverage is currently thin, so AGIB "
                "reports the research frame rather than fabricating breadth or flow prints. "
                f"{breadth_note} {flow_note} {rotate_note} "
                "Monitor: index breadth, FII/DII net, sector rotation vs valuation medians, "
                "and the macro liquidity/rates backdrop."
            )
            expl = {
                "observed": [f"dashboard_error={pack.get('error') or 'mi_empty'}"],
                "derived": [breadth_note, flow_note],
                "inferred": [
                    "Rotation and market-wide valuation stance require a populated warehouse universe."
                ],
            }
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.45,
                t0=t0,
                summary=summary[:1200],
                why=[breadth_note, flow_note, rotate_note, "Research priorities: breadth, flows, rotation, macro"],
                evidence=[{
                    "source": "market_intelligence_engine",
                    "title": "mi:coverage_gap",
                    "explainability": expl,
                }],
                facts=[
                    {"field": "coverage_gap", "value": pack.get("error") or "mi_empty", "source": "mi"},
                ],
                raw={"engine": "market_intelligence_engine", "coverage_gap": True, "error": pack.get("error")},
            )

        agi = pack.get("summary") or {}
        summary = (
            agi.get("headline")
            or agi.get("summary")
            or agi.get("text")
            or "Indian market intelligence pack from warehouse valuation + breadth + flows."
        )
        if isinstance(summary, dict):
            summary = summary.get("headline") or summary.get("text") or str(summary)
        why = []
        overview = pack.get("overview") or {}
        breadth = pack.get("breadth") or {}
        flows = pack.get("flows") or {}
        rotate = pack.get("rotation") or {}
        if overview.get("median_pe") is not None:
            why.append(f"Market median PE={overview.get('median_pe')}")
        if breadth.get("advance_decline_ratio") is not None:
            why.append(f"Advance/decline={breadth.get('advance_decline_ratio')}")
        if flows.get("latest_fii_net") is not None:
            why.append(f"Latest FII net={flows.get('latest_fii_net')}")
        if rotate.get("stance") or (rotate.get("leaders") or []):
            why.append(f"Rotation: {rotate.get('stance') or rotate.get('leaders')}")
        for item in (agi.get("watch") or agi.get("monitor") or [])[:3]:
            why.append(str(item))
        expl = pack.get("explainability") or agi.get("explainability") or {
            "observed": why[:3],
            "derived": [f"companies={(pack.get('coverage') or {}).get('companies')}"],
            "inferred": [],
        }
        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=0.72,
            t0=t0,
            summary=str(summary)[:1200],
            why=why[:8],
            evidence=[{
                "source": "market_intelligence_engine",
                "title": "mi:dashboard",
                "explainability": expl,
            }],
            facts=[
                {"field": "valuation_date", "value": (pack.get("coverage") or {}).get("valuation_date"), "source": "mi"},
                {"field": "companies", "value": (pack.get("coverage") or {}).get("companies"), "source": "mi"},
            ],
            raw={
                "engine": "market_intelligence_engine",
                "overview": overview,
                "breadth": {k: breadth.get(k) for k in ("advance_decline_ratio", "sample_size", "stance") if k in breadth},
                "flows": {
                    k: flows.get(k)
                    for k in ("latest_fii_net", "latest_dii_net", "as_of")
                    if flows.get(k) is not None
                },
            },
        )
