import useMarketIntelligence from '@/hooks/useMarketIntelligence';

function sentimentTone(sentiment = '') {
  const value = sentiment.toLowerCase();
  if (value.includes('bearish')) return 'text-[#b42318]';
  if (value.includes('bullish')) return 'text-[#087443]';
  return 'text-[#966a00]';
}

function TickerItem({ item }) {
  return (
    <div className="flex items-center gap-2 shrink-0 pr-8">
      <span className="text-[10px] font-bold tracking-[0.08em] uppercase text-[#5d6470]">{item.label}</span>
      <span className={`text-[11px] font-bold ${sentimentTone(item.sentiment)}`}>
        {item.sentiment}
      </span>
      {item.strength && <span className="text-[10px] text-[#9298a3]">· {item.strength}</span>}
    </div>
  );
}

const PENDING_INDICES = [
  'Nifty 50',
  'Sensex',
  'Bank Nifty',
  'Fin Nifty',
  'Nifty Midcap',
  'Nifty Smallcap',
  'Nifty IT',
  'Nifty Auto',
  'Nifty Pharma',
  'Nifty PSU Bank',
  'Nifty Realty',
  'Nifty FMCG',
  'Nifty Metal',
];

/**
 * Moving, compliance-safe ticker: it intentionally contains model labels only,
 * never exchange prices, daily change or live volume.
 */
export default function IndexSentimentTicker() {
  const { indexSentiments, loading } = useMarketIntelligence();
  const items = indexSentiments?.length
    ? indexSentiments
    : PENDING_INDICES.map((label) => ({
        key: label.toLowerCase().replace(/\s+/g, '-'),
        label,
        sentiment: loading ? 'Calculating' : 'Sync pending',
        strength: 'AGI model',
      }));
  const loop = [...items, ...items];

  return (
    <section className="border-y border-[#dfe3e8] bg-[#f8fafb] overflow-hidden" aria-label="AGI index sentiment ticker">
      <div className="max-w-[1600px] mx-auto flex">
        <div className="hidden md:flex shrink-0 items-center px-4 border-r border-[#dfe3e8] bg-white">
          <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#252b36]">AGI Index Signals</span>
        </div>
        <div className="agi-sentiment-ticker flex-1 min-w-0 py-2.5">
          <div className="agi-sentiment-ticker-track">
            {loop.map((item, index) => <TickerItem key={`${item.key}-${index}`} item={item} />)}
          </div>
        </div>
      </div>
    </section>
  );
}
