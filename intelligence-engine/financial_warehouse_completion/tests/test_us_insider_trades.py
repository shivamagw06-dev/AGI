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

EXPORT_HEAD=['Stock','Client Name','Client Category','Action','Reported to Exchange','Quantity','Post Transaction Holding','Traded %','Avg. Price','Value','Security Type']
def export_paste(**changes):
 row=dict(zip(EXPORT_HEAD,['Globe Life','Robert Edward Hensley','EVP & Chief Investment Officer','Exercise or conversion of derivative security received from the company   (such as an option) at price $ 103.23 per share.','22/09/26','10000','22383','0%','103.2','10,32,300','Common Stock']));row.update(changes)
 out=io.StringIO();w=csv.writer(out,delimiter='\t');w.writerow(EXPORT_HEAD);w.writerow([row[h] for h in EXPORT_HEAD]);return out.getvalue()
def test_exact_user_export():
 r=parse_pasted(export_paste());assert r['ok'],r
 row=r['rows'][0];assert row['reported_on']=='2026-09-22';assert row['transaction_date'] is None
 assert row['value']==1032300 and row['transaction_code']=='M' and row['is_purchase_sale']=='false'
 assert row.get('traded_pct') is None and row['ownership_change_pct'] is None
 assert row['action_description'].startswith('Exercise or conversion')
@pytest.mark.parametrize('action,code',[
 ('Sale of securities on an exchange or to another person at price $ 238.51 per share.','S'),
 ('Payment of exercise price or tax liability using portion of securities received from the company at price $ 52.93 per share.','F'),
 ('Acquisition of securities at price $ 110.07 per share.','J'),
 ('Purchase of securities on an exchange or from another person at price $ 10 per share.','P')])
def test_export_descriptions(action,code):
 r=parse_pasted(export_paste(Action=action));assert r['ok'];assert r['rows'][0]['transaction_code']==code

def test_export_ambiguous_date_is_day_first():
 r=parse_pasted(export_paste(**{'Reported to Exchange':'03/09/26'}));assert r['rows'][0]['reported_on']=='2026-09-03'
def test_export_distinct_holdings_not_collapsed():
 a=export_paste();b=export_paste(**{'Post Transaction Holding':'23000'}).splitlines()[1]
 assert parse_pasted(a+b+'\n')['row_count']==2

def test_export_gateway_missing_trade_date(tmp_path,monkeypatch):
 from institutional_warehouse import db
 monkeypatch.setenv('INSTITUTIONAL_WAREHOUSE_ROOT',str(tmp_path))
 monkeypatch.delenv('WAREHOUSE_DATABASE_URL',raising=False);monkeypatch.delenv('INSTITUTIONAL_WAREHOUSE_DATABASE_URL',raising=False)
 monkeypatch.setattr(db,'_BACKEND',None);monkeypatch.setattr(db,'_INITIALISED',False)
 result=import_pasted(export_paste());assert result['ok'],result
 rows=db.query('SELECT * FROM wh_us_insider_trades');assert len(rows)==1 and rows[0]['transaction_date'] is None
 assert rows[0]['value']==1032300 and rows[0]['action_description'].startswith('Exercise')
 assert import_pasted(export_paste())['ok'];assert len(db.query('SELECT * FROM wh_us_insider_trades'))==1
 if db._BACKEND:db._BACKEND.close()

@pytest.mark.parametrize('action,code',[
 ('Grant, award, or other acquisition of securities at price $ 0.00 per share.','A'),
 ('Grant, award or other acquisition of securities at price $ 0.00 per share.','A'),
 ('Other type of transaction at price $ 0.00 per share.','J'),
 ('Sale or transfer of securities back to the company at price $ 10.00 per share.','D'),
 ('Gift of securities by or to the insider at price $ 0.00 per share.','G'),
 ('','UNKNOWN'),
])
def test_additional_export_actions(action,code):
 result=parse_pasted(export_paste(Action=action));assert result['ok'],result
 row=result['rows'][0];assert row['transaction_code']==code
 assert row['is_purchase_sale']=='false' and row['action_description']==action

def test_multiline_holding_is_shares_only():
 result=parse_pasted(export_paste(**{'Post Transaction Holding':'0\n                    \n                        (0%)'}))
 assert result['ok'],result
 assert result['rows'][0]['post_holding']==0
 assert result['rows'][0]['ownership_change_pct'] is None
 assert result['rows'][0]['trade_id']==parse_pasted(export_paste(**{'Post Transaction Holding':'0'}))['rows'][0]['trade_id']

def test_holding_percentage_does_not_change_quantity():
 result=parse_pasted(export_paste(**{'Post Transaction Holding':'12,345\n (1.25%)'}))
 assert result['ok'];assert result['rows'][0]['post_holding']==12345

@pytest.mark.parametrize('value',['0 (unknown)','0 (0%) trailing','100 shares','0\n200'])
def test_malformed_holdings_still_fail(value):
 assert not parse_pasted(export_paste(**{'Post Transaction Holding':value}))['ok']

def test_unknown_standard_code_still_rejected():
 assert not parse_pasted(paste({'Trade Type':''}))['ok']
 assert not parse_pasted(export_paste(Action='Unrecognised action text'))['ok']

def test_unknown_action_gateway(tmp_path,monkeypatch):
 from institutional_warehouse import db
 monkeypatch.setenv('INSTITUTIONAL_WAREHOUSE_ROOT',str(tmp_path))
 monkeypatch.delenv('WAREHOUSE_DATABASE_URL',raising=False);monkeypatch.delenv('INSTITUTIONAL_WAREHOUSE_DATABASE_URL',raising=False)
 monkeypatch.setattr(db,'_BACKEND',None);monkeypatch.setattr(db,'_INITIALISED',False)
 result=import_pasted(export_paste(Action='',**{'Post Transaction Holding':'0\n (0%)'}));assert result['ok'],result
 row=db.query('SELECT * FROM wh_us_insider_trades')[0]
 assert row['transaction_code']=='UNKNOWN' and row['is_purchase_sale']=='false' and row['post_holding']==0
 if db._BACKEND:db._BACKEND.close()
