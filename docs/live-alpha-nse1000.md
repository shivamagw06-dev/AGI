# AGI NSE 1,000 — 8 October 2026

Default universe expands to 1,000: all existing 500 plus 500 additional NSE EQ company stocks ranked by average daily traded value over Sep 30 and Oct 1, 5, 6, 7. Every addition traded on all five sessions and matches both ISIN and symbol in the current Upstox NSE equity master. Excludes non-EQ series and non-INE instruments (funds/bonds). The last addition averaged INR 78,217,968.29 traded daily. This is not a market-cap top 1,000 or official Nifty index.

The frozen additions JSON retains source URLs, source hashes and average traded value; scripts/live-alpha/build-1000.py reproduces it from the downloads. The list is reviewed and static, not automatically refreshed. Market data updates live. Additions use an explicitly labelled MARKET_PROXY / Nifty 50 benchmark until verified sector classifications are available; pipeline flags these as sector proxies rather than sector-specific evidence.

Current master resolves 213 futures underlyings across these stocks; 1,000 equities plus futures and indices are below the existing 1,500-key feed guard. No added WebSocket connection or instance upgrade. Existing spread, history, volume and freshness rules remain. The global 80% complete-history gate now requires 800 eligible observations, so evaluations can be withheld during expansion warm-up. New volume baselines fetch at a bounded rate in the background; history is never fabricated. Baseline storage and snapshot traffic increase with coverage.

Provider roles: Upstox primary live WebSocket plus history and index/futures data. Groww shares cash history and is an enabled fallback quote feed if Upstox fails. INDstocks shares cash history, not a live WebSocket. The latter two do not add primary streaming capacity.

Rollback: LIVE_ALPHA_UNIVERSE_PRESET=nifty500 restores previous membership. nse1000 is the default; explicit custom universe paths remain supported. No broker execution changes.
