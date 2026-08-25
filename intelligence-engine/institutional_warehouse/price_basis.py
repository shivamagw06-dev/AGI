"""What a price in `close` actually means, declared rather than inferred.

Three feeds write daily_market_history and they do not agree on the question.
Upstox supplies prices already restated for splits and bonuses. The NSE bhavcopy
and Yahoo both supply the price as it traded. All of them land in `close`, the
table keeps one row per symbol and day, and the last writer wins - so a series
could begin on one convention and finish on the other, and the ratio between its
two ends carried the split factor rather than the return.

Dr. Lal PathLabs split two-for-one and was published at -45.29% for a year it
finished up 9.4%.

The first fix was to compute a return within a single source, which works but
reads the convention off the writer's name. That is fragile in a way this file
exists to end: `source` is a property of the row, not of the field, so a partial
update rewrites it. The formula engine writes only `market_cap`, yet rows it has
touched are labelled `formula_engine` while their price came from somewhere else
entirely.

So the basis is stamped alongside the price by whoever supplies the price, and a
reader asks for a basis instead of guessing at one.
"""

from __future__ import annotations

from typing import Any, Optional

RAW = "RAW"
SPLIT_ADJUSTED = "SPLIT_ADJUSTED"
TOTAL_RETURN = "TOTAL_RETURN"
UNKNOWN = "UNKNOWN"

BASES = (RAW, SPLIT_ADJUSTED, TOTAL_RETURN, UNKNOWN)

# source -> (feed family, what its `close` column means)
#
# The feed family is the vendor behind the row rather than the writer in front
# of it. Upstox writes under two names - a deep backfill and a nightly top-up -
# and they share a convention, so grouping on the writer split them apart and
# left a symbol with a deep source that failed the freshness test and a fresh
# source with no history.
_SOURCES: dict[str, tuple[str, str]] = {
    "upstox_v3_historical": ("upstox", SPLIT_ADJUSTED),
    "upstox_v3_daily": ("upstox", SPLIT_ADJUSTED),
    "upstox": ("upstox", SPLIT_ADJUSTED),
    # The bhavcopy is the exchange's own end-of-day file: the price that traded,
    # never restated. It is also the only place a delisted company still exists.
    "nse_bhavcopy": ("nse", RAW),
    # Yahoo's chart API returns both. This reader takes indicators.quote.close,
    # which is unadjusted, and keeps indicators.adjclose in `adjusted_close`.
    # Yahoo's chart API returns both. This reader takes indicators.quote.close,
    # which is unadjusted, and keeps indicators.adjclose in `adjusted_close`.
    "yahoo_finance": ("yahoo", RAW),
    "yahoo_finance_history": ("yahoo", RAW),
    # Groww's LTP/OHLC is the split-adjusted last price the tape shows.
    "groww": ("groww", SPLIT_ADJUSTED),
    "knowledge_factory_hd": ("kf_hd", UNKNOWN),
}


# Declared by vendor, for the writers that are not named individually above.
#
# Writer names multiply: `upstox_v3_historical` is the backfill, `upstox_v3_daily`
# the nightly top-up, and `upstox_v3` a third that stamped 4,500 rows UNKNOWN
# before anyone noticed. What is being declared here is not a name but a vendor -
# every Upstox v3 candle comes back restated for splits, whichever of our writers
# asked for it.
#
# Anything matching no prefix stays UNKNOWN. This widens what is recognised; it
# does not guess.
_VENDOR_PREFIXES: tuple[tuple[str, str, str], ...] = (
    ("upstox_v3", "upstox", SPLIT_ADJUSTED),
    ("upstox", "upstox", SPLIT_ADJUSTED),
    ("yahoo", "yahoo", RAW),
    ("nse_bhavcopy", "nse", RAW),
    ("groww", "groww", SPLIT_ADJUSTED),
)


def describe(source: Any) -> tuple[str, str]:
    """(feed family, basis) for a source name.

    An unrecognised source is UNKNOWN rather than assumed. A wrong basis is
    worse than an absent one: it lets a reader pair two prices that do not
    belong together while believing it checked.
    """
    key = str(source or "").strip().lower()
    if key in _SOURCES:
        return _SOURCES[key]
    for prefix, family, basis in _VENDOR_PREFIXES:
        if key.startswith(prefix):
            return (family, basis)
    return (key or "unknown", UNKNOWN)


def stamp(rows: Any, *, source: Any) -> list[dict[str, Any]]:
    """Tag rows that carry a price with the basis that price is on.

    Rows without a `close` are left alone. The formula engine updates
    `market_cap` on existing rows and supplies no price; stamping those would
    relabel somebody else's number with the basis of a writer that never
    touched it.
    """
    family, basis = describe(source)
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if row.get("close") is not None:
            row = {**row, "price_basis": basis, "feed_family": family}
        out.append(row)
    return out


def comparable(a: Any, b: Any) -> bool:
    """Whether two prices may be divided by one another.

    Same basis, and a known one. Two UNKNOWN prices are not comparable just
    because their labels match - neither has been established, so agreement
    between them means nothing.
    """
    left, right = str(a or UNKNOWN).upper(), str(b or UNKNOWN).upper()
    if left == UNKNOWN or right == UNKNOWN:
        return False
    return left == right


def known_sources() -> tuple[str, ...]:
    return tuple(sorted(_SOURCES))


# How many rows one stamping pass touches.
#
# Deliberately small. The engine and its background worker share one SQLite
# file, and a single UPDATE across 7.1m rows holds a write lock for as long as
# it runs - which is the 19 August incident, where in-process work held locks
# and the engine served 12-second timeouts for hours. Many short writes are
# slower in total and never block a request for long.
STAMP_BATCH = 20_000


def backfill_stamps(*, batches: int = 1, batch_size: int = STAMP_BATCH,
                    restamp_unknown: bool = False) -> dict[str, Any]:
    """Fill price_basis and feed_family on rows written before they existed.

    The reader already falls back to the same declaration for an unstamped row,
    so this changes no answer. It removes the fallback's reason to exist, and
    makes a row's meaning legible without knowing which table to consult.

    ``restamp_unknown`` also revisits rows stamped UNKNOWN by an earlier pass,
    for the case the declaration has since learned their writer - `upstox_v3`
    labelled 4,500 rows UNKNOWN before it was recognised. It is a separate pass
    rather than a widened filter: mixed into the same scan, one block of rows
    that genuinely cannot be resolved stalls the whole loop, which is exactly
    what the first attempt did.
    """
    from institutional_warehouse import db

    db.init()
    table = db.physical_table("daily_market_history")
    corrected = 0

    if restamp_unknown:
        # Small and set-based: only the sources the declaration now recognises,
        # updated by source rather than row by row.
        stale = db.query(
            f"SELECT DISTINCT source FROM {table} WHERE price_basis = 'UNKNOWN'"
        ) or []
        for row in stale:
            source = row.get("source")
            family, basis = describe(source)
            if basis == UNKNOWN:
                continue  # still genuinely unknown; leave it rather than churn it
            corrected += db.execute(
                f"UPDATE {table} SET price_basis = ?, feed_family = ?"
                f" WHERE price_basis = 'UNKNOWN' AND source IS ?",
                (basis, family, source),
            ) or 0

    stamped = 0
    passes = 0
    for _ in range(max(1, int(batches))):
        rows = db.query(
            f"SELECT row_id, source FROM {table}"
            f" WHERE price_basis IS NULL AND close IS NOT NULL LIMIT ?",
            (int(batch_size),),
        ) or []
        if not rows:
            break
        by_source: dict[str, list[str]] = {}
        for row in rows:
            by_source.setdefault(str(row.get("source") or ""), []).append(str(row["row_id"]))
        for source, ids in by_source.items():
            family, basis = describe(source)
            for start_at in range(0, len(ids), 500):
                chunk = ids[start_at:start_at + 500]
                marks = ", ".join("?" for _ in chunk)
                db.execute(
                    f"UPDATE {table} SET price_basis = ?, feed_family = ?"
                    f" WHERE row_id IN ({marks})",
                    (basis, family, *chunk),
                )
        stamped += len(rows)
        passes += 1

    remaining = db.query(
        f"SELECT COUNT(*) AS n FROM {table} WHERE price_basis IS NULL AND close IS NOT NULL"
    )
    left = int((remaining[0] if remaining else {}).get("n") or 0)
    return {"ok": True, "stamped": stamped, "corrected": corrected, "passes": passes,
            "remaining": left, "complete": left == 0}
