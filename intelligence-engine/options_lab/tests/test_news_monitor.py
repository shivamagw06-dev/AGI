import copy,json,sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from options_lab import news_monitor as n, paper_agents as p
NOW=datetime(2026,9,29,5,0,tzinfo=timezone.utc)
KEY='NSE_EQ|INE002A01018'
def item(at=NOW,heading='RBI announces emergency rate hike',url='https://upstox.com/news/test/article-1/'):
    return dict(heading=heading,article_link=url,published_time=at.timestamp()*1000)
def snapshot():
    articles=n.normalize([(KEY,item())],{KEY:'RELIANCE'},NOW)
    articles[0]['first_seen_at']=NOW.isoformat()
    return dict(available=True,last_success_at=NOW.isoformat(),articles=articles)
class NewsTests(unittest.TestCase):
    def test_dedup_dates_and_safe_links(self):
        items=[(KEY,item()),('other',item(url=item()['article_link']+'?utm=x')),(KEY,item(NOW+timedelta(seconds=1))),(KEY,item(NOW-timedelta(days=8))),(KEY,item(url='javascript:alert(1)'))]
        articles=n.normalize(items,{KEY:'RELIANCE','other':'HDFCBANK'},NOW)
        self.assertEqual(len(articles),1)
        self.assertEqual(articles[0]['symbols'],['RELIANCE','HDFCBANK'])
        self.assertEqual(articles[0]['reasons'],['Monetary policy'])
    def test_freshness_first_seen_and_old_headlines(self):
        s=snapshot();self.assertTrue(n.assessment(s,NOW)['would_pause'])
        self.assertIsNone(n.assessment(s,NOW+timedelta(seconds=181))['would_pause'])
        s['last_success_at']=(NOW+timedelta(hours=1)).isoformat()
        self.assertFalse(n.assessment(s,NOW+timedelta(hours=1))['would_pause'])
        self.assertIsNone(n.assessment(snapshot(),NOW-timedelta(seconds=1))['would_pause'])
        s=snapshot();s['available']=False
        self.assertIsNone(n.assessment(s,NOW)['would_pause'])
    def test_batches_and_pagination_fail_closed(self):
        calls=[]
        def get(url,token):
            query=n.urllib.parse.parse_qs(n.urllib.parse.urlsplit(url).query);calls.append(query)
            return dict(status='success',data={},metadata={'page':{'page_number':int(query['page_number'][0]),'total_pages':2}})
        n.fetch_news([str(i) for i in range(50)],'never-print',get)
        self.assertEqual(len(calls),4)
        self.assertEqual(len(calls[0]['instrument_keys'][0].split(',')),30)
        self.assertEqual(len(calls[2]['instrument_keys'][0].split(',')),20)
        with self.assertRaises(ValueError):n.fetch_news([KEY],'token',lambda *args:dict(status='success',data={},metadata={'page':{'page_number':1,'total_pages':11}}))
    def test_observer_never_changes_state_and_marks_do_not_duplicate(self):
        db=sqlite3.connect(':memory:');n.schema(db)
        db.execute('INSERT INTO paper_news_status VALUES(1,?)',(json.dumps(snapshot()),))
        state=p.fresh_state();before=n.capture(state)
        state['agents']['opening_range']['position']={'entry_at':NOW.isoformat(),'mark':1}
        original=copy.deepcopy(state)
        n.observe(db,state,before,NOW);n.observe(db,state,before,NOW+timedelta(seconds=1))
        self.assertEqual(state,original)
        self.assertEqual(db.execute('SELECT count(*) FROM paper_news_observations').fetchone()[0],1)
        before=n.capture(state);state['agents']['opening_range']['position']['mark']=2
        n.observe(db,state,before,NOW+timedelta(seconds=2))
        self.assertEqual(db.execute('SELECT count(*) FROM paper_news_observations').fetchone()[0],1)
        evidence=json.loads(db.execute('SELECT payload FROM paper_news_observations').fetchone()[0])
        self.assertTrue(evidence['would_pause']);self.assertFalse(evidence['execution_changed'])
        self.assertEqual(len(evidence['headlines']),1);db.close()
    def test_poll_preserves_first_seen_and_failure_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'UPSTOX_ACCESS_TOKEN':'test'}):
            with patch.object(p,'paths',return_value=(Path(tmp)/'source',Path(tmp)/'paper.sqlite3')):
                response=dict(status='success',data={KEY:[item()]},metadata={'page':{'page_number':1,'total_pages':1}})
                first=n.poll({KEY:'RELIANCE'},'test',now=NOW,get=lambda *args:response)
                second=n.poll({KEY:'RELIANCE'},'test',now=NOW+timedelta(seconds=60),get=lambda *args:response)
                self.assertEqual(first['articles'][0]['first_seen_at'],second['articles'][0]['first_seen_at'])
                def broken(*args):raise TimeoutError('a secret must never appear')
                failed=n.poll({KEY:'RELIANCE'},'test',now=NOW+timedelta(seconds=120),get=broken)
                self.assertIsNone(n.assessment(failed,NOW+timedelta(seconds=120))['would_pause'])
                self.assertNotIn('secret',failed['error']);self.assertEqual(failed['last_success_at'],second['last_success_at'])
    def test_bundled_watchlist_is_fifty_unique_keys(self):
        self.assertEqual(len(n.instruments((Path(n.__file__).parent/'data/nifty50_news_watchlist.csv').read_text())),50)
if __name__=='__main__':unittest.main()

class TransportTests(unittest.TestCase):
    def test_transport_uses_bearer_without_redirects_and_bounds_body(self):
        from unittest.mock import MagicMock
        response=MagicMock();response.status_code=200
        response.__enter__.return_value=response
        response.iter_content.return_value=[b'{"status":"success"}']
        with patch('requests.get',return_value=response) as get:
            self.assertEqual(n.read_json('https://api.upstox.com/v2/news','private')['status'],'success')
            self.assertFalse(get.call_args.kwargs['allow_redirects'])
            self.assertTrue(get.call_args.kwargs['stream'])
        response.iter_content.return_value=[b'x'*2_000_001]
        with patch('requests.get',return_value=response),self.assertRaises(ValueError):
            n.read_json('https://api.upstox.com/v2/news','private')
