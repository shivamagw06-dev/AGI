import json
from datetime import datetime, timezone
import pytest
from financial_warehouse_completion.website_analytics import clean, collect, report, summarize, connection
from financial_warehouse_completion.tests.test_investor_mapping import isolated_db

def payload(**kwargs):
 return dict(id='a'*20,visitor='v'*20,session='s'*20,event='page_view',path='/institutions?secret=x',referrer='google.com',device='Desktop',**kwargs)

def test_minimizes_payload():
 p=payload();p.update(email='private@example.com',ip='127.0.0.1')
 r=clean(p);assert r['path']=='/institutions';assert 'email' not in r and 'ip' not in r
 p['path']='/portfolio/private-person';assert clean(p)['path']=='/portfolio'
 for path in ['/admin/test','https://evil.test','/x@example.com']:
  p['path']=path
  with pytest.raises(ValueError):clean(p)

def test_durable_idempotent_events(isolated_db):
 collect(payload());collect(payload())
 with connection() as db: assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0]==1
 assert report(1)['pageviews']==1
 # A conflicting retry cannot change the original stored event.
 p=payload();p['event']='model_download';collect(p)
 assert report(1)['downloads']==0

def test_ist_boundaries_unique_visitors_sessions_and_events():
 now=datetime(2026,9,27,1,tzinfo=timezone.utc)
 def row(at,session='s'*20,event='page_view',visitor='v'*20):
  p=payload();p.update(session=session,event=event,visitor=visitor)
  return {'received_at':at,'event_json':json.dumps(clean(p))}
 rows=[row('2026-09-26T18:29:00+00:00'),row('2026-09-26T18:31:00+00:00'),row('2026-09-27T00:30:00+00:00',session='t'*20),row('2026-09-27T00:31:00+00:00',event='model_download'),row('2026-09-27T00:32:00+00:00',event='signup_completed')]
 r=summarize(rows,1,now)
 assert (r['pageviews'],r['visitors'],r['visits'],r['repeatVisitors'],r['downloads'],r['signups'])==(2,1,2,1,1,1)
 assert r['daily']==[{'date':'2026-09-27','views':2}]
