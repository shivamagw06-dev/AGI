# INDstocks Live Alpha connection

IND_API is a server-only access token. When present, Live Alpha distributes NSE cash one-minute history requests deterministically across Upstox, Groww and INDstocks. Existing Upstox live WebSocket quotes remain the primary stream; this integration is candle-history load sharing, not an INDstocks WebSocket connection. Index/futures requests remain Upstox until independently mapped.

INDstocks equity master maps NSE EQ securities using exact ISIN, rejects ambiguous IDs and caches the mapping for one day. Minute windows are paged at seven days and require genuine timestamped OHLCV. No price synthesis, order execution, signal-rule change or retrospective publication is introduced. Existing bootstrap rejects incomplete/current bars.

Requests are serialized at least 350ms apart (under 3/sec), with a local 50,000/day process budget. 429 pauses INDstocks for one minute; 401/403 pauses it for 30 minutes. Other providers are attempted on failure. These limits apply to this process, not unrelated clients using the same account. Tokens expire daily; replace IND_API and deploy after renewal. A missing/expired token must never be described as connected.

`/api/market/live-alpha/status` history routing includes successful series counts and sanitized INDstocks HTTP health. HTTP success alone does not prove a valid candle series: use the indstocks series count as well. Provider state contains no tokens.

Sources: https://api-docs.indstocks.com/historicalData/ and https://api-docs.indstocks.com/instruments/ . Actual equity CSV tested on 8 October includes ISIN despite the abbreviated documentation schema.

Validation: 15 targeted tests for mapping, timestamps, malformed data, paging, request spacing, authentication cooldown, three-provider routing, fallback and bootstrap regression. Read-only Render probes verified quote HTTP 200 and real one-minute candles before integration.
