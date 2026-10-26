"""Read-only, rate-limited SEC audit of the selected public manager directory.
No broker/database mutations. Unknown, amended and missing sources remain explicit.
"""
import concurrent.futures, hashlib, json, re, threading, time, ssl
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path('/private/tmp/agi-hedge-source-cache-'+datetime.now(timezone.utc).strftime('%Y%m%d'));CACHE.mkdir(exist_ok=True)
try:
 import certifi
 TLS=ssl.create_default_context(cafile=certifi.where())
except ImportError:
 TLS=ssl.create_default_context()
LOCK=threading.Lock();LAST=0
UA='AGI Institutional Research research@agarwalglobalinvestments.com'
# Identity-reviewed links discovered in Dataroma's public manager directory.
SECONDARY={'akre-capital':'AC','appaloosa-management':'AM','berkshire-hathaway':'BRK','tiger-global':'TGM','tci-fund-management':'tci','third-point':'tp','himalaya-capital':'HC','pershing-square':'psc','fundsmith':'FS','hh-international':'HH','durable-capital':'DCP','maverick-capital':'mc','baupost-group':'BAUPOST','lone-pine-capital':'LPC','valley-forge-capital':'VFC','viking-global':'vg','gates-foundation-trust':'GFT'}

def get(url):
 global LAST
 path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.raw')
 if path.exists():return path.read_bytes()
 for attempt in range(3):
  with LOCK:
   pause=.24-(time.monotonic()-LAST)
   if pause>0:time.sleep(pause)
   LAST=time.monotonic()
  try:
   with urlopen(Request(url,headers={'User-Agent':UA}),timeout=35,context=TLS) as r:data=r.read()
   path.write_bytes(data);return data
  except Exception:
   if attempt==2:raise
   time.sleep(2*(attempt+1))

def field(el,name):
 for node in el.iter():
  if node.tag.split('}')[-1].lower()==name.lower():return (node.text or '').strip()
 return ''

def parse_table(raw):
 root=ET.fromstring(raw);out=[]
 for node in root.iter():
  if node.tag.split('}')[-1].lower()!='infotable':continue
  if not field(node,'cusip'):continue
  quantity=field(node,'sshPrnamt');value=field(node,'value')
  if not re.fullmatch(r'\d+(?:\.\d+)?',quantity) or not re.fullmatch(r'\d+(?:\.\d+)?',value):raise ValueError('Invalid quantity/value')
  out.append(dict(cusip=field(node,'cusip').upper(),issuer=field(node,'nameOfIssuer'),securityClass=field(node,'titleOfClass'),unit=field(node,'sshPrnamtType').upper(),option=field(node,'putCall').upper(),quantity=float(quantity),value=float(value)))
 return out

def aggregate(rows):
 out={}
 for r in rows:
  # Retain security class, units and option side; never combine stock with a put.
  key='|'.join(r[k] for k in ('cusip','unit','option'))
  if key not in out:out[key]={**r,'quantity':0,'value':0,'classLabels':[]}
  if r['securityClass'] not in out[key]['classLabels']:out[key]['classLabels'].append(r['securityClass'])
  out[key]['quantity']+=r['quantity'];out[key]['value']+=r['value']
 return out

def compare(current,prior):
 a,b=aggregate(current),aggregate(prior);changes=[]
 for k in a.keys()|b.keys():
  r=a.get(k) or b[k]
  if r['option'] or r['unit']!='SH':continue
  old=b.get(k,{}).get('quantity',0);new=a.get(k,{}).get('quantity',0)
  identityReview=k in a and k in b and {x.upper().strip() for x in a[k]['classLabels']}!={x.upper().strip() for x in b[k]['classLabels']}
  if old==new:continue
  changes.append(dict(cusip=r['cusip'],issuer=r['issuer'],securityClass=r['securityClass'],identityReview=identityReview,priorQuantity=old,quantity=new,quantityChange=new-old,quantityChangePct=round((new/old-1)*100,4) if old else None,status='New disclosure' if old==0 else 'Absent in newer table' if new==0 else 'Quantity increased' if new>old else 'Quantity reduced',rankingValue=a.get(k,{}).get('value',0) if new>old else b.get(k,{}).get('value',0)))
 return sorted(changes,key=lambda x:(-x['rankingValue'],x['cusip']))

def filing(cik,row):
 base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{row["accessionNumber"].replace("-","")}/'
 index=json.loads(get(base+'index.json'));rows=[];sources=[];cover=None
 for f in index['directory']['item']:
  name=f['name']
  if not name.lower().endswith('.xml'):continue
  raw=get(base+name)
  parsed=parse_table(raw)
  if parsed:rows+=parsed;sources.append(base+name)
  elif name==row.get('primaryDocument','').rsplit('/',1)[-1]:cover=ET.fromstring(raw)
 if not rows:raise ValueError('Information table unavailable')
 amendmentType=field(cover,'amendmentType') if cover is not None else ''
 if cover is not None:
  declared=field(cover,'tableEntryTotal')
  if declared.isdigit() and int(declared)!=len(rows):raise ValueError('SEC cover/table line count differs; reconciliation required')
 return dict(period=row['reportDate'],filedAt=row['filingDate'],form=row['form'],accession=row['accessionNumber'],sourceUrl=base+row['primaryDocument'],tableSources=sources,amendmentType=amendmentType,rows=rows)

def audit(m):
 out=dict(slug=m['slug'],name=m['display_name'],cik=m['cik'],managerType=m.get('manager_type'),checkedAt=datetime.now(timezone.utc).isoformat(),directoryPeriod=m.get('latest_filing',{}).get('report_date'),secUrl=f'https://www.sec.gov/edgar/browse/?CIK={int(m["cik"])}&owner=exclude')
 try:
  sub=json.loads(get(f'https://data.sec.gov/submissions/CIK{str(m["cik"]).zfill(10)}.json'));r=sub['filings']['recent']
  entries=[{k:r[k][i] for k in ['form','reportDate','filingDate','accessionNumber','primaryDocument']} for i,f in enumerate(r['form']) if f in ['13F-HR','13F-HR/A','13F-NT','13F-NT/A'] and r['reportDate'][i]]
  reports=sorted([x for x in entries if x['form'].startswith('13F-HR')],key=lambda x:(x['reportDate'],x['filingDate']),reverse=True)
  notices=sorted([x for x in entries if x['form'].startswith('13F-NT')],key=lambda x:(x['reportDate'],x['filingDate']),reverse=True)
  if not reports:out.update(status='No holdings table in recent SEC record',latestNotice=notices[0] if notices else None);return out
  latest=filing(m['cik'],reports[0]);rows=latest.pop('rows');out.update(latest=latest,sourceRowCount=len(rows),nonOptionShRows=sum(not x['option'] and x['unit']=='SH' for x in rows),optionRows=sum(bool(x['option']) for x in rows),otherUnitRows=sum(not x['option'] and x['unit']!='SH' for x in rows),disclosedTableValue=round(sum(x['value'] for x in rows),2),nonOptionShValue=round(sum(x['value'] for x in rows if not x['option'] and x['unit']=='SH'),2),optionUnderlyingValue=round(sum(x['value'] for x in rows if x['option']),2))
  out['status']='Reports through another filer' if notices and notices[0]['reportDate']>latest['period'] else 'Historical SEC record' if latest['period']<'2026-06-30' else 'SEC table checked'
  if notices:out['latestNotice']=notices[0]
  if out['status']=='Reports through another filer':
   notice=notices[0];base=f'https://www.sec.gov/Archives/edgar/data/{int(m["cik"])}/{notice["accessionNumber"].replace("-","")}/'
   noticeRoot=ET.fromstring(get(base+'primary_doc.xml'));out['noticeSource']=base+'primary_doc.xml'
   out['reportingFilers']=[dict(name=field(x,'name'),cik=field(x,'cik'),secUrl=f'https://www.sec.gov/edgar/browse/?CIK={int(field(x,"cik"))}&owner=exclude') for x in noticeRoot.iter() if x.tag.split('}')[-1]=='otherManager' and field(x,'cik')]
   # A single named successor can be inspected separately, never silently merged.
   if len(out['reportingFilers'])==1:
    parent=out['reportingFilers'][0]
    out['alternatePortfolio']=audit(dict(slug=m['slug']+'-notice-filer',display_name=parent['name'],cik=parent['cik'],manager_type='Notice-named filer',latest_filing={}))
    out['alternatePortfolio']['secondary']=secondary(m,out['alternatePortfolio'])
    out['alternatePortfolio'].pop('auditHoldings',None);out['alternatePortfolio']['changes']=[]
  out['directoryPeriodMatches']=latest['period']==out['directoryPeriod']
  out['nonOptionShSecurities']=sum(not x['option'] and x['unit']=='SH' for x in aggregate(rows).values())
  out['directoryPositionCount']=m.get('position_count')
  out['directoryCountMatches']=out['nonOptionShSecurities']==m.get('position_count')
  out['auditHoldings']=rows
  out['sourceTopHoldings']=sorted([x for x in aggregate(rows).values() if not x['option'] and x['unit']=='SH'],key=lambda x:-x['value'])[:3]
  try:
   priorRow=next((x for x in reports if x['reportDate']<latest['period']),None)
   if latest['form'].endswith('/A') and 'RESTATEMENT' not in latest['amendmentType'].upper():out['comparisonStatus']='Amendment requires reconciliation; quantity comparisons withheld'
   elif priorRow:
    out['priorCandidate']={**priorRow,'sourceUrl':f'https://www.sec.gov/Archives/edgar/data/{int(m["cik"])}/{priorRow["accessionNumber"].replace("-","")}/{priorRow["primaryDocument"]}'}
    prior=filing(m['cik'],priorRow);previous=prior.pop('rows');out['prior']=prior
    if prior['form'].endswith('/A') and 'RESTATEMENT' not in prior['amendmentType'].upper():out['comparisonStatus']='Prior amendment requires reconciliation; quantity comparisons withheld'
    else:out.update(changes=compare(rows,previous),comparisonStatus='Reported quantities compared; corporate actions and trading motives not inferred')
   else:out['comparisonStatus']='Earlier quarter unavailable in recent SEC record'
  except Exception as e:
   out['comparisonStatus']='Prior-quarter source does not reconcile; quantity comparisons withheld'
   out['comparisonError']=str(e)[:180]
   out['changes']=[]
 except Exception as e:out.update(status='Source check incomplete',error=str(e)[:180])
 return out

def secondary(m,record):
 from bs4 import BeautifulSoup
 code=SECONDARY.get(m['slug'])
 if not code:return dict(status='Not covered by reviewed Dataroma identity map')
 url=f'https://www.dataroma.com/m/holdings.php?m={code}'
 try:
  soup=BeautifulSoup(get(url),'html.parser');text=soup.get_text(' ',strip=True)
  quarter=re.search(r'Period:\s*Q([1-4])\s*(20\d{2})',text);value=re.search(r'Portfolio value:\s*\$([\d,]+)',text)
  period=f'{quarter[2]}-{int(quarter[1])*3:02d}-'+('31' if quarter[1] in ('1','4') else '30') if quarter else None
  stocks=[];secondaryRows=[]
  for tr in soup.select('tr'):
   link=tr.select_one('a[href*="stock.php?sym="]')
   if not link:continue
   stocks.append(link.get_text(' ',strip=True))
   tds=[x.get_text(' ',strip=True) for x in tr.select('td')]
   if len(tds)>6 and re.fullmatch(r'[\d,]+(?:\.\d+)?',tds[4]):secondaryRows.append(dict(symbol=link.get('href').split('sym=')[-1].split('&')[0].replace('.','-'),quantity=float(tds[4].replace(',',''))))
  mappings=json.loads((ROOT/'src/data/investorProfiles/priceMappings.json').read_text())['CUSIP']
  # Quantity matching uses exact existing CUSIP-to-symbol identities, never fuzzy issuer names.
  sourceRows=record.get('auditHoldings',[])
  primaryBySymbol=defaultdict(float)
  for r in aggregate(sourceRows).values():
   mapping=mappings.get(r['cusip'],{})
   symbol=mapping.get('symbol') if isinstance(mapping,dict) else mapping
   if symbol and not r['option'] and r['unit']=='SH':primaryBySymbol[symbol.replace('.','-')]+=r['quantity']
  matched=[r for r in secondaryRows if r['symbol'] in primaryBySymbol]
  mismatches=[dict(**r,secQuantity=primaryBySymbol[r['symbol']]) for r in matched if r['quantity']!=primaryBySymbol[r['symbol']]]
  return dict(matchedQuantityRows=len(matched) if period==record.get('latest',{}).get('period') else 0,quantityMismatches=mismatches if period==record.get('latest',{}).get('period') else [],unmappedSecondaryRows=len(secondaryRows)-len(matched),url=url,status='Dataroma page checked' if quarter else 'Secondary page could not be parsed',period=period,periodMatches=period==record.get('latest',{}).get('period') if period else None,reportedValue=float(value[1].replace(',','')) if value else None,stockRows=len(stocks),note='Secondary presentation may exclude options or aggregate security lines. A differing value is not a return discrepancy.')
 except Exception as e:return dict(url=url,status='Secondary check incomplete',error=str(e)[:120])

def apply_reviews(report):
 reviews=json.loads((ROOT/'scripts/hedge_fund_audit/reviews.json').read_text())
 by={r['slug']:r for r in report['managers']}
 report['contextReviewedAt']=reviews['reviewedAt']
 report['whaleWisdomChecks']=[w for w in reviews['whaleWisdomChecks'] if by.get(w['slug'],{}).get('latest',{}).get('period')==w['period']]
 report['insights']=[i for i in reviews['insights'] if by.get(i['slug'],{}).get('latest',{}).get('period')==i['period'] and by[i['slug']].get('status')=='SEC table checked']
 for r in report['managers']:
  q=r.get('secondary',{});unresolved=[];resolved=[]
  for mismatch in q.get('quantityMismatches',[]):
   action=next((a for a in reviews['corporateActions'] if a['symbol']==mismatch['symbol'] and r['latest']['period']<a['date']<=reviews['reviewedAt']),None)
   if action and abs(mismatch['quantity']-mismatch['secQuantity']*action['factor'])<1:
    resolved.append(dict(**mismatch,corporateAction=action,status='Consistent with later split basis within one share; original SEC quantity retained'))
   else:unresolved.append(mismatch)
  q['splitBasisComparisons']=resolved;q['quantityMismatches']=unresolved


def main():
 data=json.loads(get('https://finance-news-backend-19i5.onrender.com/api/institutional-holdings/overview'));managers=data['managers'];by={m['slug']:m for m in managers};out=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for record in pool.map(audit,managers):
   out.append(record)
   print(record['name'],record['status'],record.get('sourceRowCount'),flush=True)
 report=dict(schemaVersion=1,checkedAt=datetime.now(timezone.utc).isoformat(),universe='Selected Hedge Funds directory; not every fund on ownership websites',managerCount=len(managers),methodology='Original SEC submissions and latest/previous information tables. Security class, quantity unit and option side retained. Quantity differences are not proven trading flows; corporate actions are not adjusted. Secondary sites are cross-checks, not primary evidence.',managers=out)
 (CACHE/'full-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 for record in out:record['secondary']=secondary(by[record['slug']],record)
 (CACHE/'full-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 apply_reviews(report)
 for record in report['managers']:
  record.pop('auditHoldings',None)
  changes=record.pop('changes',[])
  record['quantityChangeCount']=len(changes)
  record['identityReviewCount']=sum(x['identityReview'] for x in changes)
  safe=[x for x in changes if not x['identityReview']]
  record['changes']=[x for x in safe if x['quantityChange']>0][:5]+[x for x in safe if x['quantityChange']<0][:5]
  record['changeDisplayLimit']='Five largest increases/new disclosures and five reductions/absences by reported value; class-wording conflicts excluded. Full tables linked.'
 (ROOT/'public/data/hedge-fund-source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Saved audit',len(out),flush=True)
if __name__=='__main__':main()
