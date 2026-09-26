"""Strict US clipboard imports. USD stays USD; no inferred dates or SEC links."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime
from urllib.parse import urlparse

SOURCE = 'us_insider_paste'
CODES = {'UNKNOWN':'Unknown action (not supplied)', 'P':'Purchase (open market or private)', 'S':'Sale (open market or private)',
         'A':'Grant / award', 'D':'Disposition to issuer', 'F':'Tax / exercise withholding',
         'M':'Exercise / conversion', 'C':'Conversion', 'G':'Gift', 'J':'Other',
         'K':'Equity swap', 'U':'Tender', 'W':'Inheritance', 'Z':'Voting trust',
         'E':'Short derivative expiration', 'H':'Long derivative expiration',
         'I':'Discretionary plan transaction', 'L':'Small acquisition', 'O':'Out-of-money derivative exercise', 'X':'In-money derivative exercise'}
ALIASES = {
 'company': ['Company','Company Name','Stock'], 'symbol':['Ticker','Symbol'],
 'person':['Insider Name','Insider','Owner','Client Name'], 'category':['Title','Role','Relationship','Client Category'],
 'filed':['Filing Date','Reported Date','Reported To/By Exchange','Reported to Exchange'],
 'trade':['Trade Date','Transaction Date','Date'], 'code':['Transaction Code','Trade Type','Transaction','Action'],
 'quantity':['Quantity','Qty','Shares','#Shares'], 'price':['Price','Cost','Avg. Price'],
 'value':['Value','Value ($)','Value USD'], 'owned':['Owned','Shares Owned','Post Transaction Holding','#Shares Total'],
 'change':['ΔOwn','Delta Own','Ownership Change %'], 'plan':['10b5-1','10b5-1 Plan','Trading Plan'],
 'link':['SEC URL','Source URL','Filing URL'], 'id':['Transaction ID'],
 'security':['Security Type','Security'], 'form':['Form Type'], 'derivative':['Derivative'],
}
def _key(value): return re.sub(r'\s+',' ',str(value or '').strip().lower())
def _pick(row, field):
 for name in ALIASES[field]:
  if _key(name) in row: return str(row[_key(name)] or '').strip()
 return ''
def _number(value):
 if value.strip().lower() in {'','-','--','n/a','na','unknown','new'}: return None
 text=value.strip().replace(',','').replace('$','').replace('%','').replace('+','')
 if text.startswith('(') and text.endswith(')'):text='-'+text[1:-1]
 try: result=float(text)
 except ValueError: raise ValueError('invalid numeric value: '+value[:35])
 if not math.isfinite(result): raise ValueError('numeric value must be finite')
 return result

def _holding(value):
 # Clipboard holdings may contain a second line showing ownership percentage.
 # Parse only the share count; never combine it with the percentage.
 match=re.fullmatch(r'\s*([\d,]+(?:\.\d+)?)\s*\(\s*[\d.]+%\s*\)\s*',value)
 return _number(match.group(1) if match else value)

def _date(value, required=True, day_first=False):
 if not value and not required:return None
 # Dates without a year are deliberately not guessed. US slash dates are month/day/year.
 for fmt in ('%Y-%m-%d', *(['%d/%m/%Y','%d/%m/%y'] if day_first else ['%m/%d/%Y','%m/%d/%y']), '%b %d, %Y','%d %b %Y'):
  try:return datetime.strptime(value,fmt).date().isoformat()
  except ValueError:pass
 if re.match(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}',value):
  try:return datetime.fromisoformat(value.replace('Z','+00:00')).date().isoformat()
  except ValueError:pass
 raise ValueError('date needs a valid year (YYYY-MM-DD preferred): '+value[:35])

def _bool(value):
 s=value.strip().lower()
 if s in {'yes','true','1','y'}:return 'true'
 if s in {'no','false','0','n'}:return 'false'
 if s in {'','unknown','-','n/a'}:return 'unknown'
 raise ValueError('10b5-1 / Derivative must be Yes, No or Unknown')

def parse_pasted(text, **_):
 body=str(text or '').lstrip('\ufeff').strip()
 if not body:return {'ok':False,'error':'nothing_pasted','hint':'Paste the header and US trade rows.','rows':[]}
 if len(body)>2_000_000:return {'ok':False,'error':'paste_too_large','hint':'Split the paste into smaller batches.','rows':[]}
 header=body.splitlines()[0];delimiter='\t' if '\t' in header else ','
 try:
  reader=csv.DictReader(io.StringIO(body),delimiter=delimiter)
  raw=list(reader)
 except csv.Error as exc:return {'ok':False,'error':'invalid_table','hint':str(exc),'rows':[]}
 rows={};errors=[];duplicates=0
 for index,item in enumerate(raw,2):
  if not any(item.values()):continue
  try:
   if None in item:raise ValueError('extra cells: use tabs or quote values containing commas')
   row={_key(k):v for k,v in item.items()}
   symbol=_pick(row,'symbol').upper();company=_pick(row,'company') or symbol;person=_pick(row,'person')
   if not company or not person:raise ValueError('Company/Ticker and Insider Name are required')
   export_format='reported to exchange' in row
   filed=_date(_pick(row,'filed'),day_first=export_format);trade=_date(_pick(row,'trade'),required=not export_format,day_first=export_format)
   if trade and trade>filed:raise ValueError('trade date cannot follow filing date')
   rawcode=_pick(row,'code');code=rawcode.upper()
   code={'PURCHASE':'P','BUY':'P','SALE':'S','SELL':'S','OPTION EXERCISE':'M','GIFT':'G','AWARD':'A'}.get(code,code)
   if re.match(r'^[A-Z]\s*[-–]',code):code=code[0]
   description=_key(rawcode.replace(',', ''))
   if export_format and not rawcode:code='UNKNOWN'
   for prefix, mapped in [('exercise or conversion of derivative security received from the company','M'),('payment of exercise price or tax liability using portion of securities received from the company','F'),('sale of securities on an exchange or to another person','S'),('purchase of securities on an exchange or from another person','P'),('acquisition of securities','J'),('grant award or other acquisition','A'),('other type of transaction','J'),('sale or transfer of securities back to the company','D'),('gift of securities','G')]:
    if description.startswith(prefix):
     code=mapped;break
   if code not in CODES:raise ValueError('unsupported transaction code: '+rawcode)
   if _pick(row,'form').upper() in {'4/A','AMENDMENT','AMENDED'}:raise ValueError('amendments require reconciliation with the original transaction; do not import as a new trade')
   qty=_number(_pick(row,'quantity'));price=_number(_pick(row,'price'));value=_number(_pick(row,'value'))
   if qty is None or qty==0:raise ValueError('non-zero shares are required')
   if qty<0 and code not in {'S','D','F','G','J'}:raise ValueError('negative shares conflict with transaction code')
   if price is not None and price<0:raise ValueError('price cannot be negative')
   if value is not None and value<0 and code not in {'S','D','F','G','J'}:raise ValueError('negative value conflicts with transaction code')
   plan=_bool(_pick(row,'plan'));derivative=_bool(_pick(row,'derivative'))
   link=_pick(row,'link')
   if link and (urlparse(link).scheme!='https' or not urlparse(link).hostname or urlparse(link).username):raise ValueError('source URL must begin with https://')
   filing_stamp=datetime.fromisoformat(_pick(row,'filed').replace('Z','+00:00')).isoformat() if re.match(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}',_pick(row,'filed')) else filed
   change_text=_pick(row,'change')
   change_num=None if re.match(r'^[<>]',change_text) else _number(change_text)
   identity_parts=[symbol,company,person,filing_stamp,trade,code,abs(qty),price,_pick(row,'security')]
   if export_format:identity_parts.append(_holding(_pick(row,'owned')))
   identity=json.dumps([symbol or company,_pick(row,'id')]) if _pick(row,'id') else json.dumps(identity_parts,ensure_ascii=False)
   legacy_ident=hashlib.sha256(identity.encode()).hexdigest()[:32]
   if export_format and not _pick(row,'id'):
    identity=json.dumps([identity, _key(rawcode), abs(value) if value is not None else None],ensure_ascii=False)
   ident=hashlib.sha256(identity.encode()).hexdigest()[:32]
   candidate={'trade_id':ident,'_legacy_trade_id':legacy_ident if ident!=legacy_ident else None,'company_name':company,'symbol':symbol or None,'symbol_match':'provided' if symbol else 'unmapped',
    'reported_on':filed,'transaction_date':trade,'filing_timestamp':filing_stamp,'person':person,'category':_pick(row,'category') or None,
    'transaction_code':code,'action_description':rawcode,'action':'Acquisition' if code=='P' else 'Disposal' if code=='S' else CODES[code],
    'quantity':abs(qty),'avg_price':price,'value':abs(value) if value is not None else None,
    'post_holding':_holding(_pick(row,'owned')),'ownership_change_pct':change_num,'ownership_change_text':change_text or None,
    'mode':CODES[code],'regulation':'SEC Form 4 import','regime':'insider','security_type':_pick(row,'security') or None,
    'period':trade,'is_open_market':'false','is_purchase_sale':'true' if code in {'P','S'} else 'false',
    'planned':plan,'derivative':derivative,'source_url':link or None,'source':SOURCE,'country':'US','currency':'USD'}
   if ident in rows:
    if rows[ident]!=candidate:raise ValueError('conflicting rows share one transaction identity; use distinct Transaction IDs')
    duplicates+=1
   rows[ident]=candidate
  except ValueError as exc:errors.append(f'Row {index}: {exc}')
 out=list(rows.values());dates=[r['reported_on'] for r in out]
 return {'ok':bool(out) and not errors,'rows':out,'country':'US','currency':'USD','row_count':len(out),'pasted_rows':len(raw),'dropped_rows':len(errors),'duplicate_rows':duplicates,
  'error':'invalid_us_rows' if errors else None,'hint':'; '.join(errors[:5]) if errors else ('Paste at least one US transaction.' if not out else None),
  'errors':errors[:50],'companies':len({r['company_name'] for r in out}),'with_symbol':sum(bool(r['symbol']) for r in out),
  'open_market_rows':sum(r['is_purchase_sale']=='true' for r in out),'first_reported':min(dates) if dates else None,'last_reported':max(dates) if dates else None,
  'preview_rows':out[:6], 'limitations':['P/S codes include private transactions; they do not prove exchange execution.','10b5-1 and derivative status stay unknown when omitted.','Trade date stays unknown when absent. Reported to Exchange exports use day/month/year.','Generic acquisitions and blank actions are not treated as market purchases. Blank actions are retained as Unknown.','Use distinct Transaction IDs for otherwise identical trades. Amendments require reconciliation.','Values must be absolute USD amounts; ownership change is not percentage of company equity.']}

def import_pasted(text, *, actor='us_insider_paste'):
 from institutional_warehouse import gateway, db
 parsed=parse_pasted(text)
 if not parsed['ok']:return {k:v for k,v in parsed.items() if k!='rows'}
 # Preserve IDs already published by the earlier rounded-price importer.
 # Match description AND value before reusing one; a distinct trade gets its new ID.
 legacy_ids=list({r['_legacy_trade_id'] for r in parsed['rows'] if r.get('_legacy_trade_id')})
 existing={}
 for start in range(0,len(legacy_ids),200):
  batch=legacy_ids[start:start+200]
  for old in db.query('SELECT trade_id, action_description, value FROM wh_us_insider_trades WHERE trade_id IN ('+','.join('?' for _ in batch)+')',batch):
   existing[old['trade_id']]=old
 for row in parsed['rows']:
  old=existing.get(row.pop('_legacy_trade_id',None))
  if old and _key(old.get('action_description'))==_key(row['action_description']) and old.get('value')==row['value']:
   row['trade_id']=old['trade_id']
 written=gateway.write('us_insider_trades',parsed['rows'],source=SOURCE,actor=actor,reason='us_insider_paste')
 return {**{k:v for k,v in parsed.items() if k!='rows'},'written':written,'ok':bool(written.get('ok'))}
