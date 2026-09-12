"""Acceptance dataset paths, health checks, and bootstrap for CI/local parity."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Golden regression corpus — always version-controlled
GOLDEN_TICKERS: tuple[str, ...] = (
    "TCS",
    "INFY",
    "HDFCBANK",
    "RELIANCE",
    "ICICIBANK",
    "ASIANPAINT",
    "TITAN",
    "LT",
    "MARUTI",
    "BHARTIARTL",
)

MINIMUM_REQUIRED = {
    "valuation_consensus_rows": 10,
    "ikt_companies": 10,
    "kf_objects": 1,
    "evidence_packs": 1,
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def intelligence_engine_root() -> Path:
    return Path(__file__).resolve().parents[1]


def fixtures_root() -> Path:
    override = (os.getenv("ACCEPTANCE_FIXTURES_ROOT") or "").strip()
    if override:
        return Path(override)
    return intelligence_engine_root() / "acceptance_fixtures"


def data_root() -> Path:
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    if kip:
        return Path(kip)
    return intelligence_engine_root() / "data"


def _vc_root() -> Path:
    raw = (os.getenv("VALUATION_CONSENSUS_ROOT") or "").strip()
    return Path(raw) if raw else data_root() / "valuation_consensus"


def _ikt_root() -> Path:
    raw = (os.getenv("IKT_STORE_ROOT") or "").strip()
    return Path(raw) if raw else data_root() / "institutional_knowledge_tables"


def _kf_root() -> Path:
    raw = (os.getenv("KF_STORE_ROOT") or "").strip()
    return Path(raw) if raw else data_root() / "knowledge_factory"


def _iere_root() -> Path:
    raw = (os.getenv("IERE_STORE_ROOT") or "").strip()
    return Path(raw) if raw else data_root() / "evidence_retrieval"


@dataclass
class DatasetCheck:
    name: str
    ok: bool
    count: int
    required: int
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "count": self.count,
            "required": self.required,
            "detail": self.detail,
        }


def _count_json_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.glob("*.json") if p.is_file())


def _load_vc_rows() -> dict[str, Any]:
    path = _vc_root() / "live.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    rows = payload.get("rows") if isinstance(payload, dict) else {}
    return rows if isinstance(rows, dict) else {}


def apply_env_defaults() -> None:
    """Point runtime stores at bootstrapped data directories."""
    root = data_root()
    os.environ.setdefault("KIP_DATA_DIR", str(root))
    os.environ.setdefault("VALUATION_CONSENSUS_ROOT", str(_vc_root()))
    os.environ.setdefault("IKT_STORE_ROOT", str(_ikt_root()))
    os.environ.setdefault("KF_STORE_ROOT", str(_kf_root()))
    os.environ.setdefault("IERE_STORE_ROOT", str(_iere_root()))


def check_acceptance_data(*, verbose: bool = True) -> dict[str, Any]:
    """Verify required acceptance datasets exist with minimum row counts."""
    apply_env_defaults()

    vc_rows = _load_vc_rows()
    ikt_count = _count_json_files(_ikt_root() / "facts")
    kf_objects = _count_json_files(_kf_root() / "objects" / "company")
    kf_packs = _count_json_files(_kf_root() / "packs")
    evidence_packs = _count_json_files(_iere_root() / "packs")
    manifest_path = fixtures_root() / "manifest.json"
    manifest_ok = manifest_path.exists()

    checks = [
        DatasetCheck(
            "Valuation Consensus",
            len(vc_rows) >= MINIMUM_REQUIRED["valuation_consensus_rows"],
            len(vc_rows),
            MINIMUM_REQUIRED["valuation_consensus_rows"],
            f"{len(vc_rows)} rows in {_vc_root() / 'live.json'}",
        ),
        DatasetCheck(
            "IKT",
            ikt_count >= MINIMUM_REQUIRED["ikt_companies"],
            ikt_count,
            MINIMUM_REQUIRED["ikt_companies"],
            f"{ikt_count} companies in {_ikt_root() / 'facts'}",
        ),
        DatasetCheck(
            "Knowledge Factory Objects",
            kf_objects >= MINIMUM_REQUIRED["kf_objects"],
            kf_objects,
            MINIMUM_REQUIRED["kf_objects"],
            f"{kf_objects} objects in {_kf_root() / 'objects/company'}",
        ),
        DatasetCheck(
            "Knowledge Factory Packs",
            kf_packs >= 1,
            kf_packs,
            1,
            f"{kf_packs} packs in {_kf_root() / 'packs'}",
        ),
        DatasetCheck(
            "Evidence Packs",
            evidence_packs >= MINIMUM_REQUIRED["evidence_packs"],
            evidence_packs,
            MINIMUM_REQUIRED["evidence_packs"],
            f"{evidence_packs} packs in {_iere_root() / 'packs'}",
        ),
        DatasetCheck(
            "Acceptance Fixture Manifest",
            manifest_ok,
            1 if manifest_ok else 0,
            1,
            str(manifest_path),
        ),
    ]

    golden_present = sum(1 for t in GOLDEN_TICKERS if t in vc_rows)
    checks.append(
        DatasetCheck(
            "Golden Tickers",
            golden_present == len(GOLDEN_TICKERS),
            golden_present,
            len(GOLDEN_TICKERS),
            f"{golden_present}/{len(GOLDEN_TICKERS)} golden tickers in valuation consensus",
        )
    )

    all_ok = all(c.ok for c in checks)
    report = {
        "status": "PASS" if all_ok else "FAIL",
        "failure_class": None if all_ok else "INFRASTRUCTURE",
        "checks": [c.to_dict() for c in checks],
        "paths": {
            "fixtures_root": str(fixtures_root()),
            "data_root": str(data_root()),
            "valuation_consensus": str(_vc_root()),
            "ikt": str(_ikt_root()),
            "knowledge_factory": str(_kf_root()),
            "evidence_retrieval": str(_iere_root()),
        },
        "golden_tickers": list(GOLDEN_TICKERS),
    }

    if verbose:
        print("Acceptance Data Health")
        print("-" * 48)
        for c in checks:
            mark = "✓" if c.ok else "✗"
            print(f"{c.name:<32} {mark}  ({c.count}/{c.required})  {c.detail}")
        print("-" * 48)
        print(f"Overall: {'PASS' if all_ok else 'INFRASTRUCTURE FAILURE'}")
    return report


def bootstrap_acceptance_data(*, force: bool = False, verbose: bool = True) -> dict[str, Any]:
    """Copy tracked acceptance fixtures into runtime data directories."""
    src = fixtures_root()
    if not src.is_dir():
        raise FileNotFoundError(f"Acceptance fixtures not found: {src}")

    manifest_path = src / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    dst_root = data_root()
    mappings = [
        (src / "valuation_consensus" / "live.json", _vc_root() / "live.json"),
        (src / "institutional_knowledge_tables" / "facts", _ikt_root() / "facts"),
        (src / "knowledge_factory" / "objects" / "company", _kf_root() / "objects" / "company"),
        (src / "knowledge_factory" / "packs", _kf_root() / "packs"),
        (src / "knowledge_factory" / "historical" / "financials_annual", _kf_root() / "historical" / "financials_annual"),
        (src / "knowledge_factory" / "historical" / "valuation", _kf_root() / "historical" / "valuation"),
        (src / "evidence_retrieval" / "packs", _iere_root() / "packs"),
        (src / "decision_samples" / "samples.json", dst_root / "decision_samples" / "samples.json"),
    ]

    copied: list[str] = []
    for src_path, dst_path in mappings:
        if not src_path.exists():
            continue
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_file():
            if force or not dst_path.exists():
                shutil.copy2(src_path, dst_path)
                copied.append(str(dst_path))
        elif src_path.is_dir():
            dst_path.mkdir(parents=True, exist_ok=True)
            for item in src_path.glob("*.json"):
                target = dst_path / item.name
                if force or not target.exists():
                    shutil.copy2(item, target)
                    copied.append(str(target))

    # Invalidate caches
    try:
        from valuation_consensus.store import invalidate_cache as vc_invalidate

        vc_invalidate()
    except Exception:
        pass
    try:
        from company_identity.service import invalidate_cache as cis_invalidate

        cis_invalidate()
    except Exception:
        pass

    apply_env_defaults()
    health = check_acceptance_data(verbose=verbose)
    return {
        "bootstrapped": True,
        "fixtures_root": str(src),
        "files_copied": len(copied),
        "manifest_version": manifest.get("version"),
        "health": health,
    }


# Suites that require acceptance datasets — empty stores = infrastructure, not product
INFRASTRUCTURE_DEPENDENT_SUITES: frozenset[str] = frozenset(
    {
        "canonical_classification",
        "company_metadata_routing",
        "coverage_acceptance",
    }
)

PRODUCT_SUITES: frozenset[str] = frozenset(
    {
        "founder_evaluation_v2",
        "golden_founder_5",
        "golden_business_20",
        "afi_acceptance",
        "bi_acceptance",
        "bi_integration",
        "ii_acceptance",
        "ii_integration",
        "founder_evaluation_v3",
        "concept_acceptance",
        "kul_acceptance",
        "recommendation_policy",
        "unknown_entity",
        "core_platform_acceptance",
        "answer_quality",
    }
)
