"""Name / sector risk caps — iterative clip + renormalise (no optimiser)."""

from __future__ import annotations

from collections import defaultdict

from app.engines.e10.construction.select import Candidate
from app.engines.e10.mapping import NAME_CAP, SECTOR_CAP


def apply_risk_caps(
    equity_weights: dict[str, float],
    candidates: list[Candidate],
    *,
    name_cap: float = NAME_CAP,
    sector_cap: float = SECTOR_CAP,
    equity_budget: float = 1.0,
) -> tuple[dict[str, float], list[str]]:
    """Enforce |w_i| ≤ name_cap and sector sum ≤ sector_cap within equity_budget."""
    if not equity_weights or equity_budget <= 0:
        return {}, []

    sector_of = {c.symbol: (c.sector_id or "__UNKNOWN__") for c in candidates}
    binding: list[str] = []
    w = {s: float(v) * equity_budget for s, v in equity_weights.items()}

    for _ in range(25):
        # Name cap
        clipped = False
        for sym, weight in list(w.items()):
            if weight > name_cap + 1e-12:
                w[sym] = name_cap
                clipped = True
                tag = f"C_NAME:{sym}"
                if tag not in binding:
                    binding.append(tag)
        # Sector cap
        by_sector: dict[str, list[str]] = defaultdict(list)
        for sym in w:
            by_sector[sector_of.get(sym, "__UNKNOWN__")].append(sym)
        for sector, syms in by_sector.items():
            total = sum(w[s] for s in syms)
            if total > sector_cap + 1e-12:
                scale = sector_cap / total
                for s in syms:
                    w[s] *= scale
                clipped = True
                tag = f"C_SECTOR:{sector}"
                if tag not in binding:
                    binding.append(tag)
        # Renormalise to equity_budget
        gross = sum(w.values())
        if gross <= 1e-12:
            return {s: 0.0 for s in w}, binding
        if abs(gross - equity_budget) > 1e-9:
            scale = equity_budget / gross
            # Only scale up if it won't immediately breach caps; otherwise leave slack → cash
            if scale < 1.0 - 1e-12 or not clipped:
                w = {s: v * scale for s, v in w.items()}
            elif scale > 1.0 + 1e-12:
                # Try gentle scale-up respecting caps
                room = True
                trial = {s: v * scale for s, v in w.items()}
                for sym, weight in trial.items():
                    if weight > name_cap + 1e-9:
                        room = False
                        break
                by_sec: dict[str, float] = defaultdict(float)
                for sym, weight in trial.items():
                    by_sec[sector_of.get(sym, "__UNKNOWN__")] += weight
                if any(v > sector_cap + 1e-9 for v in by_sec.values()):
                    room = False
                if room:
                    w = trial
                else:
                    # Cannot fill equity_budget — residual becomes cash
                    binding.append("C_BUDGET_SLACK")
                    break
        else:
            if not clipped:
                break
            # Check if still violating after renorm
            if all(v <= name_cap + 1e-9 for v in w.values()):
                ok_sec = True
                by_sec2: dict[str, float] = defaultdict(float)
                for sym, weight in w.items():
                    by_sec2[sector_of.get(sym, "__UNKNOWN__")] += weight
                if any(v > sector_cap + 1e-9 for v in by_sec2.values()):
                    ok_sec = False
                if ok_sec:
                    break

    # Final hard clip (never exceed caps)
    for sym in list(w):
        if w[sym] > name_cap:
            w[sym] = name_cap
            tag = f"C_NAME:{sym}"
            if tag not in binding:
                binding.append(tag)
    by_sector_f: dict[str, list[str]] = defaultdict(list)
    for sym in w:
        by_sector_f[sector_of.get(sym, "__UNKNOWN__")].append(sym)
    for sector, syms in by_sector_f.items():
        total = sum(w[s] for s in syms)
        if total > sector_cap + 1e-12:
            scale = sector_cap / total
            for s in syms:
                w[s] *= scale
            tag = f"C_SECTOR:{sector}"
            if tag not in binding:
                binding.append(tag)

    return {s: round(v, 8) for s, v in w.items()}, binding
