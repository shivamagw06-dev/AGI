import sys, json, os, time, hashlib, collections
from datetime import datetime, timezone
SP = "/private/tmp/claude-501/-Users-shivamagarwal-Downloads-spaceanalytix/c24f664e-aa91-48a6-af6a-a3b7519affc6/scratchpad/"
sys.path.insert(0, SP); sys.path.insert(0, ".")
import pilot
from institutional_warehouse import xbrl_shadow as sh
from earnings_intelligence.xbrl import INCOME_MAP, BALANCE_MAP, CASHFLOW_MAP
from live_data.collectors.base import nse_session_opener

MAPPED = set(INCOME_MAP) | set(BALANCE_MAP) | set(CASHFLOW_MAP)
UNIV = json.load(open(SP + "pilot_universe.json"))
SYMBOLS = UNIV["symbols"]
MAX_FILINGS_PER_SYMBOL = 3
REQUEST_BUDGET = 650

DISCOVERY = ("https://www.nseindia.com/api/corporates-financial-results"
             "?index=equities&period={period}&symbol={symbol}")

op = nse_session_opener()
records, by_symbol, seen_urls, seen_hashes = [], {}, set(), set()
outcomes = collections.Counter(); dupes = collections.Counter()
stopped = None
t0 = time.time()

for i, symbol in enumerate(SYMBOLS, 1):
    if pilot.state["requests"] >= REQUEST_BUDGET:
        stopped = f"request budget {REQUEST_BUDGET} reached"; break
    try:
        filings = []
        for period in ("Quarterly", "Annual"):
            body = pilot.fetch(DISCOVERY.format(period=period, symbol=symbol), op)
            data = json.loads(body.decode("utf-8"))
            if isinstance(data, list):
                filings += [f for f in data if f.get("xbrl")]
        # filingDate is "31-May-2020 09:45". Sorting it as text ranks by
        # day-of-month, so "most recent" silently became "highest day number".
        def _filed(f):
            import datetime
            try:
                return datetime.datetime.strptime(str(f.get("filingDate"))[:11], "%d-%b-%Y")
            except Exception:
                return datetime.datetime.min
        filings.sort(key=_filed, reverse=True)

        taken = 0
        for f in filings:
            if taken >= MAX_FILINGS_PER_SYMBOL: break
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
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "content_sha256": digest, "bytes": len(raw),
                "period": f.get("fromDate") and f"{f.get('fromDate')}..{f.get('toDate')}",
                "financial_year": f.get("financialYear"),
                "filing_date": f.get("filingDate"),
                "filing_type": f.get("format") or f.get("audited"),
                "consolidated": f.get("consolidated"),
                "inline_xbrl": scan["inline"],
                "declared_units": sorted({u["kind"] for u in scan["units"].values()}),
                "mapped_facts": len(mapped),
                "outcomes": dict(c),
            })
            taken += 1
        by_symbol[symbol] = taken
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
  "generated_at_utc": datetime.now(timezone.utc).isoformat(),
  "applied": False, "warehouse_writes": 0,
  "symbols_requested": len(SYMBOLS), "symbols_completed": len(by_symbol),
  "filings_fetched": len(records),
  "requests_made": pilot.state["requests"], "cache_hits": pilot.state["cache_hits"],
  "retries": pilot.state["retries"],
  "min_interval_seconds": pilot.MIN_INTERVAL, "concurrency": 1,
  "duplicates_skipped": dict(dupes),
  "mapped_outcomes": dict(outcomes),
  "stopped_early": stopped,
  "elapsed_seconds": round(time.time()-t0, 1),
}
json.dump(summary, open(SP+"pilot_summary.json","w"), indent=2)
json.dump(records, open(SP+"pilot_records.json","w"), indent=1)
print("\n=== PILOT SUMMARY ==="); print(json.dumps(summary, indent=1))
