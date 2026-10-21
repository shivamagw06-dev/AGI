"""Fetch reviewed Yahoo daily histories. Run manually; does not change allocations.
Uses curl with normal certificate verification. Cache raw responses outside repo.
"""
import math,argparse,datetime as dt,json,pathlib,subprocess,time,concurrent.futures,urllib.parse
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache',default='/private/tmp/agi-portfolio-history/raw');ap.add_argument('--cutoff',default=(dt.datetime.now(ZoneInfo('America/New_York')).date()-dt.timedelta(days=1)).isoformat());ap.add_argument('--refresh',action='store_true');args=ap.parse_args()
 cutoff=dt.date.fromisoformat(args.cutoff);start=cutoff-dt.timedelta(days=405)
 mapping=json.loads((ROOT/'scripts/portfolio-history/instruments.json').read_text());research=json.loads((ROOT/'src/data/portfolioResearch.json').read_text())
 symbols=sorted({v['symbol'] for v in mapping.values() if v.get('symbol')}|{s.replace('BRK.B','BRK-B') for s in research['securities']}|{'SPY'})
 cache=pathlib.Path(args.cache)/args.cutoff;cache.mkdir(parents=True,exist_ok=True)
 def fetch(symbol):
  path=cache/(symbol+'.json');source='https://finance.yahoo.com/quote/'+urllib.parse.quote(symbol,safe='')+'/history/'
  out={'source':source,'status':'unavailable'}
  try:
   if not path.exists() or args.refresh:
    query=urllib.parse.urlencode({'interval':'1d','period1':int(dt.datetime.combine(start,dt.time(),dt.timezone.utc).timestamp()),'period2':int(dt.datetime.combine(cutoff+dt.timedelta(days=1),dt.time(),dt.timezone.utc).timestamp()),'events':'div,splits','includeAdjustedClose':'true'})
    url='https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(symbol,safe='')+'?'+query
    for attempt in range(3):
     result=subprocess.run(['curl','-f','-sS','--max-time','25','-A','Mozilla/5.0',url],capture_output=True,text=True)
     if result.returncode==0:
      payload=json.loads(result.stdout)
      if payload.get('chart',{}).get('result'):path.write_text(result.stdout);break
     if attempt<2:time.sleep(2**(attempt+1))
    else:raise ValueError('Provider request failed after bounded retries')
   d=json.loads(path.read_text())['chart']['result'][0];m=d['meta'];q=d['indicators']['quote'][0];adj=d['indicators'].get('adjclose',[{}])[0].get('adjclose',[])
   if m.get('currency')!='USD' or m.get('instrumentType') not in ['EQUITY','ETF']:raise ValueError('Not a USD equity/ETF history')
   if m.get('symbol')!=symbol:raise ValueError('Provider symbol mismatch')
   bars=[]
   for i,t in enumerate(d.get('timestamp',[])):
    date=dt.datetime.fromtimestamp(t,ZoneInfo(m.get('exchangeTimezoneName','America/New_York'))).date().isoformat()
    if date>args.cutoff:continue
    a=adj[i] if i<len(adj) else None;c=q.get('close',[])[i]
    if not isinstance(a,(int,float)) or not math.isfinite(a) or a<=0 or not isinstance(c,(int,float)) or not math.isfinite(c) or c<=0:continue
    bars.append([date,round(a,6),round(c,6),q.get('volume',[None]*len(adj))[i]])
   if not bars or len({b[0] for b in bars})!=len(bars):raise ValueError('Missing or duplicate daily prices')
   out.update(status='ok',name=m.get('longName') or m.get('shortName'),currency=m['currency'],exchange=m.get('exchangeName'),instrumentType=m.get('instrumentType'),bars=sorted(bars),events=d.get('events',{}),firstDate=bars[0][0],lastDate=bars[-1][0])
  except Exception as e:out['reason']=str(e)
  time.sleep(.15)
  return symbol,out
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:securities=dict(pool.map(fetch,symbols))
 spy=securities.get('SPY',{});
 if spy.get('status')!='ok':raise SystemExit('Benchmark calendar unavailable; existing output preserved')
 calendar=[b[0] for b in spy['bars']];asof=calendar[-1]
 if (cutoff-dt.date.fromisoformat(asof)).days>4:raise SystemExit('Benchmark is stale; existing output preserved')
 data={'schemaVersion':1,'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'asOf':asof,'requestedCutoff':args.cutoff,'source':'Yahoo Finance','columns':['date','adjustedClose','close','volume'],'calendar':calendar,'mappings':mapping,'securities':securities}
 target=ROOT/'public/data/portfolio-history.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False));temp.replace(target)
 print(json.dumps({'asOf':asof,'requested':len(symbols),'ok':sum(v['status']=='ok' for v in securities.values()),'failed':{s:v.get('reason') for s,v in securities.items() if v['status']!='ok'},'bytes':target.stat().st_size}))
if __name__=='__main__':main()
