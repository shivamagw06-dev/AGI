import unittest
from options_lab.technical_chart import chart_payload
from options_lab.regime_agents import indicators

class ChartTests(unittest.TestCase):
    def test_bounded_and_matches_engine(self):
        bars=[dict(at=1800000000+i*300,open=100+i,high=102+i,low=99+i,close=101+i) for i in range(100)]
        payload=chart_payload({'research':{'candles':bars},'last_at':'now'})
        self.assertEqual(len(payload['candles']),100)
        self.assertEqual(payload['candles'][-1]['ema20'],indicators(bars)['ema20'])
        self.assertNotIn('ema50',payload['candles'][48])
        self.assertFalse(payload['volume_available'])
    def test_empty(self):
        self.assertEqual(chart_payload({})['candles'],[])
