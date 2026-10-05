import research from '@/data/portfolioResearch.json';

export default function PortfolioResearch({ portfolio }) {
  if (portfolio.market === 'usa' && portfolio.id === 'us-top10' && portfolio.customized && !portfolio.incomplete) return <section className="pf-research" aria-labelledby="portfolio-research-heading">
    <span className="pf-eyebrow">AGI RESEARCH · 2026-10-02</span>
    <h2 id="portfolio-research-heading">Why this portfolio?</h2>
    <p>AGI independently selected a concentrated quality-growth basket for a 3–5-year research horizon. Microsoft, Alphabet, Amazon and Nvidia provide cloud and AI exposure; Visa, JPMorgan and Berkshire broaden the business mix; Lilly, GE Aerospace and Costco add healthcare, aerospace and consumer exposure.</p>
    <p>The initial allocation totals 100%. Weights are research judgments, not an optimised portfolio. The four cloud and AI names account for 38% of the initial allocation and share spending-cycle risk. Ten stocks remain a concentrated, aggressive equity portfolio.</p>
    <p>Selection considered operating growth, cash generation and business durability. Investment gains can distort reported earnings; valuation comparisons should use normalised operating results. Current valuation comparisons are incomplete, particularly before making any investment decision.</p>
    <p>Review after quarterly results. Record any allocation changes and their rationale. The historical comparisons above use current holdings with hindsight; they are not an independently validated selection strategy or returns earned since launch.</p>
    <p className="pf-footnote">This rationale describes the 2 October 2026 selection. Subsequent holding edits require a fresh research review. It replaces the earlier partially disclosed reference basket.</p>
  </section>;
  const review = portfolio.market === 'usa' && research.portfolios[portfolio.id];
  if (!review) return null;
  return <section className="pf-research" aria-labelledby="portfolio-research-heading">
    <div className="pf-heading"><div><span className="pf-eyebrow">AGI RESEARCH · {research.asOf}</span>
      <h2 id="portfolio-research-heading">More names to research</h2>
      <p>Based on the original {review.name} strategy. Candidates have no assigned weights and are not portfolio holdings.</p>
    </div></div>
    {portfolio.customized && <p className="pf-warning">You have customised this portfolio. Recheck these candidates against your current strategy before using them.</p>}
    <p>{review.note}</p>
    <p className="pf-footnote">{research.status}. Business fit and risks are AGI research judgments. Filing evidence establishes dated ownership, not a manager’s investment thesis.</p>
    <div className="pf-research-grid">{review.symbols.map(symbol => {
      const stock = research.securities[symbol];
      const overlap = Object.values(research.portfolios).filter(p => p.symbols.includes(symbol) && p !== review).map(p => p.name);
      return <article className="pf-research-card" key={symbol}>
        <span className="pf-research-symbol">{symbol}</span><h3>{stock.name}</h3>
        <p>{stock.fit}</p>
        <dl><dt>Evidence</dt><dd>{stock.evidence}</dd><dt>Main risk</dt><dd>{stock.risk}</dd></dl>
        <details><summary>Before adding this name</summary><p>{stock.reviewGate}</p>
          {overlap.length > 0 && <p>Also shortlisted for: {overlap.join(', ')}. Repeated names increase combined exposure.</p>}
        </details>
        <div className="pf-research-sources">{stock.sources.map((url, i) => <a key={url} href={url} target="_blank" rel="noreferrer">{stock.sources.length > 1 ? `Source ${i + 1}` : 'Read source'} ↗</a>)}</div>
      </article>;
    })}</div>
    <p><a href="/research/portfolio-expansion-2026-10-02.html" target="_blank" rel="noreferrer">Read the full 26-portfolio research report ↗</a></p>
    <p className="pf-footnote">A strategy-fit shortlist, not an exhaustive screen or a buy recommendation. No target prices, proposed allocations or portfolio returns have been calculated.</p>
  </section>;
}
