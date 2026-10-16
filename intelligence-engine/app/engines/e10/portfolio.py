"""Canonical E10Portfolio contract (P0 subset)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e10.mapping import (
    BOOK_ID,
    ENGINE_VERSION,
    MANDATE_ID,
    MODEL_VERSION,
    PORTFOLIO_TYPE,
    SOLVER_ID,
)


class E10Portfolio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E10"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    mandate_id: str = MANDATE_ID
    portfolio_type: str = PORTFOLIO_TYPE
    book_id: str = BOOK_ID
    weights: dict[str, float] = Field(default_factory=dict)
    cash_allocation: float
    target_positions: list[dict[str, Any]] = Field(default_factory=list)
    risk_budget: dict[str, Any] = Field(default_factory=dict)
    expected_volatility: float
    vol_target: float
    portfolio_confidence: float
    gross: float
    net: float
    sector_allocation: dict[str, float] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    binding_constraints: list[str] = Field(default_factory=list)
    solver: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    l4_refs: dict[str, str] = Field(default_factory=dict)
    e02_refs: dict[str, str] = Field(default_factory=dict)
    selected_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[dict[str, str]] = Field(default_factory=list)
    model_version: str = MODEL_VERSION
    research_only: bool = True
    execution: bool = False
    hash: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.solver:
            object.__setattr__(
                self,
                "solver",
                {"model_id": SOLVER_ID, "status": "feasible", "binding_constraints": list(self.binding_constraints)},
            )
