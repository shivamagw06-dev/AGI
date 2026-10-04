# US portfolio logos

The US portfolio UI uses 266 bundled SVG logos covering the 267 distinct holding names in the 26 public US portfolios captured on 5 October 2026. Two names refer to GE Aerospace. Logo changes do not change holdings, weights, ticker mappings used for returns, or prices.

`src/data/usCompanyLogos.json` records each asset source, matched instrument and exact holding-name alias. Existing reviewed Yahoo instrument mappings supplied the lookup tickers. TradingView's America scanner matched the ticker to its company/fund name and logo ID; images were downloaded from its symbol-logo CDN. Honeywell Aerospace's logo comes directly from its official website. ETFs display their fund/provider identity, not a made-up operating-company logo.

Images are bundled at build time; visitors do not call an external logo service. The India and US namespaces are separate to avoid ticker collisions. Explicit tickers take precedence over exact-name aliases. Unknown future holdings or failed images retain the initial-letter fallback. Update the manifest and asset set when adding new holdings.

Validation: every current US holding resolves to a nonempty valid SVG, all SVGs are checked for scripts/foreignObject/event-handler attributes, and names/instruments were reviewed for matching issuer identities. UI coverage includes the USA overview preview, portfolio cards, allocation tables and stock-by-stock historical return tables.
