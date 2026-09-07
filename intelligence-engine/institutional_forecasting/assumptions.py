"""ScenarioAssumption — every scenario is built from explicit assumptions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ScenarioAssumption:
    """One explicit, auditable assumption driving a forecast scenario."""

    assumption_id: str
    variable: str  # e.g. RBI Repo Rate, NIM, Credit Cost
    node_key: str  # graph metric key or node type key (rbi_rate, nim, credit_cost, ...)
    current_value: str
    scenario_value: str
    direction: str  # positive | negative | neutral
    magnitude: float  # signed shock in [-1, 1]
    confidence: float  # 0–1
    unit: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ScenarioAssumption":
        body = dict(payload or {})
        try:
            mag = float(body.get("magnitude") if body.get("magnitude") is not None else 0.0)
        except (TypeError, ValueError):
            mag = 0.0
        try:
            conf = float(body.get("confidence") if body.get("confidence") is not None else 0.7)
        except (TypeError, ValueError):
            conf = 0.7
        if conf > 1.0:
            conf = conf / 100.0
        direction = str(body.get("direction") or "neutral").strip().lower()
        if direction not in {"positive", "negative", "neutral"}:
            direction = "positive" if mag > 0 else ("negative" if mag < 0 else "neutral")
        return cls(
            assumption_id=str(body.get("assumption_id") or body.get("id") or "").strip(),
            variable=str(body.get("variable") or body.get("name") or "").strip(),
            node_key=str(body.get("node_key") or body.get("key") or "").strip(),
            current_value=str(body.get("current_value") or body.get("current") or "").strip(),
            scenario_value=str(body.get("scenario_value") or body.get("scenario") or "").strip(),
            direction=direction,
            magnitude=max(-1.0, min(1.0, mag)),
            confidence=max(0.0, min(1.0, conf)),
            unit=str(body.get("unit") or "").strip(),
            notes=str(body.get("notes") or "").strip(),
        )


def banking_preset_assumptions(scenario_name: str) -> tuple[ScenarioAssumption, ...]:
    """Deterministic banking assumption packs for standard scenarios."""
    name = str(scenario_name or "base").strip().lower()
    if name == "base":
        return (
            ScenarioAssumption(
                assumption_id="base-rbi",
                variable="RBI Repo Rate",
                node_key="rbi_rate",
                current_value="5.75%",
                scenario_value="5.75%",
                direction="neutral",
                magnitude=0.0,
                confidence=0.9,
                unit="%",
                notes="Policy rate unchanged",
            ),
            ScenarioAssumption(
                assumption_id="base-credit",
                variable="Credit Cost",
                node_key="credit_cost",
                current_value="stable",
                scenario_value="stable",
                direction="neutral",
                magnitude=0.0,
                confidence=0.85,
                notes="Credit costs track recent trend",
            ),
        )
    if name in {"bull", "optimistic"}:
        scale = 1.0 if name == "bull" else 1.25
        return (
            ScenarioAssumption(
                assumption_id=f"{name}-rbi",
                variable="RBI Repo Rate",
                node_key="rbi_rate",
                current_value="5.75%",
                scenario_value="5.25%" if name == "bull" else "5.00%",
                direction="negative",  # rate down is negative on the rate node
                magnitude=-0.35 * scale,
                confidence=0.82,
                unit="%",
                notes="Policy easing supports funding costs",
            ),
            ScenarioAssumption(
                assumption_id=f"{name}-nim",
                variable="Net Interest Margin",
                node_key="nim",
                current_value="stable",
                scenario_value="expanding",
                direction="positive",
                magnitude=0.40 * min(scale, 1.0),
                confidence=0.78,
                notes="NIM expands as funding cost falls",
            ),
            ScenarioAssumption(
                assumption_id=f"{name}-credit",
                variable="Credit Cost",
                node_key="credit_cost",
                current_value="stable",
                scenario_value="falling",
                direction="negative",  # credit cost falling
                magnitude=-0.45 * min(scale, 1.0),
                confidence=0.8,
                notes="Credit costs moderate",
            ),
            ScenarioAssumption(
                assumption_id=f"{name}-roe",
                variable="Return on Equity",
                node_key="roe",
                current_value="stable",
                scenario_value="improving",
                direction="positive",
                magnitude=0.35 * min(scale, 1.0),
                confidence=0.75,
            ),
        )
    if name == "bear":
        return (
            ScenarioAssumption(
                assumption_id="bear-rbi",
                variable="RBI Repo Rate",
                node_key="rbi_rate",
                current_value="5.75%",
                scenario_value="6.25%",
                direction="positive",
                magnitude=0.35,
                confidence=0.8,
                unit="%",
                notes="Tightening pressures funding costs",
            ),
            ScenarioAssumption(
                assumption_id="bear-nim",
                variable="Net Interest Margin",
                node_key="nim",
                current_value="stable",
                scenario_value="compressing",
                direction="negative",
                magnitude=-0.40,
                confidence=0.78,
            ),
            ScenarioAssumption(
                assumption_id="bear-credit",
                variable="Credit Cost",
                node_key="credit_cost",
                current_value="stable",
                scenario_value="rising",
                direction="positive",
                magnitude=0.45,
                confidence=0.82,
            ),
            ScenarioAssumption(
                assumption_id="bear-valuation",
                variable="Valuation",
                node_key="valuation",
                current_value="Fair",
                scenario_value="Expensive",
                direction="negative",
                magnitude=-0.30,
                confidence=0.7,
            ),
        )
    if name == "stress":
        return (
            ScenarioAssumption(
                assumption_id="stress-credit",
                variable="Credit Cost",
                node_key="credit_cost",
                current_value="stable",
                scenario_value="spike",
                direction="positive",
                magnitude=0.85,
                confidence=0.75,
                notes="Severe asset-quality stress",
            ),
            ScenarioAssumption(
                assumption_id="stress-nim",
                variable="Net Interest Margin",
                node_key="nim",
                current_value="stable",
                scenario_value="sharp compression",
                direction="negative",
                magnitude=-0.70,
                confidence=0.72,
            ),
            ScenarioAssumption(
                assumption_id="stress-risk",
                variable="Overall Risk",
                node_key="risk",
                current_value="Moderate",
                scenario_value="Severe",
                direction="positive",
                magnitude=0.90,
                confidence=0.8,
            ),
            ScenarioAssumption(
                assumption_id="stress-valuation",
                variable="Valuation",
                node_key="valuation",
                current_value="Fair",
                scenario_value="Expensive",
                direction="negative",
                magnitude=-0.50,
                confidence=0.7,
            ),
        )
    # custom empty — caller supplies assumptions
    return ()
