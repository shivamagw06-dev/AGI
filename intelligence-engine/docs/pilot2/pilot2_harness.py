"""Second bounded pilot: corrected date parsing, FY26/FY27 only, 250-request cap."""
import sys, json, os, time, hashlib, collections, datetime
from datetime import timezone
SP = "/private/tmp/claude-501/-Users-shivamagarwal-Downloads-spaceanalytix/c24f664e-aa91-48a6-af6a-a3b7519affc6/scratchpad/"
sys.path.insert(0, SP); sys.path.insert(0, ".")
import pilot
from institutional_warehouse import xbrl_shadow as sh
from earnings_intelligence.xbrl import INCOME_MAP, BALANCE_MAP, CASHFLOW_MAP
from live_data.collectors.base import nse_session_opener

MAPPED = set(INCOME_MAP) | set(BALANCE_MAP) | set(CASHFLOW_MAP)
UNIV = json.load(open(SP + "pilot_universe.json"))
SYMBOLS = UNIV["symbols"]
REQUEST_BUDGET = 250
MAX_PER_SYMBOL = 4

# FY26 = Apr 2025..Mar 2026, FY27 = Apr 2026..Mar 2027. Nothing older is taken,
# even when a company has no filing in range - the point is to test these
# periods, not to fill the quota with whatever exists.
FY_START = datetime.date(2025, 4, 1)
FY_END   = datetime.date(2027, 3, 31)

DISCOVERY = ("https://www.nseindia.com/api/corporates-financial-results"
             "?index=equities&period={period}&symbol={symbol}")


def _date(text):
    for fmt in ("%d-%b-%Y",):
        try:
            return datetime.datetime.strptime(str(text)[:11].strip(), fmt).date()
        except Exception:
            pass
    return None


op = nse_session_opener()
records, seen_urls, seen_hashes = [], set(), set()
outcomes = collections.Counter(); dupes = collections.Counter()
per_symbol = {}; no_target_filing = []; stopped = None
t0 = time.time()

for i, symbol in enumerate(SYMBOLS, 1):
    if pilot.state["requests"] >= REQUEST_BUDGET:
        stopped = f"request budget {REQUEST_BUDGET} reached at symbol {i}/{len(SYMBOLS)}"
        break
    try:
        filings = []
        for period in ("Quarterly", "Annual"):
            body = pilot.fetch(DISCOVERY.format(period=period, symbol=symbol), op)
            data = json.loads(body.decode("utf-8"))
            if isinstance(data, list):
                filings += [f for f in data if f.get("xbrl")]

        in_range = []
        for f in filings:
            end = _date(f.get("toDate"))
            if end and FY_START <= end <= FY_END:
                in_range.append((_date(f.get("filingDate")) or datetime.date.min, f))
        if not in_range:
            no_target_filing.append(symbol); per_symbol[symbol] = 0
            continue
        in_range.sort(key=lambda pair: pair[0], reverse=True)

        taken = 0
        for _filed, f in in_range:
            if taken >= MAX_PER_SYMBOL: break
            if pilot.state["requests"] >= REQUEST_BUDGET:
                stopped = f"request budget {REQUEST_BUDGET} reached"; break
            url = str(f.get("xbrl"))
            if url in seen_urls:
                dupes["by_url"] += 1; continue
            seen_urls.add(url)
            raw = pilot.fetch(url, op, binary=True)
            digest = hashlib.sha256(raw).hexdigest()
            if digest in seen_hashes:
                dupes["by_content_hash"] += 1; continue
            seen_hashes.add(digest)

            scan = sh.scan_document(raw.decode("utf-8", "replace"), filing_url=url,
                                    provider="nse_india", company=symbol)
            mapped = [x for x in scan["facts"] if x["concept"] in MAPPED]
            c = collections.Counter(x["outcome"] for x in mapped)
            outcomes.update(c)
            records.append({
                "symbol": symbol, "filing_url": url,
                "retrieved_at_utc": datetime.datetime.now(timezone.utc).isoformat(),
                "content_sha256": digest, "bytes": len(raw),
                "from_date": f.get("fromDate"), "to_date": f.get("toDate"),
                "filing_date": f.get("filingDate"),
                "financial_year": f.get("financialYear"),
                "filing_type": f.get("format") or f.get("audited"),
                "consolidated": f.get("consolidated"),
                "inline_xbrl": scan["inline"],
                "declared_units": sorted({u["kind"] for u in scan["units"].values()}),
                "mapped_facts": len(mapped), "outcomes": dict(c),
            })
            taken += 1
        per_symbol[symbol] = taken
        if stopped: break
        if i % 10 == 0:
            print(f"[{i}/{len(SYMBOLS)}] reqs={pilot.state['requests']} "
                  f"cache={pilot.state['cache_hits']} filings={len(records)} "
                  f"{time.time()-t0:.0f}s", flush=True)
    except pilot.Throttled as exc:
        stopped = f"NSE throttled/blocked: {exc}"; break
    except Exception as exc:
        outcomes[f"error:{type(exc).__name__}"] += 1
        continue

summary = {
  "run": "pilot_2_fy26_fy27",
  "generated_at_utc": datetime.datetime.now(timezone.utc).isoformat(),
  "applied": False, "warehouse_writes": 0, "conversions": 0,
  "period_window": {"from": str(FY_START), "to": str(FY_END),
                    "note": "FY26 and FY27 only; older periods never substituted"},
  "symbols_considered": len(per_symbol),
  "symbols_with_a_target_filing": sum(1 for v in per_symbol.values() if v),
  "symbols_without_a_target_filing": len(no_target_filing),
  "no_target_filing": no_target_filing,
  "filings_fetched": len(records),
  "requests_made": pilot.state["requests"], "request_budget": REQUEST_BUDGET,
  "cache_hits": pilot.state["cache_hits"],
  "retries": pilot.state["retries"], "retry_detail": pilot.state["retry_detail"],
  "failures": pilot.state["failures"],
  "min_interval_seconds": pilot.MIN_INTERVAL, "concurrency": 1,
  "duplicates_skipped": dict(dupes),
  "mapped_outcomes": dict(outcomes),
  "stopped_early": stopped,
  "elapsed_seconds": round(time.time()-t0, 1),
}
json.dump(summary, open(SP+"pilot2_summary.json","w"), indent=2)
json.dump(records, open(SP+"pilot2_records.json","w"), indent=1)
print("\n=== PILOT 2 SUMMARY ==="); print(json.dumps(
  {k:v for k,v in summary.items() if k not in ("no_target_filing","retry_detail")}, indent=1))
