"""Resolve measurement universes for the Evidence Coverage Dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from financial_statements_engine.schema import GOLD_UNIVERSE


def _default_hd_root() -> Path:
    raw = (os.environ.get("KF_HD_STORE_ROOT") or "").strip()
    if raw:
        return Path(raw)
    kip = (os.environ.get("KIP_DATA_DIR") or "").strip()
    if kip:
        return Path(kip) / "historical_depth"
    # intelligence-engine/data/knowledge_factory/historical
    return Path(__file__).resolve().parents[2] / "data" / "knowledge_factory" / "historical"


def hd_financial_tickers() -> list[str]:
    root = _default_hd_root()
    tickers: set[str] = set()
    for kind in ("financials_annual", "financials_quarterly"):
        d = root / kind
        if not d.is_dir():
            continue
        for p in d.glob("*.json"):
            tickers.add(p.stem.upper())
    return sorted(tickers)


def _nifty50() -> list[str]:
    try:
        from institutional_reasoning.fundamentals.universe import NIFTY_50

        return [str(t).upper() for t in NIFTY_50]
    except Exception:
        return list(GOLD_UNIVERSE)


def _nifty100() -> list[str]:
    try:
        from institutional_reasoning.fundamentals.universe import NIFTY_50, NIFTY_100_EXTRA

        return [str(t).upper() for t in list(NIFTY_50) + list(NIFTY_100_EXTRA)]
    except Exception:
        return _nifty50()


def _nifty500() -> list[str]:
    try:
        from institutional_reasoning.fundamentals.nifty500_universe import NIFTY_500

        return [str(t).upper() for t in NIFTY_500]
    except Exception:
        # CSV fallback
        csv_path = Path(__file__).resolve().parents[3] / "Nifty500.csv"
        if csv_path.exists():
            rows = []
            for i, line in enumerate(csv_path.read_text(encoding="utf-8").splitlines()):
                if i == 0 and ("symbol" in line.lower() or "ticker" in line.lower()):
                    continue
                sym = line.split(",")[0].strip().upper()
                if sym:
                    rows.append(sym)
            if rows:
                return rows
        return _nifty100()


def resolve_universe(universe: str = "nifty500") -> dict[str, Any]:
    u = (universe or "nifty500").lower().strip()
    if u in ("gold", "ic5"):
        tickers = [str(t).upper() for t in GOLD_UNIVERSE]
        label = "gold"
    elif u in ("nifty50", "n50"):
        tickers = _nifty50()
        label = "nifty50"
    elif u in ("nifty100", "n100"):
        tickers = _nifty100()
        label = "nifty100"
    elif u in ("hd", "historical", "on_disk"):
        tickers = hd_financial_tickers()
        label = "hd"
    else:
        tickers = _nifty500()
        label = "nifty500"

    seen: set[str] = set()
    ordered: list[str] = []
    for t in tickers:
        if t and t not in seen:
            seen.add(t)
            ordered.append(t)
    return {
        "universe": label,
        "universe_size": len(ordered),
        "tickers": ordered,
        "primary_universe_policy": "nifty500",
        "hd_root": str(_default_hd_root()),
    }
