import csv,io,json
import pytest
from financial_warehouse_completion.institutions import parse,publish,current
HEADER=['Superstar','Portfolio Value *\n(change)','#Of Stocks','Sector Preference','Quarterly Net Worth','Top Holdings','Recently bought','Recently sold','']
def paste(country='IN',**changes):
 row=dict(zip(HEADER,['Mukesh Ambani and Family' if country=='IN' else 'Warren Buffett','334,805.84 Cr\n↓ -5.62%' if country=='IN' else '313,025.25 M\n↑ 2.29%','2' if country=='IN' else '32','Banking & Finance (31.57%) ↑\nTelecom Equipment (24.64%) ↑','','Reliance (307,977.16 Cr)' if country=='IN' else 'Apple (76,562.15 M)\nAMEX (46,341.33 M)','-' if country=='IN' else 'Delta Air Lines ↑ 2.6627%','Jio Financial ↓ -0.78%' if country=='IN' else 'DaVita ↓ -1.73952%','']))
 row.update(changes);out=io.StringIO();w=csv.writer(out,delimiter='\t');w.writerow(HEADER);w.writerow([row[h] for h in HEADER]);return out.getvalue()
@pytest.mark.parametrize('country,value,change,stocks',[('IN',334805.84,-5.62,2),('US',313025.25,2.29,32)])
def test_screenshot_formats(country,value,change,stocks):
 r=parse(paste(country),country);assert r['ok'],r
 x=r['rows'][0];assert (x['value'],x['change'],x['stocks'])==(value,change,stocks)
 assert len(x['sectors'])==2 and x['quarterlyNetWorth'] is None

def test_wrong_currency_and_unknown_market_rejected():
 assert not parse(paste('US'),'IN')['ok'];assert not parse(paste(),'XX')['ok']

def test_links_and_markdown():
 s='| Superstar | Portfolio Value * (change) | #Of Stocks | Sector Preference | Quarterly Net Worth | Top Holdings | Recently bought | Recently sold |\n|---|---|---|---|---|---|---|---|\n| [Investor](https://example.com/investor) | **100 Cr**<br>+2% | 2 | Banking<br>Software | | [Company](https://example.com/company) | - | - |'
 r=parse(s);assert r['ok'],r;assert r['rows'][0]['url']=='https://example.com/investor';assert len(r['rows'][0]['sectors'])==2
 assert not parse(s.replace('https://example.com/investor','javascript:alert'))['ok']

def test_duplicate_conflict_and_empty_rejected():
 a=paste();row=a.splitlines() # use csv to preserve multiline cells
 table=list(csv.reader(io.StringIO(a),delimiter='\t'))
 out=io.StringIO();w=csv.writer(out,delimiter='\t');w.writerows([*table,table[1]])
 r=parse(out.getvalue());assert r['ok'] and r['duplicate_rows']==1
 table[1][1]='123 Cr';w.writerow(table[1]);assert not parse(out.getvalue())['ok']
 assert not parse('')['ok']

@pytest.mark.parametrize('change',[{'#Of Stocks':'1.5'},{'Portfolio Value *\n(change)':'NaN Cr'},{'Portfolio Value *\n(change)':'100 M'},{'Superstar':''}])
def test_invalid_rows(change):assert not parse(paste(**change))['ok']

def test_missing_change_not_zero():
 r=parse(paste(**{'Portfolio Value *\n(change)':'100 Cr'}));assert r['ok'];assert r['rows'][0]['change'] is None

def test_atomic_publication_country_isolation_and_failed_batch(tmp_path,monkeypatch):
 from institutional_warehouse import db
 monkeypatch.setenv('INSTITUTIONAL_WAREHOUSE_ROOT',str(tmp_path));monkeypatch.delenv('WAREHOUSE_DATABASE_URL',raising=False);monkeypatch.delenv('INSTITUTIONAL_WAREHOUSE_DATABASE_URL',raising=False)
 monkeypatch.setattr(db,'_BACKEND',None);monkeypatch.setattr(db,'_INITIALISED',False)
 assert current('IN')['published'] is False
 assert publish(paste(),'IN')['ok'];assert publish(paste('US'),'US')['ok']
 original=current('IN');assert len(original['rows'])==1
 assert publish(paste(**{'Superstar':'New Investor'}),'IN','2026-09-26')['ok']
 assert current('IN')['rows'][0]['name']=='New Investor'
 assert current('US')['rows'][0]['name']=='Warren Buffett'
 assert not publish(paste(**{'#Of Stocks':'bad'}),'IN')['ok']
 assert current('IN')['rows'][0]['name']=='New Investor'
 assert len(db.query('SELECT * FROM wh_institution_snapshots'))==2
 if db._BACKEND:db._BACKEND.close()
