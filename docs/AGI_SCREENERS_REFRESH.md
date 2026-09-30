# AGI screener refresh policy

AGI does not import Trendlyne's screen results. It calculates its own screens from licensed/connected inputs. The by-type page currently ships **NSE universe**, **market activity**, and **published AGI research** screens.

| Screen family | Input | Refresh | Current state |
| --- | --- | --- | --- |
| NSE equity list | Upstox NSE BOD instruments, filtered to `NSE_EQ` + `EQ` | Daily after 16:15 IST on NSE trading days; also refreshed on demand after 24 hours | Implemented in this PR |
| Price, daily change, share volume | Upstox V3 quote snapshots, in batches of 150 | Cached at most 15 minutes during use; forced post-close refresh at 16:15 IST | Implemented when an analytics/access token and quotes are available |
| AGI sentiment, score, confidence, research factors | Current published Nifty 500 research run | Independent research publication schedule; API cache up to 30 minutes | Published subset only |
| Fundamental ratios | Statements/key ratios; fiscal-period comparisons | On new company filing or successful refresh, not every trading day | Not yet exposed as screener rules |
| Shareholding changes | Exchange filings/shareholding disclosures | Quarterly or on new filing, not daily | Not yet exposed as screener rules |
| RSI/MACD, moving averages, candlestick patterns | Complete, adjusted daily OHLCV history | Compute after each completed trading session | Not yet exposed; requires full-universe history, corporate-action handling, and data-quality checks |

The Node API scheduler retries incomplete post-close refreshes every 15 minutes within the 16:15–16:59 IST window. It records the last result in process memory. If the server restarts, the page's on-demand cache refresh remains the fallback. Displayed timestamps and quote counts tell readers whether data is current; missing quotes never qualify for price/volume screens. Research values are never inferred for uncovered stocks.

The configured token permits read-only API calls; it does not itself establish permission to redistribute exchange quote data on a public site. Confirm the applicable public-display and redistribution terms before relying on those quotes for a public product.

Before exposing further Trendlyne-like screen families, add a durable per-symbol daily data store, sufficient lookback, corporate-action adjustments, input coverage checks, and a last-successful-session date for each rule. Do not present a screen as refreshed if its inputs are incomplete.
