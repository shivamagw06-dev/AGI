import { useEffect, useMemo, useRef, useState } from 'react';
import './tradingViewUsDesk.css';

const TABS = [
  { id: 'map', label: 'Market map', note: 'S&P 500 leadership' },
  { id: 'screener', label: 'US screener', note: 'Fundamental + technical' },
  { id: 'research', label: 'Chart research', note: 'Price, signals + news' },
];

const EXCHANGES = ['NASDAQ', 'NYSE', 'AMEX'];

function cleanSymbol(value) {
  return String(value || 'AAPL')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9.-]/g, '')
    .replace('-', '.') || 'AAPL';
}

function TradingViewEmbed({ scriptSrc, config, height = 520, label }) {
  const containerRef = useRef(null);
  const configKey = JSON.stringify(config);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    container.innerHTML = '<div class="tradingview-widget-container__widget"></div>';
    const script = document.createElement('script');
    script.src = scriptSrc;
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = configKey;
    container.appendChild(script);

    return () => {
      container.innerHTML = '';
    };
  }, [scriptSrc, configKey]);

  return (
    <div
      ref={containerRef}
      className="tradingview-widget-container tvus-widget-frame"
      style={{ minHeight: height }}
      aria-label={label}
    />
  );
}

function WidgetCard({ eyebrow, title, description, children, className = '' }) {
  return (
    <article className={'tvus-card ' + className}>
      <header className="tvus-card__header">
        <div>
          <span className="tvus-card__eyebrow">{eyebrow}</span>
          <h3>{title}</h3>
        </div>
        <span className="tvus-card__source">TRADINGVIEW</span>
      </header>
      {description ? <p className="tvus-card__description">{description}</p> : null}
      <div className="tvus-card__body">{children}</div>
      <a
        className="tvus-attribution"
        href="https://www.tradingview.com/"
        target="_blank"
        rel="noopener nofollow"
      >
        Market display by TradingView
      </a>
    </article>
  );
}

export default function TradingViewUsDesk() {
  const [activeTab, setActiveTab] = useState('map');
  const [exchange, setExchange] = useState('NASDAQ');
  const [draftSymbol, setDraftSymbol] = useState('AAPL');
  const [symbol, setSymbol] = useState('AAPL');
  const tvSymbol = exchange + ':' + symbol;

  const advancedChart = useMemo(() => ({
    autosize: true,
    symbol: tvSymbol,
    interval: 'D',
    timezone: 'America/New_York',
    theme: 'light',
    backgroundColor: 'rgba(255, 255, 255, 1)',
    gridColor: 'rgba(226, 235, 239, 0.7)',
    style: '1',
    locale: 'en',
    allow_symbol_change: true,
    calendar: false,
    hide_side_toolbar: false,
    withdateranges: true,
    details: true,
    hotlist: false,
  }), [tvSymbol]);

  const technicalAnalysis = useMemo(() => ({
    interval: '1D',
    width: '100%',
    isTransparent: true,
    height: 450,
    symbol: tvSymbol,
    showIntervalTabs: true,
    displayMode: 'multiple',
    locale: 'en',
    colorTheme: 'light',
  }), [tvSymbol]);

  const fundamentalData = useMemo(() => ({
    symbol: tvSymbol,
    colorTheme: 'light',
    isTransparent: true,
    largeChartUrl: '',
    displayMode: 'regular',
    width: '100%',
    height: 520,
    locale: 'en',
  }), [tvSymbol]);

  const topStories = useMemo(() => ({
    feedMode: 'symbol',
    symbol: tvSymbol,
    colorTheme: 'light',
    isTransparent: true,
    displayMode: 'regular',
    width: '100%',
    height: 520,
    locale: 'en',
  }), [tvSymbol]);

  const applySymbol = (event) => {
    event.preventDefault();
    setSymbol(cleanSymbol(draftSymbol));
  };

  return (
    <section className="tvus-suite" aria-labelledby="tvus-title">
      <div className="tvus-suite__glow tvus-suite__glow--one" aria-hidden="true" />
      <div className="tvus-suite__glow tvus-suite__glow--two" aria-hidden="true" />

      <header className="tvus-suite__header">
        <div>
          <span className="tvus-suite__kicker">INDEPENDENT MARKET LAYER</span>
          <h2 id="tvus-title">Visual US market intelligence</h2>
          <p>
            Explore leadership, screen the full US universe and inspect a company
            without replacing AGI's evidence, rankings or investment conclusions.
          </p>
        </div>
        <div className="tvus-suite__status">
          <span className="tvus-suite__status-dot" />
          Delayed exchange display
        </div>
      </header>

      <nav className="tvus-tabs" aria-label="TradingView intelligence tools">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={'tvus-tab ' + (activeTab === tab.id ? 'tvus-tab--active' : '')}
            onClick={() => setActiveTab(tab.id)}
            aria-pressed={activeTab === tab.id}
          >
            <span>{tab.label}</span>
            <small>{tab.note}</small>
          </button>
        ))}
      </nav>

      {activeTab === 'map' ? (
        <WidgetCard
          eyebrow="MARKET LEADERSHIP"
          title="S&P 500 sector heatmap"
          description="Tile size represents market capitalization; color shows the latest daily move. Zoom into sectors and inspect individual constituents."
          className="tvus-card--feature"
        >
          <TradingViewEmbed
            scriptSrc="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js"
            height={610}
            label="S&P 500 stock heatmap"
            config={{
              dataSource: 'SPX500',
              blockSize: 'market_cap_basic',
              blockColor: 'change',
              grouping: 'sector',
              locale: 'en',
              symbolUrl: '',
              colorTheme: 'light',
              exchanges: [],
              hasTopBar: true,
              isDataSetEnabled: false,
              isZoomEnabled: true,
              hasSymbolTooltip: true,
              isMonoSize: false,
              width: '100%',
              height: 610,
            }}
          />
        </WidgetCard>
      ) : null}

      {activeTab === 'screener' ? (
        <WidgetCard
          eyebrow="DISCOVERY"
          title="Full US stock screener"
          description="Sort the US universe by price, performance, valuation, dividends and technical conditions. Use it for discovery, then return to AGI for evidence-led analysis."
          className="tvus-card--feature"
        >
          <TradingViewEmbed
            scriptSrc="https://s3.tradingview.com/external-embedding/embed-widget-screener.js"
            height={650}
            label="US stock screener"
            config={{
              width: '100%',
              height: 650,
              defaultColumn: 'overview',
              defaultScreen: 'most_capitalized',
              market: 'us',
              showToolbar: true,
              colorTheme: 'light',
              isTransparent: true,
              locale: 'en',
            }}
          />
        </WidgetCard>
      ) : null}

      {activeTab === 'research' ? (
        <div className="tvus-research">
          <form className="tvus-symbol-bar" onSubmit={applySymbol}>
            <div>
              <span className="tvus-suite__kicker">SYMBOL WORKBENCH</span>
              <strong>{tvSymbol}</strong>
            </div>
            <div className="tvus-symbol-bar__controls">
              <label>
                <span>Exchange</span>
                <select value={exchange} onChange={(event) => setExchange(event.target.value)}>
                  {EXCHANGES.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label>
                <span>US ticker</span>
                <input
                  value={draftSymbol}
                  onChange={(event) => setDraftSymbol(event.target.value)}
                  placeholder="AAPL"
                  inputMode="text"
                />
              </label>
              <button type="submit">Open research</button>
            </div>
          </form>

          <div className="tvus-research__grid">
            <WidgetCard
              eyebrow="PRICE BEHAVIOR"
              title={symbol + ' advanced chart'}
              description="Interactive price history, comparisons, drawing tools and technical indicators."
              className="tvus-card--chart"
            >
              <TradingViewEmbed
                scriptSrc="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
                config={advancedChart}
                height={570}
                label={symbol + ' advanced chart'}
              />
            </WidgetCard>

            <WidgetCard
              eyebrow="TECHNICAL STATE"
              title="Multi-horizon signal summary"
              description="A TradingView oscillator and moving-average consensus, shown separately from AGI's proprietary signals."
            >
              <TradingViewEmbed
                scriptSrc="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js"
                config={technicalAnalysis}
                height={450}
                label={symbol + ' technical analysis'}
              />
            </WidgetCard>

            <WidgetCard
              eyebrow="FUNDAMENTALS"
              title="Financial overview"
              description="A secondary reference for operating performance and valuation, not AGI's canonical research warehouse."
            >
              <TradingViewEmbed
                scriptSrc="https://s3.tradingview.com/external-embedding/embed-widget-financials.js"
                config={fundamentalData}
                height={520}
                label={symbol + ' fundamental data'}
              />
            </WidgetCard>

            <WidgetCard
              eyebrow="MARKET NARRATIVE"
              title="Latest company stories"
              description="Recent symbol-linked market coverage for context around price moves and catalysts."
            >
              <TradingViewEmbed
                scriptSrc="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js"
                config={topStories}
                height={520}
                label={symbol + ' top stories'}
              />
            </WidgetCard>
          </div>
        </div>
      ) : null}

      <footer className="tvus-suite__footer">
        TradingView widgets are an external display layer. US exchange data may be delayed,
        cannot be exported into AGI's warehouse and does not alter AGI research conclusions.
      </footer>
    </section>
  );
}
