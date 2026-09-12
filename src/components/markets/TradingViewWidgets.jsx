import { useEffect, useRef, memo } from "react";

function useTradingViewEmbed(scriptSrc, config, deps = []) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.innerHTML = "";
    const widgetDiv = document.createElement("div");
    widgetDiv.className = "tradingview-widget-container__widget";
    container.appendChild(widgetDiv);

    const script = document.createElement("script");
    script.src = scriptSrc;
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify(config);
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return containerRef;
}

export const TradingViewFinancials = memo(function TradingViewFinancials({ symbol = "NSE:HDFCBANK" }) {
  const tvSymbol = symbol.includes(":") ? symbol : `NSE:${symbol}`;
  const ref = useTradingViewEmbed(
    "https://s3.tradingview.com/external-embedding/embed-widget-financials.js",
    {
      symbol: tvSymbol,
      colorTheme: "light",
      displayMode: "regular",
      isTransparent: false,
      locale: "en",
      width: "100%",
      height: 550,
    },
    [tvSymbol]
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      <div className="border-b border-slate-100 px-6 py-4">
        <h3 className="text-base font-semibold text-slate-900">Fundamentals</h3>
        <p className="text-sm text-slate-500 mt-0.5">{tvSymbol.replace(":", " · ")}</p>
      </div>
      <div className="tradingview-widget-container w-full" ref={ref} style={{ height: 550 }} />
    </div>
  );
});

export const TradingViewHeatmap = memo(function TradingViewHeatmap() {
  const ref = useTradingViewEmbed(
    "https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js",
    {
      dataSource: "SENSEX",
      blockSize: "market_cap_basic",
      blockColor: "change",
      grouping: "sector",
      locale: "en",
      symbolUrl: "",
      colorTheme: "light",
      exchanges: [],
      hasTopBar: false,
      isDataSetEnabled: false,
      isZoomEnabled: true,
      hasSymbolTooltip: true,
      isMonoSize: false,
      width: "100%",
      height: 600,
    },
    []
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      <div className="border-b border-slate-100 px-6 py-4">
        <h3 className="text-base font-semibold text-slate-900">Market Heatmap</h3>
        <p className="text-sm text-slate-500 mt-0.5">SENSEX · sector view</p>
      </div>
      <div className="tradingview-widget-container w-full" ref={ref} style={{ height: 600 }} />
    </div>
  );
});

export function TradingViewMarketOverview() {
  const containerRef = useRef(null);

  useEffect(() => {
    if (document.querySelector('script[src*="tv-market-overview.js"]')) return;

    const script = document.createElement("script");
    script.type = "module";
    script.src = "https://widgets.tradingview-widget.com/w/en/tv-market-overview.js";
    script.async = true;
    document.body.appendChild(script);
  }, []);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      <div className="border-b border-slate-100 px-6 py-4">
        <h3 className="text-base font-semibold text-slate-900">Market Movers</h3>
        <p className="text-sm text-slate-500 mt-0.5">BSE · top gainers & losers</p>
      </div>
      <div ref={containerRef} className="p-4 min-h-[420px]">
        <tv-market-overview exchange="BSE" mode="market-movers" />
      </div>
    </div>
  );
}
