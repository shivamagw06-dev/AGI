"""Universe loaders for scale testing (Nifty500 / IC-10 / custom)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from production_hardening.schema import GOLD_REGRESSION_UNIVERSE


def nifty500_path() -> Path:
    # Prefer full NSE trading book (NIFTYstocks from EQUITY_L); fall back to Nifty500.
    here = Path(__file__).resolve()
    candidates = [
        Path("/workspace/NIFTYstocks.csv"),
        here.parents[2] / "NIFTYstocks.csv",
        here.parents[3] / "NIFTYstocks.csv",
        Path.cwd() / "NIFTYstocks.csv",
        Path.cwd().parent / "NIFTYstocks.csv",
        Path("/workspace/Nifty500.csv"),
        here.parents[2] / "Nifty500.csv",
        here.parents[3] / "Nifty500.csv",
        Path.cwd() / "Nifty500.csv",
        Path.cwd().parent / "Nifty500.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_nifty500_symbols(*, limit: int | None = None) -> list[str]:
    """Load symbols from NIFTYstocks (full trading universe) or Nifty500 fallback."""
    path = nifty500_path()
    if not path.exists():
        # Fallback to opportunity IC-10
        try:
            from opportunity_intelligence.schema import IC10_UNIVERSE

            syms = list(IC10_UNIVERSE)
        except Exception:
            syms = list(GOLD_REGRESSION_UNIVERSE)
        return syms[:limit] if limit else syms

    symbols: list[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = (row.get("Symbol") or row.get("symbol") or "").strip().upper()
            if sym:
                symbols.append(sym)
    # Deterministic order as file order
    if limit is not None:
        symbols = symbols[: max(0, int(limit))]
    return symbols


def resolve_universe(
    *,
    preset: str | None = None,
    limit: int | None = None,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    from production_hardening.schema import SCALE_PRESETS

    if symbols:
        out = [s.upper().strip() for s in symbols if s and str(s).strip()]
        return {"source": "explicit", "n": len(out), "symbols": out}

    p = (preset or "smoke").lower().strip()
    if p == "gold":
        out = list(GOLD_REGRESSION_UNIVERSE)
        return {"source": "gold_regression", "n": len(out), "symbols": out}
    if p in {"ic10", "smoke"}:
        # smoke defaults to IC-10 (warm compiled cache) for CI predictability
        try:
            from opportunity_intelligence.schema import IC10_UNIVERSE

            out = list(IC10_UNIVERSE)
        except Exception:
            out = list(GOLD_REGRESSION_UNIVERSE)
        if p == "smoke" and limit is not None:
            out = out[: max(0, int(limit))]
        return {"source": "ic10" if p == "ic10" else "ic10_smoke", "n": len(out), "symbols": out, "preset": p}

    if p in {"all", "nse", "equity", "equity_l", "trading", "niftystocks"}:
        out = load_nifty500_symbols(limit=limit)
        return {
            "source": "nse_trading_universe",
            "preset": p,
            "file": str(nifty500_path()),
            "n": len(out),
            "symbols": out,
            "role": "all_equity_stocks_available_for_trading",
        }

    preset_limit = SCALE_PRESETS.get(p, SCALE_PRESETS["sample_100"])
    effective = limit if limit is not None else preset_limit
    out = load_nifty500_symbols(limit=effective)
    source_name = "niftystocks" if "NIFTYstocks" in str(nifty500_path()) else "nifty500"
    return {
        "source": f"{source_name}:{p}",
        "preset": p,
        "limit": effective,
        "file": str(nifty500_path()),
        "n": len(out),
        "symbols": out,
    }
