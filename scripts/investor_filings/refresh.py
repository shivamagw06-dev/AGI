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
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
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

def local(tag):
    return tag.rsplit('}', 1)[-1]

def parse(raw, period):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('External declarations unsupported')
    root = ET.fromstring(raw)
    # Join duration/name and instant/quantity contexts by their dimensions,
    # not by context-id spelling; this also prevents mixing different dates.
    contexts, facts = {}, {}
    for item in root:
        if local(item.tag) == 'context':
            dims = tuple(sorted((e.get('dimension', ''), ''.join(e.itertext()).strip()) for e in item.iter() if local(e.tag) in ('typedMember', 'explicitMember')))
            dates = [e.text for e in item.iter() if local(e.tag) in ('instant', 'endDate')]
            contexts[item.get('id')] = (dims, dates[0] if len(dates) == 1 else None)
        elif item.get('contextRef'):
            key = (item.get('contextRef'), local(item.tag))
            value = (item.text or '').strip()
            if key in facts and facts[key] != value: raise ValueError('Conflicting XBRL facts')
            facts[key] = value
    quantities = {}
    for (ctx, tag), value in facts.items():
        if tag != 'NumberOfShares' or ctx not in contexts: continue
        dims, date = contexts[ctx]
        if not dims or date != period: continue
        qty = Decimal(value)
        if not qty.is_finite() or qty < 0 or qty != int(qty): raise ValueError('Invalid share count')
        pct = facts.get((ctx, 'ShareholdingAsAPercentageOfTotalNumberOfShares'))
        pct = Decimal(pct) * 100 if pct else None
        if pct is not None and (not pct.is_finite() or not 0 <= pct <= 100): raise ValueError('Invalid ownership')
        record = {'quantity': int(qty), 'ownershipPct': float(pct) if pct is not None else None}
        if dims in quantities and quantities[dims] != record: raise ValueError('Ambiguous shareholder dimensions')
        quantities[dims] = record
    result = []
    for (ctx, tag), name in facts.items():
        if tag != 'NameOfTheShareholder' or ctx not in contexts: continue
        dims, date = contexts[ctx]
        if date != period or dims not in quantities or not name: continue
        if facts.get((ctx, 'WhetherACategoryOrMoreThan1PercentageOfShareholding'), '').lower() == 'category': continue
        result.append({'holder': name, **quantities[dims]})
    if not result: raise ValueError('No named shareholder facts for filing period')
    return result

def targets():
    return [r for r in json.loads((ROOT / 'src/data/investorProfiles/index.json').read_text()) if r['country'] == 'IN']

def latest_filings(rows):
    latest = {}
    for row in rows:
        try:
            period = day(row['date']); symbol = row['symbol']; url = row['xbrl']
            if not symbol or urlparse(url).hostname != 'nsearchives.nseindia.com' or not url.startswith('https://'): continue
            filing = {'symbol': symbol, 'stock': row['name'], 'period': period, 'url': url, 'submitted': row.get('broadcastDate') or row.get('submissionDate'), 'revision': row.get('revisedData') == 'Y'}
            # A later submission in the same quarter supersedes an earlier one.
            stamp = datetime.strptime((filing['submitted'] or '')[:20], '%d-%b-%Y %H:%M:%S') if len(filing['submitted'] or '') >= 20 else datetime.strptime(filing['submitted'], '%d-%b-%Y')
            rank = (period, stamp)
            if symbol not in latest or rank > latest[symbol][0]: latest[symbol] = (rank, filing)
        except (KeyError, ValueError, TypeError): continue
    return [v[1] for v in latest.values()]

def refresh(previous, index, limit):
    people = targets(); names = {normalized(p['name']) for p in people}
    # Generic group titles are never stripped or guessed to generate aliases.
    old = previous.get('filings', {})
    filings = latest_filings(index)
    if len(filings) < 100: raise ValueError('Incomplete exchange index; preserve previous feed')
    pending = [f for f in filings if old.get(f['symbol'], {}).get('url') != f['url'] or old.get(f['symbol'], {}).get('status') != 'ok']
    pending.sort(key=lambda f: (old.get(f['symbol'], {}).get('attemptedAt', ''), f['symbol']))
    output = {f['symbol']: old[f['symbol']] for f in filings if old.get(f['symbol'], {}).get('url') == f['url'] }
    def collect(filing):
        try:
            rows = parse(get(filing['url']), filing['period'])
            return {**filing, 'attemptedAt': datetime.now(timezone.utc).isoformat(), 'status': 'ok', 'rows': [r for r in rows if normalized(r['holder']) in names]}
        except Exception as exc:
            return {**filing, 'attemptedAt': datetime.now(timezone.utc).isoformat(), 'status': 'unavailable', 'rows': [], 'error': type(exc).__name__}
        finally: time.sleep(.25)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(collect, pending[:limit]): output[result['symbol']] = result
    profiles = {}
    for person in people:
        rows = []
        for filing in output.values():
            if filing['status'] != 'ok': continue
            matches = [r for r in filing['rows'] if normalized(r['holder']) == normalized(person['name'])]
            # Duplicate named contexts need review, never sum them blindly.
            if len(matches) == 1:
                rows.append({**matches[0], **{k: filing[k] for k in ('symbol', 'stock', 'period', 'url', 'submitted')}})
        profiles['in-' + person['slug']] = {'name': person['name'], 'rows': sorted(rows, key=lambda r: (r['period'], r['stock']), reverse=True)}
    success = sum(f['status'] == 'ok' for f in output.values())
    return {'schemaVersion': 1, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'source': 'NSE original shareholding filings', 'issuerCount': len(filings), 'checkedCount': success, 'pendingCount': len(filings) - success, 'profiles': profiles, 'filings': output}

def main():
    args = argparse.ArgumentParser(); args.add_argument('output'); args.add_argument('--limit', type=int, default=250); args = args.parse_args()
    try: previous = json.loads(get(FEED))
    except Exception:
        # A failed state read must not replace the established cache with a partial scan.
        raise RuntimeError('Cannot read prior filing state; initialize explicitly before scheduling')
    result = refresh(previous, json.loads(get(INDEX)), args.limit)
    p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(result, ensure_ascii=False))
    print(json.dumps({k:result[k] for k in ('issuerCount','checkedCount','pendingCount')}))

if __name__ == '__main__': main()
