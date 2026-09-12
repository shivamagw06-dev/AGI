"""Persist golden evaluation runs — per-ticker JSON under results/{release}/."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

_LOCK = Lock()
_RUNS: list[dict[str, Any]] = []
_MAX = 50

_IEL_ROOT = Path(__file__).resolve().parent.parent
_REPORTS = _IEL_ROOT / "reports"
_RESULTS = _IEL_ROOT / "results"
_BASELINE_PATH = _REPORTS / "phase1_golden_baseline.json"
_LATEST_PATH = _REPORTS / "phase1_golden_latest.json"

_RELEASE_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _env_root() -> Path | None:
    raw = (os.environ.get("IEL_GOLDEN_STORE_ROOT") or "").strip()
    return Path(raw) if raw else None


def results_root() -> Path:
    """Root for release result trees: results/{release_id}/{TICKER}.json"""
    override = (os.environ.get("IEL_GOLDEN_RESULTS_ROOT") or "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    root = _env_root()
    if root:
        path = root / "results"
        path.mkdir(parents=True, exist_ok=True)
        return path
    _RESULTS.mkdir(parents=True, exist_ok=True)
    return _RESULTS


def sanitize_release_id(release_id: str | None) -> str:
    raw = (release_id or "run").strip() or "run"
    safe = _RELEASE_SAFE.sub("_", raw)
    return safe[:80] or "run"


def release_dir(release_id: str | None) -> Path:
    return results_root() / sanitize_release_id(release_id)


def baseline_path() -> Path:
    root = _env_root()
    if root:
        root.mkdir(parents=True, exist_ok=True)
        return root / "phase1_golden_baseline.json"
    return _BASELINE_PATH


def latest_path() -> Path:
    root = _env_root()
    if root:
        root.mkdir(parents=True, exist_ok=True)
        return root / "phase1_golden_latest.json"
    return _LATEST_PATH


def ticker_result_payload(
    row: dict[str, Any],
    *,
    release_id: str,
    run_id: str | None = None,
    versions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Canonical per-ticker JSON written to results/{release}/{TICKER}.json."""
    # Prefer per-ticker version stamps when present (needed for MODEL drift classification)
    row_versions = row.get("versions") if isinstance(row.get("versions"), dict) else {}
    versions = {**(versions or {}), **row_versions}
    return {
        "ticker": row.get("ticker"),
        "company_name": row.get("company_name") or row.get("name"),
        "sector": row.get("sector"),
        "bucket": row.get("bucket"),
        "investment_opportunity": row.get("investment_opportunity") or row.get("market_opportunity"),
        "analytical_confidence": row.get("analytical_confidence"),
        "release_id": release_id,
        "run_id": run_id,
        "status": row.get("status") or ("COMPLETED" if row.get("ok") else "FAILED"),
        "company_quality": row.get("company_quality"),
        "financial_quality": row.get("financial_quality"),
        "valuation": row.get("valuation"),
        "macro": row.get("macro"),
        "technical": row.get("technical"),
        "risk": row.get("risk"),
        "overall_score": row.get("overall_score"),
        "recommendation_readiness": row.get("recommendation_readiness"),
        "institutional_readiness": row.get("institutional_readiness"),
        "decision": row.get("decision"),
        "action": row.get("action"),
        "readiness_band": row.get("readiness_band"),
        "investment_thesis_status": row.get("investment_thesis_status"),
        "gate": row.get("gate"),
        "gate_status": row.get("gate_status"),
        "evidence_class": row.get("evidence_class"),
        "runtime_ms": row.get("runtime_ms"),
        "timing": row.get("timing") or {},
        "live_price": row.get("live_price"),
        "price_available": row.get("price_available"),
        "price_ltp": row.get("price_ltp"),
        "price_source": row.get("price_source"),
        "price_stale": row.get("price_stale"),
        "pack_present": row.get("pack_present"),
        "knowledge_snapshot": row.get("knowledge_snapshot"),
        "market_snapshot": row.get("market_snapshot"),
        "failure": row.get("failure"),
        "qa_passed": row.get("qa_passed"),
        "qa": row.get("qa"),
        "pipeline": row.get("pipeline"),
        "replay_inputs": row.get("replay_inputs"),
        "versions": versions,
        "errors": row.get("errors") or [],
        "ok": row.get("ok"),
    }


def release_health(rows: list[dict[str, Any]], coverage: dict[str, Any] | None = None) -> dict[str, Any]:
    """At-a-glance release quality metrics for _summary.json."""
    n = len(rows)
    completed = sum(1 for r in rows if str(r.get("status") or "").upper() == "COMPLETED" or r.get("ok"))
    failed = n - completed
    readiness = []
    runtimes = []
    evidence_conf = []
    for r in rows:
        if r.get("recommendation_readiness") is not None:
            try:
                readiness.append(float(r["recommendation_readiness"]))
            except (TypeError, ValueError):
                pass
        t = (r.get("timing") or {}).get("total_ms")
        if t is None:
            t = r.get("runtime_ms")
        if t is not None:
            try:
                runtimes.append(float(t))
            except (TypeError, ValueError):
                pass
        # evidence confidence ≈ readiness when diagnostic gate not present
        if r.get("recommendation_readiness") is not None:
            try:
                evidence_conf.append(float(r["recommendation_readiness"]) / 100.0)
            except (TypeError, ValueError):
                pass
    cov = coverage or {}
    gate_pass_rate = cov.get("gate_pass_rate_pct")
    if gate_pass_rate is not None:
        try:
            gate_pass_rate = round(float(gate_pass_rate) / 100.0, 4)
        except (TypeError, ValueError):
            gate_pass_rate = None
    return {
        "companies": n,
        "completed": completed,
        "failed": failed,
        "gate_pass_rate": gate_pass_rate,
        "average_readiness": round((sum(readiness) / len(readiness)) / 100.0, 4) if readiness else None,
        "average_runtime_ms": int(sum(runtimes) / len(runtimes)) if runtimes else None,
        "average_evidence_confidence": round(sum(evidence_conf) / len(evidence_conf), 4)
        if evidence_conf
        else None,
    }


def save_release_results(summary: dict[str, Any]) -> dict[str, Any]:
    """
    Write the durable Evaluation Lab artifact tree:

        results/
          PR306/
            HDFCBANK.json
            RELIANCE.json
            ...
            _summary.json
            _manifest.json
    """
    from datetime import datetime, timezone

    from institutional_evaluation_lab.golden_universe.schema import collect_version_metadata

    release = sanitize_release_id(str(summary.get("release_id") or summary.get("run_id") or "run"))
    out_dir = release_dir(release)
    out_dir.mkdir(parents=True, exist_ok=True)
    versions = summary.get("versions") or collect_version_metadata()
    timestamp = summary.get("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    written: list[str] = []
    rows = [r for r in (summary.get("rows") or []) if isinstance(r, dict) and r.get("ticker")]
    for row in rows:
        ticker = str(row["ticker"]).upper()
        path = out_dir / f"{ticker}.json"
        payload = ticker_result_payload(
            row,
            release_id=release,
            run_id=summary.get("run_id"),
            versions=versions,
        )
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        written.append(ticker)

    market_snaps = [r.get("market_snapshot") for r in rows if r.get("market_snapshot")]
    knowledge_snaps = [r.get("knowledge_snapshot") for r in rows if r.get("knowledge_snapshot")]
    health = release_health(rows, summary.get("coverage"))

    manifest = {
        "release_id": release,
        "timestamp": timestamp,
        "git_commit": summary.get("commit"),
        "run_id": summary.get("run_id"),
        "constitution_version": versions.get("constitution_version"),
        "decision_engine_version": versions.get("decision_engine_version"),
        "readiness_gate_version": versions.get("readiness_gate_version"),
        "knowledge_snapshot": knowledge_snaps[0] if knowledge_snaps else None,
        "market_snapshot": market_snaps[0] if market_snaps else None,
        "golden_set_version": versions.get("golden_set_version"),
        "golden_universe_version": versions.get("golden_universe_version"),
        "golden_composition_sha256": versions.get("golden_composition_sha256"),
        "runner_version": versions.get("runner_version"),
        "eval_version": versions.get("eval_version") or summary.get("version"),
        "suite": summary.get("suite"),
        "n": len(written),
        "tickers": written,
        "results_dir": str(out_dir),
        "layout": "results/{release_id}/{TICKER}.json",
        "health": health,
    }
    (out_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    light_summary = {
        k: v
        for k, v in summary.items()
        if k not in {"rows", "drift_table"}
    }
    light_summary["timestamp"] = timestamp
    light_summary["versions"] = versions
    light_summary["results_dir"] = str(out_dir)
    light_summary["ticker_files"] = len(written)
    light_summary.update(health)
    # Keep nested health for consumers that prefer the block
    light_summary["health"] = health
    (out_dir / "_summary.json").write_text(
        json.dumps(light_summary, indent=2, default=str), encoding="utf-8"
    )

    return {
        "release_id": release,
        "results_dir": str(out_dir),
        "n": len(written),
        "tickers": written,
        "manifest_path": str(out_dir / "_manifest.json"),
        "summary_path": str(out_dir / "_summary.json"),
        "health": health,
    }


def load_release_results(release_id: str) -> dict[str, Any] | None:
    """Load a prior release tree for Phase 6+ governance tests / drift."""
    out_dir = release_dir(release_id)
    manifest_path = out_dir / "_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    rows: list[dict[str, Any]] = []
    for ticker in manifest.get("tickers") or []:
        path = out_dir / f"{str(ticker).upper()}.json"
        if not path.exists():
            continue
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    summary = None
    summary_path = out_dir / "_summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            summary = None
    return {
        "release_id": sanitize_release_id(release_id),
        "results_dir": str(out_dir),
        "manifest": manifest,
        "summary": summary,
        "rows": rows,
        "n": len(rows),
    }


def list_releases() -> list[dict[str, Any]]:
    root = results_root()
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        man = child / "_manifest.json"
        if not man.exists():
            continue
        try:
            meta = json.loads(man.read_text(encoding="utf-8"))
        except Exception:
            meta = {"release_id": child.name, "n": None}
        out.append(
            {
                "release_id": meta.get("release_id") or child.name,
                "n": meta.get("n"),
                "results_dir": str(child),
                "commit": meta.get("commit"),
            }
        )
    return out


def record_run(summary: dict[str, Any]) -> dict[str, Any]:
    light = {
        "record_id": f"golden-{uuid4().hex[:12]}",
        **{k: v for k, v in summary.items() if k != "rows"},
        "n_rows": len(summary.get("rows") or []),
    }
    with _LOCK:
        _RUNS.append(light)
        if len(_RUNS) > _MAX:
            del _RUNS[: len(_RUNS) - _MAX]
    return deepcopy(light)


def list_runs(*, limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_RUNS)
    return deepcopy(list(reversed(rows[-max(1, min(int(limit), 50)) :])))


def save_latest(summary: dict[str, Any]) -> dict[str, Any]:
    path = latest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": summary.get("run_id"),
        "release_id": summary.get("release_id"),
        "commit": summary.get("commit"),
        "suite": summary.get("suite"),
        "n": summary.get("n"),
        "coverage": summary.get("coverage"),
        "sector": summary.get("sector"),
        "qa": {k: v for k, v in (summary.get("qa") or {}).items() if k != "failures"},
        "scorecard": summary.get("scorecard"),
        "rows": summary.get("rows") or [],
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {"path": str(path), "n": len(payload["rows"])}


def load_latest() -> dict[str, Any] | None:
    path = latest_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_baseline(summary: dict[str, Any]) -> dict[str, Any]:
    path = baseline_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": summary.get("run_id"),
        "release_id": summary.get("release_id"),
        "commit": summary.get("commit"),
        "suite": summary.get("suite"),
        "n": summary.get("n"),
        "coverage": summary.get("coverage"),
        "scorecard": summary.get("scorecard"),
        "rows": [
            {
                "ticker": r.get("ticker"),
                "decision": r.get("decision"),
                "recommendation_readiness": r.get("recommendation_readiness"),
                "gate": r.get("gate"),
                "evidence_class": r.get("evidence_class"),
                "sector": r.get("sector"),
                "bucket": r.get("bucket"),
                "overall_score": r.get("overall_score"),
                "company_quality": r.get("company_quality"),
                "financial_quality": r.get("financial_quality"),
                "valuation": r.get("valuation"),
            }
            for r in (summary.get("rows") or [])
            if isinstance(r, dict)
        ],
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {"path": str(path), "n": len(payload["rows"]), "run_id": payload.get("run_id")}


def load_baseline() -> dict[str, Any] | None:
    path = baseline_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
