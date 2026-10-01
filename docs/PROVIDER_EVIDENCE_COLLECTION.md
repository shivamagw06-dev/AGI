# Read-only NIFTY data collection

Admin: `/admin/nifty-paper-agents` → Data recording & historical downloads.
Start once to persist the requested 365-day window ending yesterday. The engine
supervisor resumes incomplete downloads after a deployment. No broker orders,
strategy state, event-calendar approval, or automatic feed switching is involved.

## Storage and scope

All new data lives beside OPTIONS_LAB_DB_PATH under provider_evidence. Collection
refuses to start unless the path resolves onto the existing /var/data/kip mount.
It pauses with less than 2 GiB free. SQLite WAL holds source-specific history and
verified chunk manifests. Empty responses remain explicit gaps. Sources are never
silently mixed. Groww's absent volume/OI remains null. Upstox candles are also
cached by the existing minute-history module, but a download is not a backtest.

Spot: requested 365 days of minute candles, in 28-day chunks. Derivatives:
provider-returned expired NIFTY contracts; strikes within 2,000 points of observed
spot opens, options final 14 calendar days and futures final 28 days. This is a
bounded research universe, not all historical contracts. Provider restrictions,
missing expiries and session gaps are not inferred away. Finished download pass
means returned coverage was processed, not that a complete year was supplied.

Groww official SDK subscribes to NIFTY plus up to 42 nearest-expiry options and
one future selected from the official instrument master. Mapping is saved.
Changed index/LTP/depth payloads are sampled at most once per second and retain
provider and receipt timestamps. Both stale and fresh observations are retained
with quality labels. No automatic failover is enabled. It reconnects daily and
on process exit, with a five-minute failure cooldown. After-market state does not
prove fresh live delivery. The existing finance backend owns Groww authentication. An allowlisted NIFTY-only
service bridge supplies historical data and short-lived socket authorization;
the Groww trading token is never copied to the engine. The engine retains its
existing Upstox credentials. No token is returned through the admin API or written
into collector configuration. A brief after-hours connection probe checks stream
authentication, but does not prove fresh market delivery.

Live Upstox second frames already use 14 hot days plus verified compressed daily
archives for 365 days. Groww observations are retained 365 days. Both reside on
the same volume; this is retention, not an independently verified disaster backup.
Historical candle caches are preserved until an explicit future archival policy.

## Operations

`GET /v1/options-lab/data-evidence` returns coverage, retention and stream health.
`POST` activates/resumes the persisted window. Both require engine authentication;
the frontend proxy additionally requires an AGI admin. Runtime status remains
separate from the small broker-capability audit. Do not interpret a successful
REST sample as a verified WebSocket session or as a profitable trading strategy.
