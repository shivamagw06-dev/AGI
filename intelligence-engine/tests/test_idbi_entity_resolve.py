"""IDBI Bank must resolve to IDBI — never fall through to HDFCBANK / bare BANK."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_irl_detects_idbi_bank():
    from ask_pipeline.intent_resolution.entities import detect_entities

    pack = detect_entities("idbi bank")
    assert pack.get("concept_mode") is False
    assert (pack.get("primary") or {}).get("entity_id") == "IDBI"
    ids = {e.get("id") for e in (pack.get("entities") or [])}
    assert "IDBI" in ids
    assert "HDFCBANK" not in ids


def test_evidence_contracts_resolve_idbi():
    from institutional_reasoning.evidence_contracts import resolve_entities

    resolved = resolve_entities("What is your view on IDBI Bank?")
    assert resolved.get("resolved") is True
    assert (resolved.get("primary") or {}).get("entity_id") == "IDBI"


def test_sif_alias_idbi():
    from sif.detection import COMPANY_ALIASES, COMPANY_SECTOR, resolve_ticker

    assert COMPANY_ALIASES.get("idbi bank") == "IDBI"
    assert COMPANY_SECTOR.get("IDBI") == "banks"
    assert resolve_ticker("idbi bank") == "IDBI"


def test_irp_does_not_emit_bare_bank_ticker():
    from app.irp.entities import resolve_entities

    pack = resolve_entities("idbi bank")
    assert pack.primary_ticker == "IDBI"
    assert "BANK" not in (pack.tickers or [])
    assert pack.primary_ticker != "HDFCBANK"


def test_ere_seed_resolves_idbi():
    from entity_resolution.production import soft_slice_for_ask_agi

    pack = soft_slice_for_ask_agi("idbi bank") or {}
    body = pack.get("entity_resolution") or {}
    assert body.get("ticker") == "IDBI", pack
    assert body.get("needs_clarification") is not True


def test_looks_like_equity_ticker_rejects_bank_word():
    from app.kip.extractors import looks_like_equity_ticker

    assert looks_like_equity_ticker("IDBI") is True
    assert looks_like_equity_ticker("HDFCBANK") is True
    assert looks_like_equity_ticker("BANK") is False
    assert looks_like_equity_ticker("BANKS") is False
