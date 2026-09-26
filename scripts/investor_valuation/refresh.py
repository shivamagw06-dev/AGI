"""Nightly mark-to-market of disclosed equity quantities. Never changes filings."""
import concurrent.futures, hashlib, json, math, re, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
ROOT = Path(__file__).resolve().parents[2]

def fingerprint(profile):
    # Only valuation inputs matter; byte-stable serialization is shared with JS.
    inputs = [profile.get('reportPeriod'), [[r.get(k) for k in ('stock','quantity','security','cusip')] for r in profile['rows']]]
    return hashlib.sha256(json.dumps(inputs,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def number(value):
    try:
        n=float(str(value).replace(',',''))
        return n if math.isfinite(n) and n>0 else None
    except (ValueError,TypeError): return None

def period_date(profile):
    s=profile.get('reportPeriod') or ''
    for fmt in ('%Y-%m-%d','%d %b %Y','%b %Y','%B %Y'):
        try:
            dt=datetime.strptime(s,fmt).replace(tzinfo=timezone.utc)
            if fmt in ('%b %Y','%B %Y'):
                import calendar
                dt=dt.replace(day=calendar.monthrange(dt.year,dt.month)[1])
            return dt
        except ValueError: pass
    m=re.fullmatch(r'(?:Q([1-4]) (\d{4})|(\d{4}) Q([1-4]))',s)
    if m:
        import calendar
        year=int(m[2] or m[3]); month=int(m[1] or m[4])*3
        return datetime(year,month,calendar.monthrange(year,month)[1],tzinfo=timezone.utc)
    return None

def eligible(profile,row,mappings):
    if not number(row.get('quantity')): return None,'Quantity unavailable'
    if profile['country']=='IN' and (not row.get('history') or row['history'][0] in ('-',None,'')):
        return None,'Historical position; current ownership unavailable'
    if re.search(r'\b(PUT|CALL|PRN|PFD|PREF|NOTE|WARRANT|WTS|DEBT|CONVERTIBLE)\b',row.get('security',''),re.I):
        return None,'Security requires separate valuation'
    mapping=mappings['IN'].get(row['stock']) if profile['country']=='IN' else mappings['CUSIP'].get(row.get('cusip'))
    if not mapping and profile['country']=='US' and profile.get('kind')=='fund-disclosures':
        explicit=re.match(r'^([A-Z][A-Z0-9.\-]{0,9}) - ',row['stock'])
        if explicit: return explicit[1].replace('.','-'),None
    if not mapping: return None,'Exact security mapping unavailable'
    return mapping['symbol'],None

def fetch_quote(symbol):
    # No alternate hosts, proxy bypasses, or retries on provider rate limits.
    url='https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol,safe='')+'?range=1y&interval=1d&events=splits'
    proc=subprocess.run(['curl','--fail','--silent','--show-error','--max-time','25','--user-agent','AGI-Portfolio-Valuation/1.0 (+https://agarwalglobalinvestments.com)',url],capture_output=True,text=True)
    if proc.returncode: raise RuntimeError('Yahoo quote unavailable')
    data=json.loads(proc.stdout)['chart']['result'][0]
    meta=data['meta']; stamps=data.get('timestamp',[])
    closes=data['indicators']['quote'][0]['close']
    regular_time=meta.get('regularMarketTime',0)
    # Use the previous daily bar for a comparable regular-session price change.
    valid=[(ts,number(c)) for ts,c in zip(stamps,closes) if number(c)]
    previous=valid[-2][1] if len(valid)>1 else None
    return dict(symbol=meta.get('symbol'),currency=meta.get('currency'),price=number(meta.get('regularMarketPrice')),
                time=regular_time,previous=previous,type=meta.get('instrumentType'),
                splits=[int(s['date']) for s in data.get('events',{}).get('splits',{}).values()])

def value_profile(profile,mappings,quotes,now):
    source_date=period_date(profile)
    out=[]; total=0; previous_total=0; comparable=True; times=[]
    for row in profile['rows']:
        symbol,reason=eligible(profile,row,mappings)
        q=quotes.get(symbol)
        if not reason and (not source_date or not 0 <= (now-source_date).days <= 360): reason='Disclosure date needs review'
        if not reason and not q: reason='Price unavailable'
        if not reason and (q.get('symbol')!=symbol or q.get('currency')!=('INR' if profile['country']=='IN' else 'USD') or q.get('type') not in ('EQUITY','ETF')): reason='Quote identity or currency mismatch'
        if not reason and (not q.get('price') or not 0 <= now.timestamp()-q.get('time',0) <= 7*86400): reason='Price stale or invalid'
        if not reason and any(t>=source_date.timestamp() for t in q.get('splits',[])): reason='Stock split since disclosure; quantity needs review'
        if reason:
            out.append({'symbol':symbol,'reason':reason}); continue
        qty=number(row['quantity']); value=qty*q['price']; prev=qty*q['previous'] if q.get('previous') else None
        total+=value; times.append(q['time'])
        if prev is None: comparable=False
        else: previous_total+=prev
        out.append(dict(symbol=symbol,price=q['price'],value=round(value,2),priceAt=datetime.fromtimestamp(q['time'],timezone.utc).isoformat(),dayChangePct=round((q['price']/q['previous']-1)*100,4) if q.get('previous') else None))
    count=len(times)
    return dict(name=profile['name'],country=profile['country'],fingerprint=fingerprint(profile),reportPeriod=profile.get('reportPeriod'),
                pricedCount=count,rowCount=len(out),value=round(total,2) if count else None,
                dayChangePct=round((total/previous_total-1)*100,4) if count and comparable and previous_total else None,
                oldestPriceAt=datetime.fromtimestamp(min(times),timezone.utc).isoformat() if times else None,rows=out)

def run(output):
    now=datetime.now(timezone.utc)
    mappings=json.loads((ROOT/'src/data/investorProfiles/priceMappings.json').read_text())
    profiles=[json.loads(p.read_text()) for p in sorted((ROOT/'src/data/investorProfiles/holdings').glob('*.json'))]
    symbols=sorted({eligible(p,r,mappings)[0] for p in profiles for r in p['rows']} - {None})
    quotes={}; failures=0
    # Small bounded batches; abort on widespread provider errors and retain published file.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for offset in range(0,len(symbols),12):
            batch=symbols[offset:offset+12]
            for symbol,future in zip(batch,[pool.submit(fetch_quote,s) for s in batch]):
                try: quotes[symbol]=future.result()
                except (Exception,): failures+=1
            if failures>=6 and failures/(offset+len(batch))>.25:
                raise RuntimeError('Yahoo unavailable or rate limited; previous published valuations preserved')
            time.sleep(1)
    # Validate against collection completion: US quotes may advance during the run.
    now=datetime.now(timezone.utc)
    results={p['country'].lower()+'-'+p['slug']:value_profile(p,mappings,quotes,now) for p in profiles}
    if not any(p['pricedCount'] for p in results.values()): raise RuntimeError('No usable prices; refusing publication')
    data=dict(schemaVersion=1,updatedAt=now.isoformat(),provider='Yahoo Finance',schedule='Daily at 02:00 Asia/Kolkata',profiles=results)
    target=Path(output); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'profiles':len(results),'pricedRows':sum(p['pricedCount'] for p in results.values()),'symbols':len(quotes),'failedSymbols':failures}))
if __name__=='__main__':
    import sys
    run(sys.argv[1])
