"""Register only observations visible on the public site; preserve their first-seen dates.
No backdating to the ownership quarter or guessed trade executions.
"""
import base64,copy,hashlib,json,math,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
REPO='shivamagw06-dev/AGI';BRANCH='institution-research-data';FILE='institution-research/performance.json'
PUBLIC='https://agarwalglobalinvestments.com/data/institution-briefs.json'

def update(previous,briefs,quotes,now):
    out=copy.deepcopy(previous or {'schemaVersion':1,'observations':{}})
    if out.get('schemaVersion')!=1 or not isinstance(out.get('observations'),dict): raise ValueError('Invalid previous ledger; do not reset')
    for o in briefs['observations']:
        digest=hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        item=out['observations'].setdefault(o['id'],dict(firstPublishedAt=now.isoformat(),contentHash=digest,symbol=o['symbol'],benchmark=o['benchmark'],country=o['country'],baselineDate=None,series=[]))
        if item['contentHash']!=digest:
            item['status']='Observation changed; requires new version ID';continue
        # Registration-only runs must not mark a previously successful price collection as failed.
        if not quotes:
            if not item.get('series'):item['status']='Awaiting next completed common session'
            continue
        # Each bar must be a completed local trading session. Both series use identical dates.
        q,b=quotes.get(o['symbol'],{}),quotes.get(o['benchmark'],{})
        if q.get('symbol')!=o['symbol'] or b.get('symbol')!=o['benchmark'] or q.get('currency')!=o['currency'] or b.get('currency')!=o['currency']:
            item['status']='Price or benchmark identity unavailable';continue
        from zoneinfo import ZoneInfo
        zone=ZoneInfo('Asia/Kolkata' if o['country']=='IN' else 'America/New_York')
        today=now.astimezone(zone).date().isoformat()
        registered=datetime.fromisoformat(item['firstPublishedAt']).astimezone(zone).date().isoformat()
        def valid_history(x):
            return {p['date']:p['adjustedClose'] for p in x.get('history',[]) if p.get('date','')<today and p.get('date','')>registered and isinstance(p.get('adjustedClose'),(int,float)) and math.isfinite(p['adjustedClose']) and p['adjustedClose']>0}
        stock,benchmark=valid_history(q),valid_history(b)
        dates=sorted(stock.keys()&benchmark.keys())
        if not item['baselineDate'] and dates:item['baselineDate']=dates[0]
        baseline=item['baselineDate']
        if not baseline or baseline not in dates:
            item['status']='Awaiting completed common sessions; previous results retained';continue
        series=[]
        for date in dates:
            if date<baseline:continue
            sr=(stock[date]/stock[baseline]-1)*100;br=(benchmark[date]/benchmark[baseline]-1)*100
            series.append(dict(date=date,stockReturn=round(sr,6),benchmarkReturn=round(br,6),excessPp=round(sr-br,6)))
        # A provider gap cannot erase a previously recorded trading session.
        merged={p['date']:p for p in item['series']};merged.update({p['date']:p for p in series})
        item['series']=[merged[d] for d in sorted(merged)]
        item['status']='Tracking adjusted closes';item['lastPriceDate']=dates[-1]
    out['updatedAt']=now.isoformat();out['methodology']='First observed on public AGI page; baseline is the first completed common session strictly after registration. Adjusted close returns; no trade fills, fees, taxes, short P&L or manager performance.'
    return out

def api(path,method='GET',data=None,missing_ok=False):
    args=['gh','api',f'repos/{REPO}/{path}','--method',method]
    if data is not None:args+=['--input','-']
    r=subprocess.run(args,input=json.dumps(data) if data is not None else None,capture_output=True,text=True)
    if r.returncode:
        if missing_ok and 'HTTP 404' in r.stderr:return None
        raise RuntimeError('Ledger publication failed; existing data preserved')
    return json.loads(r.stdout) if r.stdout else None

def run(quote_path):
    with urlopen(Request(PUBLIC,headers={'User-Agent':'AGI-Ownership-Research/1.0'}),timeout=20) as r:public=json.load(r)
    local=json.loads((Path(__file__).resolve().parents[2]/'public/data/institution-briefs.json').read_text())
    if public!=local:raise ValueError('Public observation version does not match checkout; no registration')
    old=api(f'contents/{FILE}?ref={BRANCH}',missing_ok=True)
    previous=json.loads(base64.b64decode(old['content'])) if old else None
    quotes=json.loads(Path(quote_path).read_text())
    data=update(previous,public,quotes,datetime.now(timezone.utc))
    if api(f'git/ref/heads/{BRANCH}',missing_ok=True) is None:
        head=api('git/ref/heads/main');api('git/refs','POST',{'ref':f'refs/heads/{BRANCH}','sha':head['object']['sha']})
    body=dict(message='Record public ownership research outcomes without backdating',branch=BRANCH,content=base64.b64encode(json.dumps(data,separators=(',',':')).encode()).decode())
    if old:body['sha']=old['sha']
    api(f'contents/{FILE}','PUT',body)
    print('Registered public observations and retained chronological outcomes:',len(data['observations']))
if __name__=='__main__':run(sys.argv[1])
