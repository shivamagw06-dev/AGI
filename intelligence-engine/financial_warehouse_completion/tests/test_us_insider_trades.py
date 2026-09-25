import csv,io
import pytest
from financial_warehouse_completion.us_insider_trades import parse_pasted,import_pasted
HEAD=['Company Name','Ticker','Insider Name','Title','Filing Date','Trade Date','Trade Type','Qty','Price','Value','Owned','ΔOwn','10b5-1','SEC URL','Transaction ID','Derivative','Form Type']
def paste(*changes):
 out=io.StringIO();w=csv.writer(out,delimiter='\t');w.writerow(HEAD)
 for change in changes or ({},):
  row=dict(zip(HEAD,['Example Inc','EXM','Example Person','CEO','2026-09-25 16:05:00','2026-09-24','P - Purchase','1,000','$25.50','+$25,500','11,000','+10%','','https://www.sec.gov/Archives/example','','No','4']));row.update(change);w.writerow([row[h] for h in HEAD])
 return out.getvalue()
def test_openinsider_headers_values_and_plan_unknown():
 result=parse_pasted(paste());assert result['ok'];r=result['rows'][0]
 assert r['value']==25500 and r['quantity']==1000 and r['country']=='US'
 assert r['planned']=='unknown' and r['is_open_market']=='false' and r['transaction_code']=='P'
 assert r['ownership_change_pct']==10 and r.get('traded_pct') is None
@pytest.mark.parametrize('code',['P','S','A','F','M','G','C','J'])
def test_distinct_us_codes(code):
 r=parse_pasted(paste({'Trade Type':code}))['rows'][0];assert r['transaction_code']==code
 assert (r['is_purchase_sale']=='true')==(code in {'P','S'})
def test_duplicates():
 assert parse_pasted(paste({},{}))['row_count']==1
 assert parse_pasted(paste({'Transaction ID':'one'},{'Transaction ID':'two'}))['row_count']==2
def test_no_partial_publish():
 r=parse_pasted(paste({}, {'Trade Date':'Sep 24'}));assert not r['ok'];assert 'Row 3' in r['hint']
@pytest.mark.parametrize('change',[{'Trade Type':'BOGUS'},{'Qty':'NaN'},{'Price':'Infinity'},{'SEC URL':'javascript:alert(1)'},{'Form Type':'4/A'},{'10b5-1':'maybe'},{'Trade Date':'2026-09-26'}])
def test_reject_bad_input(change):assert not parse_pasted(paste(change))['ok']
def test_us_dates_signed_sale():
 r=parse_pasted(paste({'Trade Date':'09/24/2026','Filing Date':'09/25/2026','Trade Type':'S - Sale','Qty':'-1,000','Value':'-$25,500','10b5-1':'Yes'}))['rows'][0]
 assert r['quantity']==1000 and r['value']==25500 and r['planned']=='true'
def test_missing_values():
 r=parse_pasted(paste({'Price':'','Value':''}))['rows'][0];assert r['value'] is None and r['avg_price'] is None

def test_gateway_isolation_and_repaste(tmp_path,monkeypatch):
 from institutional_warehouse import db
 monkeypatch.setenv('INSTITUTIONAL_WAREHOUSE_ROOT',str(tmp_path))
 monkeypatch.delenv('WAREHOUSE_DATABASE_URL',raising=False);monkeypatch.delenv('INSTITUTIONAL_WAREHOUSE_DATABASE_URL',raising=False)
 monkeypatch.setattr(db,'_BACKEND',None);monkeypatch.setattr(db,'_INITIALISED',False)
 first=import_pasted(paste());assert first['ok'],first
 again=import_pasted(paste());assert again['ok'],again
 rows=db.query('SELECT * FROM wh_us_insider_trades');assert len(rows)==1;assert rows[0]['value']==25500
 assert db.query('SELECT COUNT(*) AS n FROM wh_insider_trades')[0]['n']==0
 if db._BACKEND:db._BACKEND.close()
def test_conflicting_same_identity_blocks_publication():
 assert not parse_pasted(paste({'Transaction ID':'same'},{'Transaction ID':'same','Value':'999'}))['ok']
def test_bounded_holding_change_remains_text_not_exact_percentage():
 r=parse_pasted(paste({'ΔOwn':'>999%'}))['rows'][0]
 assert r['ownership_change_pct'] is None and r['ownership_change_text']=='>999%'
