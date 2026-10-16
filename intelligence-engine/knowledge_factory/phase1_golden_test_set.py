"""Phase 1 Golden Test Set — institutional benchmark universe (200 stocks).

Composition:
  • Nifty 50              — 50
  • Nifty Next 50         — 50
  • Midcaps               — 50
  • Smallcaps             — 25
  • Loss-making / special — 25

Purpose: broad sector + company-profile coverage for governance, readiness,
decision-engine, and evaluation-lab regression — not a claim of live coverage.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.kc.universes import NIFTY_50 as _KC_NIFTY_50
from app.kc.universes import NIFTY_NEXT_50 as _KC_NIFTY_NEXT_50

PHASE1_VERSION = "phase1-golden-test-set-v1.0.0"
# Human-facing frozen benchmark tag — bump only via an explicit v1.1 module/PR.
GOLDEN_UNIVERSE_VERSION = "v1.0"
FROZEN = True
PHASE1_TARGET_N = 200
# Pin composition — silently editing v1.0 tickers must fail validation/tests.
FROZEN_COMPOSITION_SHA256 = "776b04f31bf754b25d8b281f8e352871db03ff73a3664a52723a514a0f3b5a26"

BUCKETS = (
    "nifty_50",
    "nifty_next_50",
    "midcap",
    "smallcap",
    "special_situation",
)


def _row(
    ticker: str,
    name: str,
    sector: str,
    *,
    bucket: str,
    profile: str = "",
    aliases: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "name": name,
        "sector": sector,
        "bucket": bucket,
        "market_cap_bucket": {
            "nifty_50": "large",
            "nifty_next_50": "large",
            "midcap": "mid",
            "smallcap": "small",
            "special_situation": "special",
        }.get(bucket, "unknown"),
        "profile": profile,
        "aliases": list(aliases or []),
        "notes": notes,
        "suite": "phase1_golden",
        "version": PHASE1_VERSION,
    }


# NSE symbol renames observed in the current Nifty 500 dump — keep legacy aliases.
_SYMBOL_NORMALIZE: dict[str, tuple[str, str]] = {
    # demerger: passenger vehicles is the primary listed successor in index sets
    "TATAMOTORS": ("TMPV", "Tata Motors Passenger Vehicles"),
    # LTIMindtree abbreviated listing
    "LTIM": ("LTM", "LTM"),
}


def _normalized_index_rows(
    source: list[dict[str, str]],
    *,
    bucket: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in source:
        t = r["ticker"].upper()
        if t in _SYMBOL_NORMALIZE:
            new_t, new_name = _SYMBOL_NORMALIZE[t]
            out.append(
                _row(
                    new_t,
                    new_name,
                    r["sector"],
                    bucket=bucket,
                    profile="index_large_cap",
                    aliases=[t],
                    notes=f"NSE rename/successor of {t}",
                )
            )
        else:
            out.append(
                _row(t, r["name"], r["sector"], bucket=bucket, profile="index_large_cap")
            )
    return out


# ---------------------------------------------------------------------------
# Nifty 50 / Next 50 — reuse KC canonical lists (names + sectors)
# ---------------------------------------------------------------------------

NIFTY_50_ROWS: list[dict[str, Any]] = _normalized_index_rows(_KC_NIFTY_50, bucket="nifty_50")

NIFTY_NEXT_50_ROWS: list[dict[str, Any]] = _normalized_index_rows(
    _KC_NIFTY_NEXT_50, bucket="nifty_next_50"
)


# ---------------------------------------------------------------------------
# Midcaps (50) — liquid Nifty 500 names outside Nifty 100
# ---------------------------------------------------------------------------

MIDCAP_SEED: list[tuple[str, str, str]] = [
    ("BHEL", "Bharat Heavy Electricals", "Capital Goods"),
    ("CONCOR", "Container Corporation", "Logistics"),
    ("OFSS", "Oracle Financial Services", "IT Services"),
    ("PAGEIND", "Page Industries", "Consumer"),
    ("VOLTAS", "Voltas", "Consumer Durables"),
    ("CROMPTON", "Crompton Greaves Consumer", "Consumer Durables"),
    ("BERGEPAINT", "Berger Paints", "Chemicals"),
    ("ALKEM", "Alkem Laboratories", "Pharma"),
    ("LAURUSLABS", "Laurus Labs", "Pharma"),
    ("SYNGENE", "Syngene International", "Pharma"),
    ("MAXHEALTH", "Max Healthcare", "Healthcare"),
    ("FORTIS", "Fortis Healthcare", "Healthcare"),
    ("GODREJPROP", "Godrej Properties", "Real Estate"),
    ("OBEROIRLTY", "Oberoi Realty", "Real Estate"),
    ("PRESTIGE", "Prestige Estates", "Real Estate"),
    ("MOTHERSON", "Samvardhana Motherson", "Auto"),
    ("BOSCHLTD", "Bosch", "Auto"),
    ("BALKRISIND", "Balkrishna Industries", "Auto"),
    ("PIIND", "PI Industries", "Chemicals"),
    ("SRF", "SRF", "Chemicals"),
    ("AARTIIND", "Aarti Industries", "Chemicals"),
    ("NAUKRI", "Info Edge", "Internet"),
    ("TATAPOWER", "Tata Power", "Power"),
    ("ADANIGREEN", "Adani Green Energy", "Power"),
    ("APLAPOLLO", "APL Apollo Tubes", "Capital Goods"),
    ("AUBANK", "AU Small Finance Bank", "Banking"),
    ("ACC", "ACC", "Cement"),
    ("ABCAPITAL", "Aditya Birla Capital", "Financial Services"),
    ("ABBOTINDIA", "Abbott India", "Pharma"),
    ("CGPOWER", "CG Power", "Capital Goods"),
    ("CUMMINSIND", "Cummins India", "Capital Goods"),
    ("ESCORTS", "Escorts Kubota", "Auto"),
    ("EXIDEIND", "Exide Industries", "Auto"),
    ("GLENMARK", "Glenmark Pharmaceuticals", "Pharma"),
    ("HDFCAMC", "HDFC AMC", "Financial Services"),
    ("INDHOTEL", "Indian Hotels", "Consumer"),
    ("JSWENERGY", "JSW Energy", "Power"),
    ("KEI", "KEI Industries", "Capital Goods"),
    ("LICHSGFIN", "LIC Housing Finance", "Financial Services"),
    ("MANAPPURAM", "Manappuram Finance", "Financial Services"),
    ("MFSL", "Max Financial Services", "Financial Services"),
    ("MRF", "MRF", "Auto"),
    ("PETRONET", "Petronet LNG", "Energy"),
    ("PHOENIXLTD", "Phoenix Mills", "Real Estate"),
    ("RVNL", "Rail Vikas Nigam", "Capital Goods"),
    ("SOLARINDS", "Solar Industries", "Chemicals"),
    ("SUPREMEIND", "Supreme Industries", "Chemicals"),
    ("TATACOMM", "Tata Communications", "Telecom"),
    ("TIINDIA", "Tube Investments of India", "Auto"),
    ("TORNTPOWER", "Torrent Power", "Power"),
]

MIDCAP_ROWS: list[dict[str, Any]] = [
    _row(t, n, s, bucket="midcap", profile="midcap_liquid") for t, n, s in MIDCAP_SEED
]


# ---------------------------------------------------------------------------
# Smallcaps (25) — smaller / more specialised Nifty 500 names
# ---------------------------------------------------------------------------

SMALLCAP_SEED: list[tuple[str, str, str]] = [
    ("AAVAS", "Aavas Financiers", "Financial Services"),
    ("ANGELONE", "Angel One", "Financial Services"),
    ("ASTRAL", "Astral", "Capital Goods"),
    ("BANDHANBNK", "Bandhan Bank", "Banking"),
    ("BATAINDIA", "Bata India", "Consumer"),
    ("CAMS", "Computer Age Management Services", "Financial Services"),
    ("CDSL", "Central Depository Services", "Financial Services"),
    ("CLEAN", "Clean Science and Technology", "Chemicals"),
    ("CREDITACC", "CreditAccess Grameen", "Financial Services"),
    ("CYIENT", "Cyient", "IT Services"),
    ("DEEPAKNTR", "Deepak Nitrite", "Chemicals"),
    ("FACT", "Fertilisers and Chemicals Travancore", "Chemicals"),
    ("FLUOROCHEM", "Gujarat Fluorochemicals", "Chemicals"),
    ("AFFLE", "Affle India", "IT Services"),
    ("INDIAMART", "IndiaMART InterMESH", "Internet"),
    ("KPITTECH", "KPIT Technologies", "IT Services"),
    ("LATENTVIEW", "Latent View Analytics", "IT Services"),
    ("MAZDOCK", "Mazagon Dock Shipbuilders", "Defence"),
    ("NATCOPHARM", "Natco Pharma", "Pharma"),
    ("RADICO", "Radico Khaitan", "FMCG"),
    ("SONACOMS", "Sona BLW Precision Forgings", "Auto"),
    ("TATAELXSI", "Tata Elxsi", "IT Services"),
    ("TRITURBINE", "Triveni Turbine", "Capital Goods"),
    ("MAPMYINDIA", "C.E. Info Systems (MapmyIndia)", "IT Services"),
    ("KALYANKJIL", "Kalyan Jewellers", "Retail"),
]

SMALLCAP_ROWS: list[dict[str, Any]] = [
    _row(t, n, s, bucket="smallcap", profile="smallcap") for t, n, s in SMALLCAP_SEED
]


# ---------------------------------------------------------------------------
# Special situations (25) — loss-making, turnaround, stress, path-to-profit
# ---------------------------------------------------------------------------

SPECIAL_SEED: list[tuple[str, str, str, str, list[str]]] = [
    ("IDEA", "Vodafone Idea", "Telecom", "chronic_losses_leverage", []),
    ("PAYTM", "One 97 Communications", "Financial Services", "path_to_profit", []),
    ("NYKAA", "FSN E-Commerce (Nykaa)", "Retail", "thin_margin_growth", []),
    ("DELHIVERY", "Delhivery", "Logistics", "unit_economics", []),
    ("POLICYBZR", "PB Fintech", "Financial Services", "growth_over_profit", []),
    ("YESBANK", "Yes Bank", "Banking", "reconstruction", []),
    ("SUZLON", "Suzlon Energy", "Capital Goods", "debt_turnaround", []),
    ("JPPOWER", "Jaiprakash Power Ventures", "Power", "stressed_power", []),
    ("GMRAIRPORT", "GMR Airports", "Infrastructure", "infra_leverage", []),
    ("ZEEL", "Zee Entertainment", "Media", "governance_special", []),
    ("PNBHOUSING", "PNB Housing Finance", "Financial Services", "nbfc_stress_history", []),
    ("RPOWER", "Reliance Power", "Power", "stressed_power", []),
    ("TTML", "Tata Teleservices (Maharashtra)", "Telecom", "telecom_losses", []),
    ("HFCL", "HFCL", "Telecom", "cyclical_special", []),
    ("OLAELEC", "Ola Electric Mobility", "Auto", "ev_oem_losses", []),
    ("ATHERENERG", "Ather Energy", "Auto", "ev_oem_losses", []),
    ("IOB", "Indian Overseas Bank", "Banking", "psu_turnaround", []),
    ("UCOBANK", "UCO Bank", "Banking", "psu_turnaround", []),
    ("CENTRALBK", "Central Bank of India", "Banking", "psu_turnaround", []),
    ("HONASA", "Honasa Consumer", "FMCG", "d2c_scale_special", []),
    ("SWIGGY", "Swiggy", "Consumer Internet", "path_to_profit", []),
    ("FIRSTCRY", "Brainbees Solutions (FirstCry)", "Consumer Internet", "growth_special", []),
    ("TEJASNET", "Tejas Networks", "Telecom", "capex_cyclical", []),
    ("IDBI", "IDBI Bank", "Banking", "ownership_turnaround", []),
    ("ETERNAL", "Eternal (Zomato)", "Consumer Internet", "path_to_profit", ["ZOMATO"]),
]

SPECIAL_ROWS: list[dict[str, Any]] = [
    _row(t, n, s, bucket="special_situation", profile=p, aliases=a) for t, n, s, p, a in SPECIAL_SEED
]


def all_rows() -> list[dict[str, Any]]:
    """Deduped Phase 1 universe in bucket order (N50 → Next50 → mid → small → special)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in NIFTY_50_ROWS + NIFTY_NEXT_50_ROWS + MIDCAP_ROWS + SMALLCAP_ROWS + SPECIAL_ROWS:
        t = row["ticker"]
        if t in seen:
            continue
        seen.add(t)
        # Also reserve aliases so ZOMATO/ETERNAL don't double-count if both appear later
        for alias in row.get("aliases") or []:
            seen.add(str(alias).upper())
        out.append(row)
    return out


PHASE1_GOLDEN_ROWS: list[dict[str, Any]] = all_rows()
PHASE1_GOLDEN_200: tuple[str, ...] = tuple(r["ticker"] for r in PHASE1_GOLDEN_ROWS)


def composition_fingerprint(tickers_seq: tuple[str, ...] | list[str] | None = None) -> str:
    """Stable SHA-256 over the ordered ticker list — freeze guard for v1.0."""
    seq = tuple(tickers_seq) if tickers_seq is not None else PHASE1_GOLDEN_200
    return hashlib.sha256("\n".join(seq).encode("utf-8")).hexdigest()


def tickers(*, bucket: str | None = None) -> tuple[str, ...]:
    if not bucket:
        return PHASE1_GOLDEN_200
    b = bucket.lower().strip()
    return tuple(r["ticker"] for r in PHASE1_GOLDEN_ROWS if r["bucket"] == b)


def by_bucket() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {b: [] for b in BUCKETS}
    for r in PHASE1_GOLDEN_ROWS:
        out.setdefault(r["bucket"], []).append(r)
    return out


def by_sector() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in PHASE1_GOLDEN_ROWS:
        out.setdefault(r["sector"], []).append(r["ticker"])
    return out


def lookup(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").upper().strip()
    for r in PHASE1_GOLDEN_ROWS:
        if r["ticker"] == t or t in {a.upper() for a in (r.get("aliases") or [])}:
            return dict(r)
    return None


def summary() -> dict[str, Any]:
    buckets = by_bucket()
    counts = {b: len(buckets.get(b) or []) for b in BUCKETS}
    sectors = by_sector()
    fp = composition_fingerprint()
    return {
        "version": PHASE1_VERSION,
        "golden_universe_version": GOLDEN_UNIVERSE_VERSION,
        "frozen": FROZEN,
        "composition_sha256": fp,
        "programme": "AGIB_PHASE1_GOLDEN_TEST_SET",
        "target_n": PHASE1_TARGET_N,
        "n": len(PHASE1_GOLDEN_ROWS),
        "meets_target": len(PHASE1_GOLDEN_ROWS) == PHASE1_TARGET_N,
        "bucket_counts": counts,
        "composition": {
            "nifty_50": 50,
            "nifty_next_50": 50,
            "midcaps": 50,
            "smallcaps": 25,
            "special_situations": 25,
        },
        "sector_count": len(sectors),
        "sectors": {k: len(v) for k, v in sorted(sectors.items())},
        "tickers": list(PHASE1_GOLDEN_200),
        "note": (
            f"Frozen benchmark {GOLDEN_UNIVERSE_VERSION} — do not silently edit composition. "
            "Ship an explicit v1.1 (new version + fingerprint) to change membership. "
            "Membership is not a claim of evidence completeness."
        ),
    }


def validate_universe() -> dict[str, Any]:
    """Structural integrity checks for the golden set."""
    rows = PHASE1_GOLDEN_ROWS
    tickers_list = [r["ticker"] for r in rows]
    dupes = sorted({t for t in tickers_list if tickers_list.count(t) > 1})
    buckets = by_bucket()
    expected = {
        "nifty_50": 50,
        "nifty_next_50": 50,
        "midcap": 50,
        "smallcap": 25,
        "special_situation": 25,
    }
    bucket_ok = {b: len(buckets.get(b) or []) == n for b, n in expected.items()}
    # No overlap across primary buckets
    sets = {b: {r["ticker"] for r in buckets.get(b) or []} for b in BUCKETS}
    overlaps: list[str] = []
    names = list(BUCKETS)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            hit = sorted(sets[a] & sets[b])
            if hit:
                overlaps.append(f"{a}∩{b}:{','.join(hit[:8])}")
    fp = composition_fingerprint()
    frozen_ok = (not FROZEN) or fp == FROZEN_COMPOSITION_SHA256
    return {
        "version": PHASE1_VERSION,
        "golden_universe_version": GOLDEN_UNIVERSE_VERSION,
        "frozen": FROZEN,
        "composition_sha256": fp,
        "frozen_composition_sha256": FROZEN_COMPOSITION_SHA256,
        "frozen_ok": frozen_ok,
        "n": len(rows),
        "unique": len(set(tickers_list)),
        "duplicates": dupes,
        "bucket_ok": bucket_ok,
        "overlaps": overlaps,
        "valid": (
            len(rows) == PHASE1_TARGET_N
            and not dupes
            and all(bucket_ok.values())
            and not overlaps
            and frozen_ok
        ),
        "immutability_note": (
            "Golden Universe v1.0 is frozen. Create Golden Universe v1.1 for composition changes."
        ),
    }
