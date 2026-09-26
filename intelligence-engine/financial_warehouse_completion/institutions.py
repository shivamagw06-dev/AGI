"""Owner-published investor snapshots. INR crore and USD million never mix."""
import csv
import html
import io
import json
import math
import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse

ALIASES={'name':['superstar','investor','institution'],'value':['portfolio value change','portfolio value'],'stocks':['of stocks','no of stocks','number of stocks','stocks'],'sectors':['sector preference'],'quarterly':['quarterly net worth'],'holdings':['top holdings'],'bought':['recently bought'],'sold':['recently sold']}
def clean(s):return html.unescape(re.sub(r'<[^>]+>','',re.sub(r'<br\s*/?>','\n',str(s or ''),flags=re.I))).strip().replace('**','')
def key(s):return re.sub(r'[^a-z0-9]+',' ',clean(s).lower()).strip()
def plain(s):return re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',clean(s))
def link(s):
 match=re.search(r'\[([^\]]+)\]\(([^)]+)\)',s)
 if not match:return {'label':' '.join(plain(s).split()),'url':None}
 url=match[2].strip();u=urlparse(url)
 if u.scheme!='https' or not u.hostname or u.username:raise ValueError('Links must use https://')
 return {'label':' '.join(match[1].split()),'url':url}
def entries(s):return [link(v) for v in clean(s).splitlines() if plain(v).strip() not in {'','-','—','–'}]
def parse(text,country='IN',as_of=None):
 if country not in {'IN','US'}:return {'ok':False,'errors':['Choose India or USA.']}
 if as_of:
  try:date.fromisoformat(as_of)
  except (ValueError,TypeError):return {'ok':False,'errors':['Valuation date must be YYYY-MM-DD.']}
 body=str(text or '').lstrip('\ufeff').strip('\r\n')
 if not body or len(body)>2_000_000:return {'ok':False,'errors':['Paste a table under 2 MB, including its header.']}
 if body.startswith('|'):
  table=[[x.strip() for x in line.strip().strip('|').split('|')] for line in body.splitlines() if line.strip() and not re.fullmatch(r'[\s|:\-]+',line)]
 else:
  try:table=list(csv.reader(io.StringIO(body),delimiter='\t' if '\t' in body.splitlines()[0] else ',',strict=True))
  except csv.Error as e:return {'ok':False,'errors':[f'Invalid table: {e}']}
 if not table:return {'ok':False,'errors':['Include the column headers.']}
 headers=[key(x) for x in table[0]];columns={}
 for field,names in ALIASES.items():
  matches=[i for i,h in enumerate(headers) if h in names]
  if len(matches)>1:return {'ok':False,'errors':[f'Duplicate {field} column.']}
  if matches:columns[field]=matches[0]
 for required in ['name','value','stocks','sectors','holdings','bought','sold']:
  if required not in columns:return {'ok':False,'errors':[f'Missing column: {ALIASES[required][0]}']}
 if len(table)>5001:return {'ok':False,'errors':['Paste no more than 5,000 investors at a time.']}
 rows={};errors=[];duplicates=0
 for n,cells in enumerate(table[1:],2):
  if not any(x.strip() for x in cells):continue
  try:
   if len(cells)<len(headers) or any(x.strip() for x in cells[len(headers):]):raise ValueError('Column count differs from header. Copy the complete table.')
   get=lambda field:cells[columns[field]] if field in columns else ''
   person=link(clean(get('name')));name=person['label']
   if not name:raise ValueError('Investor name is required.')
   amount=plain(get('value')).replace(',','').replace('₹','').replace('$','')
   m=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(Cr|M)\s*(?:([↑↓+−-]?)\s*([+−-]?\d+(?:\.\d+)?)\s*%)?\s*',amount,re.I)
   if not m:raise ValueError('Portfolio value must include Cr (India) or M (USA), optionally followed by change %.')
   unit='Cr' if country=='IN' else 'M'
   if m[2].lower()!=unit.lower():raise ValueError(f'{country} values must use {unit}. Check the selected market.')
   value=float(m[1]);change=float(m[4].replace('−','-')) if m[4] else None
   if change is not None and m[3] in {'↓','-','−'}:change=-abs(change)
   count=plain(get('stocks')).strip().replace(',','')
   if not re.fullmatch(r'\d+',count):raise ValueError('Number of stocks must be a whole number.')
   if not math.isfinite(value) or (change is not None and not math.isfinite(change)):raise ValueError('Values must be finite.')
   quarterly=plain(get('quarterly')).strip()
   row={'name':name,'url':person['url'],'value':value,'change':change,'stocks':int(count),'sectors':entries(get('sectors')),'holdings':entries(get('holdings')),'bought':entries(get('bought')),'sold':entries(get('sold')),'quarterlyNetWorth':quarterly if quarterly not in {'','-','—','–'} else None}
   identity=' '.join(name.casefold().split())
   if identity in rows:
    if rows[identity]!=row:raise ValueError(f'Conflicting entries for {name}. Keep one current row.')
    duplicates+=1
   rows[identity]=row
  except ValueError as e:errors.append(f'Row {n}: {e}')
 return {'ok':bool(rows) and not errors,'country':country,'currency':'INR' if country=='IN' else 'USD','unit':'Cr' if country=='IN' else 'M','asOf':as_of or None,'rows':list(rows.values()),'row_count':len(rows),'duplicate_rows':duplicates,'errors':errors or ([] if rows else ['No investor rows found.'])}
def snapshot_key(country,category):
 if country not in {'IN','US'}:raise ValueError('Invalid country')
 if category not in {'individual','institutional'}:raise ValueError('Invalid investor category')
 return country if category=='individual' else country+':institutional'
def current(country,category='individual'):
 from institutional_warehouse import db
 storage_key=snapshot_key(country,category)
 found=db.query('SELECT snapshot_json FROM wh_institution_snapshots WHERE country = ?',[storage_key])
 result=json.loads(found[0]['snapshot_json']) if found else {'country':country,'published':False,'rows':[]}
 result['category']=category
 return result
def publish(text,country,as_of=None,actor='admin',category='individual'):
 from institutional_warehouse import gateway
 storage_key=snapshot_key(country,category)
 result=parse(text,country,as_of)
 if not result['ok']:return result
 result.update(category=category,published=True,updatedAt=datetime.now(timezone.utc).isoformat())
 payload=json.dumps(result,ensure_ascii=False,allow_nan=False)
 written=gateway.write('institution_snapshots',[{'country':storage_key,'snapshot_json':payload}],source='institutions_admin_paste',actor=actor,reason='Replace selected market investor snapshot')
 return {'ok':bool(written.get('ok')) and written.get('quarantined',0)==0,'row_count':result['row_count'],'written':written,'updatedAt':result['updatedAt']}
