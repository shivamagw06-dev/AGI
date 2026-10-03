"""CON-001 / CON-002 — EngineState SSOT schema + fixture validation."""

from __future__ import annotations

import json

import pytest

from app.contracts.engine_state import (
    CANONICAL_PATH,
    SCHEMA_PATH,
    EngineState,
    iter_fixture_paths,
    load_engine_state_schema,
    validate_engine_state,
)


def test_canonical_pointer_exists():
    assert SCHEMA_PATH.is_file()
    assert CANONICAL_PATH.is_file()
    canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    assert canonical["canonical_schema_path"].endswith("engine_state.schema.json")
    assert canonical["method_version_confidence"] == "conf-1.0"


def test_schema_loads_as_draft2020():
    schema = load_engine_state_schema()
    assert schema["title"] == "AGI EngineState Envelope"
    assert "confidence" in schema["properties"]
    assert schema["properties"]["confidence"]["properties"]["method_version"]["const"] == "conf-1.0"


@pytest.mark.parametrize("path", iter_fixture_paths(), ids=lambda p: p.name)
def test_fixtures_validate_against_ssot(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_engine_state(payload)
    assert errors == [], f"{path.name} failed: {errors}"
    # Typed mirror must also accept
    EngineState.model_validate(payload)


def test_priority_fixtures_present():
    names = {path.name for path in iter_fixture_paths()}
    for required in (
        "e01_state_sample.json",
        "e03_alpha_sample.json",
        "e14_state_sample.json",
        "l4_opinion_sample.json",
        "e10_portfolio_sample.json",
    ):
        assert required in names


def test_rejects_scalar_confidence():
    payload = json.loads((SCHEMA_PATH.parent / "fixtures" / "e01_state_sample.json").read_text())
    payload["confidence"] = 0.71  # illegal under conf-1.0 object shape
    errors = validate_engine_state(payload)
    assert errors, "scalar confidence must fail SSOT validation"


def test_rejects_missing_evidence_keys():
    payload = json.loads((SCHEMA_PATH.parent / "fixtures" / "e03_alpha_sample.json").read_text())
    del payload["evidence"]["missing_data"]
    errors = validate_engine_state(payload)
    assert errors
