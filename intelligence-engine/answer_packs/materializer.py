"""Background materialization of company answer packs from AGI-owned data."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from answer_packs.builder import build_answer_pack
from company_identity.core_aliases import CORE_COMPANY_ALIASES


def store_root() -> Path:
    configured = (os.getenv("ANSWER_PACK_STORE_ROOT") or "").strip()
    if configured:
        return Path(configured)
    kip = (os.getenv("KIP_DATA_DIR") or "/var/data/kip").strip()
    return Path(kip) / "answer_packs"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_materialized_pack(ticker: str) -> dict[str, Any]:
    return _read(store_root() / f"{str(ticker or '').upper()}.json")


def _content_hash(pack: dict[str, Any]) -> str:
    stable = {k: v for k, v in pack.items() if k not in {"generated_at", "materialization"}}
    raw = json.dumps(stable, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def covered_universe() -> list[str]:
    """Return a stable core-first universe from AGI's persisted registries."""
    tickers = [ticker for ticker, _ in CORE_COMPANY_ALIASES]
    try:
        from institutional_warehouse import store

        tickers.extend(str(ticker).upper() for ticker in store.entities("company_master"))
    except Exception:
        pass
    try:
        from valuation_consensus.store import list_tickers

        tickers.extend(str(ticker).upper() for ticker in list_tickers())
    except Exception:
        pass
    return list(dict.fromkeys(ticker for ticker in tickers if ticker))


def materialize_batch(
    *,
    batch_size: int = 5,
    start_cursor: int = 0,
    analyser: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Refresh a rotating batch without any LLM or user-request dependency."""
    if analyser is None:
        from company_analysis.production import analyse as analyser

    universe = covered_universe()
    if not universe:
        return {"ok": True, "attempted": 0, "written": 0, "unchanged": 0, "next_cursor": 0}
    size = max(1, min(int(batch_size), len(universe)))
    start = int(start_cursor or 0) % len(universe)
    selected = [universe[(start + offset) % len(universe)] for offset in range(size)]
    written = 0
    unchanged = 0
    failures: list[dict[str, str]] = []
    now = datetime.now(timezone.utc).isoformat()

    for ticker in selected:
        try:
            analysis = analyser(
                f"Build the current institutional research pack for {ticker}",
                ticker=ticker,
                record=False,
            ) or {}
            executive = str(
                analysis.get("executive_summary")
                or analysis.get("business_overview")
                or f"Current AGI company-analysis pack for {ticker}."
            )
            pack = build_answer_pack(
                question=f"Background company intelligence for {ticker}",
                ticker=ticker,
                executive=executive,
                confidence=(analysis.get("recommendation_readiness") or {}).get("overall"),
                company_analysis=analysis,
                investment_thesis=analysis.get("investment_thesis"),
                bull_case=analysis.get("bull_case"),
                bear_case=analysis.get("bear_case"),
                risks=analysis.get("key_risks") or analysis.get("risks"),
                catalysts=analysis.get("key_catalysts") or analysis.get("catalysts"),
                valuation=analysis.get("valuation_intelligence"),
                evidence_used=(analysis.get("evidence") or {}).get("items")
                if isinstance(analysis.get("evidence"), dict)
                else analysis.get("evidence") or [],
                freshness=analysis.get("generated_at"),
                quality_gates={
                    "financials_supported": bool(
                        (analysis.get("financial_intelligence") or {}).get("coverage_pct")
                    ),
                    "valuation_supported": bool(
                        (analysis.get("valuation_intelligence") or {}).get("coverage_pct")
                    ),
                },
                knowledge_gaps=(analysis.get("recommendation_readiness") or {}).get("missing") or [],
            )
            digest = _content_hash(pack)
            path = store_root() / f"{ticker}.json"
            previous = _read(path)
            if (previous.get("materialization") or {}).get("content_hash") == digest:
                unchanged += 1
                continue
            pack["materialization"] = {
                "content_hash": digest,
                "materialized_at": now,
                "source": "company_analysis_database_pack",
                "llm_used": False,
            }
            _write_atomic(path, pack)
            written += 1
        except Exception as exc:  # noqa: BLE001 - one company must not stop the batch
            failures.append({"ticker": ticker, "error": str(exc)[:240]})

    return {
        "ok": not failures,
        "attempted": len(selected),
        "written": written,
        "unchanged": unchanged,
        "failures": failures,
        "tickers": selected,
        "next_cursor": (start + size) % len(universe),
        "store_root": str(store_root()),
        "generated_at": now,
    }
