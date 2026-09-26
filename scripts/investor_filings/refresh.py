"""Daily original NSE SHP scan. Never infer sales from absent disclosures.

Publishes a separate, attributed exact-name view; imported/group portfolios are
not overwritten. Only the current filing for an issuer is eligible for display.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import time
import sys
import gzip
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'intelligence-engine'))
from financial_warehouse_completion.shareholding_xml import parse, metadata
from financial_warehouse_completion.investor_mapping import build_profiles, seeds

INDEX = 'https://www.nseindia.com/api/corporate-share-holdings-master?index=equities'
FEED = 'https://raw.githubusercontent.com/shivamagw06-dev/AGI/investor-valuation-data/investor-filings/latest.json'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; AGIB-LIDI/1.0)', 'Referer': 'https://www.nseindia.com/', 'Accept': 'application/json,application/xml,text/xml,*/*'}

def get(url):
    with urlopen(Request(url, headers=HEADERS), timeout=25) as response:
        if urlparse(response.url).hostname != urlparse(url).hostname:
            raise ValueError('Unexpected source redirect')
        raw = response.read(12_000_001)
        if len(raw) > 12_000_000: raise ValueError('Source exceeds size limit')
        return raw

def normalized(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def day(value):
    return datetime.strptime(value[:11], '%d-%b-%Y').date().isoformat()


def targets():
    return [r for r in json.loads((ROOT / 'src/data/investorProfiles/index.json').read_text()) if r['country'] == 'IN']

def latest_filings(rows):
    latest = {}
    for row in rows:
        try:
            period = day(row['date']); symbol = row['symbol']; url = row['xbrl']
            if not symbol or urlparse(url).hostname != 'nsearchives.nseindia.com' or not url.startswith('https://'): continue
            filing = {'symbol': symbol, 'stock': row['name'], 'period': period, 'url': url, 'submitted': row.get('broadcastDate') or row.get('submissionDate'), 'revision': row.get('revisedData') == 'Y', 'isin':row.get('isin'), 'exchange':'NSE'}
            # A later submission in the same quarter supersedes an earlier one.
            stamp = datetime.strptime((filing['submitted'] or '')[:20], '%d-%b-%Y %H:%M:%S') if len(filing['submitted'] or '') >= 20 else datetime.strptime(filing['submitted'], '%d-%b-%Y')
            filing['submittedISO'] = stamp.isoformat()
            rank = (period, stamp)
            if symbol not in latest or rank > latest[symbol][0]: latest[symbol] = (rank, filing)
        except (KeyError, ValueError, TypeError): continue
    return [v[1] for v in latest.values()]

def refresh(previous, index, limit, mappings=None, bse_filings=None, bse_status=None):
    people = targets(); names = {normalized(p['name']) for p in people}
    # Generic group titles are never stripped or guessed to generate aliases.
    old = previous.get('filings', {})
    filings = latest_filings(index)
    if len(filings) < 100: raise ValueError('Incomplete exchange index; preserve previous feed')
    pending = [f for f in filings if old.get(f['symbol'], {}).get('url') != f['url'] or old.get(f['symbol'], {}).get('status') != 'ok' or old.get(f['symbol'], {}).get('cacheVersion') != 2]
    pending.sort(key=lambda f: (old.get(f['symbol'], {}).get('attemptedAt', ''), f['symbol']))
    output = {f['symbol']: old[f['symbol']] for f in filings if old.get(f['symbol'], {}).get('url') == f['url'] }
    def collect(filing):
        try:
            raw = get(filing['url']); info=metadata(raw)
            if info['symbol'] and info['symbol'] != filing['symbol']: raise ValueError('Issuer symbol mismatch')
            if filing.get('isin') and info['isin'] != filing['isin']: raise ValueError('Issuer ISIN mismatch')
            rows = parse(raw, filing['period'])
            return {**filing, **info, 'cacheVersion':2, 'attemptedAt': datetime.now(timezone.utc).isoformat(), 'status': 'ok', 'rows': rows}
        except Exception as exc:
            return {**filing, 'attemptedAt': datetime.now(timezone.utc).isoformat(), 'status': 'unavailable', 'rows': [], 'error': type(exc).__name__}
        finally: time.sleep(.25)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(collect, pending[:limit]): output[result['symbol']] = result
    # Retain last good records when a replacement document cannot be parsed;
    # their original reporting dates and stale flag remain explicit.
    for symbol, previous_filing in old.items():
        if previous_filing.get('status')=='ok' and (symbol not in output or output[symbol].get('status')!='ok'):
            previous_copy={**previous_filing,'stale':True}
            if symbol in output: previous_copy['refreshError']=output[symbol].get('error')
            output[symbol]=previous_copy
    all_filings = list(output.values()) + list(bse_filings or [])
    profiles, candidates = build_profiles(people, all_filings, mappings if mappings is not None else seeds())
    success = sum(output.get(f['symbol'],{}).get('status')=='ok' and output.get(f['symbol'],{}).get('url')==f['url'] and output.get(f['symbol'],{}).get('cacheVersion')==2 and not output.get(f['symbol'],{}).get('stale') for f in filings)
    return {'schemaVersion': 1, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'source': 'NSE original shareholding filings', 'issuerCount': len(filings), 'checkedCount': success, 'pendingCount': len(filings) - success, 'profiles': profiles, 'filings': output, 'reviewCandidates':candidates, 'mappingCount':len(mappings if mappings is not None else seeds()), 'bseStatus':bse_status or {'state':'not_configured','message':'BSE automatic feed is not connected.'}, 'bseFilings':list(bse_filings or [])}

def main():
    args = argparse.ArgumentParser(); args.add_argument('output'); args.add_argument('--limit', type=int, default=250); args = args.parse_args()
    try:
        previous = json.loads(get(FEED))
        if previous.get('cacheUrl'):
            cache_url=previous['cacheUrl']
            if not re.fullmatch(r'https://raw.githubusercontent.com/shivamagw06-dev/AGI/[a-f0-9]{40}/investor-filings/cache.json.gz',cache_url): raise ValueError('Invalid cache reference')
            with gzip.GzipFile(fileobj=__import__('io').BytesIO(get(cache_url))) as stream:
                cache=stream.read(60_000_001)
            if len(cache)>60_000_000: raise ValueError('Cache exceeds size limit')
            previous['filings']=json.loads(cache)
    except Exception:
        # A failed state read must not replace the established cache with a partial scan.
        raise RuntimeError('Cannot read prior filing state; initialize explicitly before scheduling')
    registry=json.loads(get('https://finance-news-backend-19i5.onrender.com/api/intelligence/investor-mappings/approved'))
    if not registry.get('ok'): raise RuntimeError('Mapping registry unavailable; previous data preserved')
    from bse import collect_bse
    bse_filings,bse_status=collect_bse(registry.get('bseFilings',[]),previous.get('bseFilings',[]),get,parse,metadata)
    result = refresh(previous, json.loads(get(INDEX)), args.limit, registry['mappings'],bse_filings,bse_status)
    p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(result, ensure_ascii=False))
    print(json.dumps({k:result[k] for k in ('issuerCount','checkedCount','pendingCount')}))

if __name__ == '__main__': main()
