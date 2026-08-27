"""Static pair discovery — sector peers, index constituents, user-defined. No optimisation."""

from __future__ import annotations

from typing import Any


def canonical_pair_id(leg_a: str, leg_b: str) -> str:
    a, b = leg_a.upper(), leg_b.upper()
    if a == b:
        raise ValueError("pair legs must differ")
    left, right = sorted((a, b))
    return f"{left}_{right}"


def parse_pair_id(pair_id: str) -> tuple[str, str]:
    parts = pair_id.upper().split("_")
    if len(parts) < 2:
        raise ValueError(f"invalid pair_id: {pair_id}")
    # Support multi-underscore tickers poorly — P0 assumes single-token legs
    if len(parts) == 2:
        return parts[0], parts[1]
    # fallback: split once from right for names like HDFC_BANK_SBIN → not supported;
    # require exactly two tokens for P0.
    raise ValueError(f"invalid pair_id (expect LEGA_LEGB): {pair_id}")


def discover_pairs(
    *,
    symbols: list[str],
    sectors: dict[str, str | None],
    user_pairs: list[tuple[str, str]] | None = None,
    static_pairs: list[tuple[str, str]] | None = None,
    index_constituents: bool = True,
    sector_peers: bool = True,
    max_pairs: int = 50,
) -> list[tuple[str, str]]:
    """Build a static pair universe. Deterministic ordering. No automatic optimisation."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []

    def _add(a: str, b: str) -> None:
        if a.upper() == b.upper():
            return
        pid = canonical_pair_id(a, b)
        if pid in seen:
            return
        seen.add(pid)
        left, right = parse_pair_id(pid)
        out.append((left, right))

    for a, b in static_pairs or []:
        _add(a, b)
    for a, b in user_pairs or []:
        _add(a, b)

    syms = sorted({s.upper() for s in symbols})
    if sector_peers:
        by_sec: dict[str, list[str]] = {}
        for s in syms:
            sec = (sectors.get(s) or sectors.get(s.lower()) or "__NONE__").upper()
            by_sec.setdefault(sec, []).append(s)
        for sec, members in sorted(by_sec.items()):
            if sec == "__NONE__" or len(members) < 2:
                continue
            members = sorted(members)
            for i, a in enumerate(members):
                for b in members[i + 1 :]:
                    _add(a, b)
                    if len(out) >= max_pairs:
                        return out[:max_pairs]

    if index_constituents and len(syms) >= 2:
        # Adjacent index pairs as a static constituent lattice (not optimised)
        for i, a in enumerate(syms):
            if i + 1 < len(syms):
                _add(a, syms[i + 1])
            if len(out) >= max_pairs:
                break

    return out[:max_pairs]


def extract_closes(panel: dict[str, Any] | None) -> list[float] | None:
    if not panel:
        return None
    closes = panel.get("closes") or panel.get("log_prices")
    if isinstance(closes, list) and len(closes) >= 8:
        try:
            return [float(x) for x in closes]
        except (TypeError, ValueError):
            return None
    return None


def synthesize_closes(panel: dict[str, Any], *, n: int = 60, seed: str = "") -> list[float]:
    """Deterministic synthetic price path from panel returns when closes absent."""
    # Simple LCG seeded from symbol chars + returns
    h = 2166136261
    for ch in seed:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    ret_s = float(panel.get("ret_3_0") or panel.get("ret_short") or 0.0)
    ret_m = float(panel.get("ret_6_1") or panel.get("ret_medium") or 0.0)
    ret_l = float(panel.get("ret_12_1") or panel.get("ret_long") or 0.0)
    mu = (0.2 * ret_s + 0.3 * ret_m + 0.5 * ret_l) / max(n / 21.0, 1.0)
    vol = float(panel.get("sigma_60") or panel.get("realized_vol_20") or 0.20) / (252**0.5)
    level = 100.0
    out: list[float] = []
    state = h or 1
    for i in range(n):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        # deterministic pseudo-noise in [-1,1]
        noise = ((state % 10000) / 5000.0) - 1.0
        # mild mean path + noise
        r = mu + vol * noise * 0.5
        level *= 1.0 + r
        out.append(round(level, 8))
    return out
