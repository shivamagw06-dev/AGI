"""EngineState envelope — Architecture v1.0.1 SSOT (E00 §5, WBS CON-001).

This module does not replace legacy research-desk models in app.schemas.models.
Those remain for L6 agent runs. Engine research outputs must validate here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACTS_V1 = Path(__file__).resolve().parents[2] / "contracts" / "v1"
SCHEMA_PATH = CONTRACTS_V1 / "engine_state.schema.json"
FIXTURES_DIR = CONTRACTS_V1 / "fixtures"
CANONICAL_PATH = CONTRACTS_V1 / "CANONICAL.json"


def empty_evidence_pack() -> dict[str, list[Any]]:
    return {
        "positive": [],
        "negative": [],
        "contradictions": [],
        "unknowns": [],
        "risks": [],
        "missing_data": [],
    }


class ScoreBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    raw: float | None = None
    normalized_0_100: float | None = Field(default=None, ge=0, le=100)
    normalized_signed: float | None = Field(default=None, ge=-1, le=1)
    unit: str


class ConfidenceBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: float = Field(ge=0, le=1)
    components: dict[str, Any] = Field(default_factory=dict)
    method_version: str = "conf-1.0"

    @field_validator("method_version")
    @classmethod
    def must_be_conf_1_0(cls, value: str) -> str:
        if value != "conf-1.0":
            raise ValueError("confidence.method_version must be conf-1.0")
        return value


class ReliabilityBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    sample_size: float | None = None
    historical_accuracy: float | None = None
    stability: float | None = None


class ExplanationBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    summary: str
    top_drivers: list[str] = Field(default_factory=list)
    falsifiers: list[str] = Field(default_factory=list)


class EngineState(BaseModel):
    """Typed mirror of contracts/v1/engine_state.schema.json."""

    model_config = ConfigDict(extra="allow")

    engine: str
    version: str
    model_version: str
    as_of: str
    universe_id: str | None = None
    symbol: str | None = None
    score: ScoreBlock
    confidence: ConfidenceBlock
    reliability: ReliabilityBlock | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any]
    explanation: ExplanationBlock
    warnings: list[str] = Field(default_factory=list)
    stale_inputs: list[str] = Field(default_factory=list)
    input_hash: str
    hash: str
    timestamp_generated: str

    @field_validator("evidence")
    @classmethod
    def evidence_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        required = (
            "positive",
            "negative",
            "contradictions",
            "unknowns",
            "risks",
            "missing_data",
        )
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"evidence missing keys: {missing}")
        for key in required:
            if not isinstance(value[key], list):
                raise ValueError(f"evidence.{key} must be a list")
        return value

    @field_validator("input_hash", "hash")
    @classmethod
    def sha256_prefix(cls, value: str) -> str:
        if not value.startswith("sha256:") or len(value) != len("sha256:") + 64:
            raise ValueError("hash fields must match sha256:<64 hex>")
        suffix = value.split(":", 1)[1]
        if any(ch not in "0123456789abcdef" for ch in suffix):
            raise ValueError("hash digest must be lowercase hex")
        return value


@lru_cache(maxsize=1)
def load_engine_state_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_engine_state(payload: dict[str, Any]) -> list[str]:
    """Validate against JSON Schema SSOT. Returns a list of error strings (empty = ok)."""
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("jsonschema is required for EngineState validation") from exc

    validator = jsonschema.Draft202012Validator(load_engine_state_schema())
    return sorted(
        f"{'.'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
        for err in validator.iter_errors(payload)
    )


def iter_fixture_paths() -> list[Path]:
    if not FIXTURES_DIR.exists():
        return []
    return sorted(FIXTURES_DIR.glob("*.json"))
