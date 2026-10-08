"""Build a reviewed expansion from five NSE bhavcopy ZIPs and current Upstox master.
Usage: python3 scripts/live-alpha/build-1000.py /path/to/input-directory
Input names: nse-YYYYMMDD.zip and nse-instruments.json.gz. Does not fetch or invent data.
"""
import csv,gzip,hashlib,io,json,pathlib,re,sys,zipfile
root=pathlib.Path(__file__).resolve().parents[2]; inputs=pathlib.Path(sys.argv[1])
dates=['20260930','20261001','20261005','20261006','20261007']
core=list(csv.DictReader((root/'indices/Nifty500.csv').open()))
core_isins={list(x.values())[4] for x in core};core_symbols={list(x.values())[2] for x in core}
master=json.loads(gzip.decompress((inputs/'nse-instruments.json.gz').read_bytes()))
active={x['instrument_key']:x for x in master if x.get('segment')=='NSE_EQ' and x.get('instrument_type')=='EQ'}
series={};sources=[]
for date in dates:
 p=inputs/f'nse-{date}.zip';raw=p.read_bytes();sources.append({'url':f'https://archives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date}_F_0000.csv.zip','sha256':hashlib.sha256(raw).hexdigest()})
 with zipfile.ZipFile(p) as z:
  rows=csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode('utf-8-sig')))
  for r in rows:
   isin=r['ISIN'];key='NSE_EQ|'+isin;symbol=r['TckrSymb'];m=active.get(key)
   if r['SctySrs']!='EQ' or not re.fullmatch(r'INE[A-Z0-9]{8}[0-9]',isin) or isin in core_isins or symbol in core_symbols or not m or m['trading_symbol']!=symbol:continue
   if r['TradDt'].replace('-','')!=date:raise ValueError('Wrong report date')
   if float(r['TtlTrfVal'])<=0 or float(r['TtlTradgVol'])<=0:continue
   series.setdefault((isin,symbol),{})[date]=float(r['TtlTrfVal'])
ranked=sorted(((sum(v.values())/5,k) for k,v in series.items() if len(v)==5),key=lambda x:(-x[0],x[1]))[:500]
assert len(ranked)==500
members=[{'symbol':symbol,'instrumentKey':'NSE_EQ|'+isin,'sector':'MARKET_PROXY','sectorInstrumentKey':'NSE_INDEX|Nifty 50','selectionAverageTradedValueINR':round(value,2)} for value,(isin,symbol) in ranked]
output={'name':'agi_nse1000','selectionAsOf':'2026-10-07','method':'Existing Nifty 500 plus 500 other active NSE EQ companies ranked by five-session average traded value; traded in all five sessions; exact ISIN and symbol confirmed against Upstox master. Not an official index.','sources':sources,'members':members}
(root/'server/config/live-alpha-nse1000-additions.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({'added':len(members),'lowestAverageDailyTurnoverINR':members[-1]['selectionAverageTradedValueINR'],'highest':members[0]['symbol']}))
