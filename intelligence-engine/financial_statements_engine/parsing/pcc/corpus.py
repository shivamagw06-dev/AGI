"""Load and inspect the Production Certification Corpus (read-only golden dataset)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from financial_statements_engine.parsing.pcc.schema import EXPECTED_FILES, SECTORS

CORPUS_ROOT = Path(__file__).resolve().parent / "corpus"


def corpus_root() -> Path:
    return CORPUS_ROOT


def document_hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data or b"").hexdigest()


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_sectors() -> list[str]:
    root = corpus_root()
    if not root.exists():
        return []
    found = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    # Prefer declared order, then extras
    ordered = [s for s in SECTORS if s in found]
    ordered.extend(s for s in found if s not in ordered)
    return ordered


def list_cases(*, sector: str | None = None) -> list[dict[str, Any]]:
    root = corpus_root()
    sectors = [sector] if sector else list_sectors()
    cases: list[dict[str, Any]] = []
    for sec in sectors:
        sec_dir = root / sec
        if not sec_dir.is_dir():
            continue
        for case_dir in sorted(p for p in sec_dir.iterdir() if p.is_dir()):
            meta_path = case_dir / "metadata.json"
            if not meta_path.exists():
                # allow metadata/ nested
                alt = case_dir / "metadata" / "metadata.json"
                meta_path = alt if alt.exists() else meta_path
            meta = _read_json(meta_path) or {}
            if not isinstance(meta, dict):
                meta = {}
            cases.append(
                {
                    "sector": sec,
                    "case_id": case_dir.name,
                    "path": str(case_dir),
                    "ticker": meta.get("ticker") or case_dir.name.split("_")[0].upper(),
                    "company_name": meta.get("company_name"),
                    "verified": bool(meta.get("verified_at") or meta.get("verified_by")),
                    "immutable": bool(meta.get("immutable", True)),
                    "metadata": meta,
                }
            )
    return cases


def load_case(sector: str, case_id: str) -> dict[str, Any]:
    case_dir = corpus_root() / sector / case_id
    if not case_dir.is_dir():
        raise FileNotFoundError(f"pcc_case_not_found: {sector}/{case_id}")

    meta_path = case_dir / "metadata.json"
    if not meta_path.exists():
        meta_path = case_dir / "metadata" / "metadata.json"
    metadata = _read_json(meta_path) or {}
    if not isinstance(metadata, dict):
        metadata = {}

    raw_dir = case_dir / "raw"
    filing_path = raw_dir / "filing.json"
    if not filing_path.exists():
        # tolerate nested document packs
        candidates = sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []
        if not candidates:
            raise FileNotFoundError(f"pcc_raw_missing: {sector}/{case_id}")
        filing_path = candidates[0]
    raw_obj = _read_json(filing_path)
    raw_bytes = filing_path.read_bytes()

    expected_dir = case_dir / "expected"
    expected: dict[str, Any] = {}
    for name in EXPECTED_FILES:
        key = name.replace(".json", "")
        expected[key] = _read_json(expected_dir / name)

    return {
        "sector": sector,
        "case_id": case_id,
        "path": str(case_dir),
        "metadata": metadata,
        "raw_path": str(filing_path),
        "raw": raw_obj,
        "raw_bytes": raw_bytes,
        "document_hash": document_hash_bytes(raw_bytes),
        "expected": expected,
        "immutable": bool(metadata.get("immutable", True)),
    }


def corpus_health() -> dict[str, Any]:
    cases = list_cases()
    by_sector: dict[str, int] = {}
    verified_n = 0
    for c in cases:
        by_sector[c["sector"]] = by_sector.get(c["sector"], 0) + 1
        if c["verified"]:
            verified_n += 1
    return {
        "corpus_root": str(corpus_root()),
        "sectors_present": list_sectors(),
        "sectors_declared": list(SECTORS),
        "case_count": len(cases),
        "verified_case_count": verified_n,
        "cases_by_sector": by_sector,
        "golden_dataset_immutable": True,
        "auto_promote_forbidden": True,
    }
