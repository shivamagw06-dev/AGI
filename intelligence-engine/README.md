# AGI Intelligence Engine

Hybrid multi-agent research service for Agarwal Global Investments.

## Role

- **Node AGIB** remains the product gateway, cache, auth, and schedulers.
- **This engine** owns Research Director orchestration, analyst agents, evidence/confidence/citation, CIO synthesis, and memory.

Frontend must never call this service directly. Use Node `/api/intelligence/*`.

## Quick start

```bash
cd intelligence-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

Health: `GET http://127.0.0.1:8100/v1/health`

## Ask AGI model synthesis

Ask AGI retrieves and validates evidence locally, then uses OpenAI only for the
final grounded answer. Set `OPENAI_API_KEY` on the intelligence-engine service.
The defaults are `ASK_LLM_ENABLED=true`, `ASK_REASONING_MODEL=gpt-5.6-terra`,
`ASK_REASONING_EFFORT=medium`, and `ASK_LLM_TIMEOUT_SECONDS=25`. If the key,
model, evidence, or API is unavailable, Ask AGI automatically returns the
existing deterministic ICE answer. Secrets are never returned in telemetry.

## Auth

Send `Authorization: Bearer $INTELLIGENCE_ENGINE_TOKEN` (or `X-AGI-Intelligence-Token`).

## Create a run

```bash
curl -sS -X POST http://127.0.0.1:8100/v1/research/runs \
  -H "Authorization: Bearer dev-intelligence-token" \
  -H "Content-Type: application/json" \
  -d '{"desk":"smoke"}'
```

CIO morning desk:

```bash
curl -sS -X POST http://127.0.0.1:8100/v1/research/runs \
  -H "Authorization: Bearer dev-intelligence-token" \
  -H "Content-Type: application/json" \
  -d '{"desk":"cio_morning"}'
```

## Architecture

Research Director plans and invokes analysts → Evidence/Confidence/Citation/Debate engines → Chief Investment Officer synthesizes the final report only.

Agents read **AGIB Node cached APIs only** (no direct third-party market API calls).

### Architecture v1.0.1 contracts (WBS CON-001)

- EngineState SSOT: `contracts/v1/engine_state.schema.json` (pointer: `contracts/v1/CANONICAL.json`)
- Fixtures: `contracts/v1/fixtures/`
- ORCH control plane package: `app/orch/` (Document ID `ORCH`; distinct from `app/orchestration` Research Director and from E00 Layer 5 / E10)
- ORCH status: `GET /v1/orch/status`

### WS02 Market Data Platform (WBS DATA-001–005)

- Package: `app/market_data/` — provider abstraction, rate limit, cache, retry, circuit breaker, failover
- Providers: IndianAPI, Finnhub, FMP (pluggable via registry)
- Engines must consume canonical objects from `MarketDataClient` only
- Health: `GET /v1/market-data/health`

### WS03 Feature Registry (WBS FEAT-001–005)

- Package: `app/features/` — metadata registry, calculator registry, dependency graph, calculation scheduler, PIT store, cache, versioning, health/metrics
- Categories: `TECH_`, `VOL_`, `MACRO_`, `FUND_`, `UNIV_`; external stubs for `OPTIONS_`, `SENT_`, `EVENT_`, `RVAL_`
- Engines must consume Feature Registry outputs; they must not compute RSI/EMA/ATR/etc. internally
- Health: `GET /v1/features/health`
- Scheduler: `GET /v1/features/schedule/frequencies`, `GET /v1/features/schedule/plan`

### ORCH Layer 2 Feature Builds (WBS ORCH-003–005)

- Package: `app/orch/l2/` — dirty tracking, build queue, dependency scheduler, feature build ledger, ready events
- Flow: MarketDataClient publish → ORCH dirty detection → impacted subgraph → Feature Registry recompute → cache/store → ready event
- Engines must not request recalculation; they only read FeatureSnapshots
- APIs: `GET /v1/orch/l2/health`, `POST /v1/orch/l2/trigger`, `POST /v1/orch/l2/drain`, `GET /v1/orch/l2/builds`

### E01 Macro & Regime Engine P0 (WBS E01-001–005)

- Package: `app/engines/e01/` — Feature Builder, threshold classifiers, MacroScore, sizing, EngineState builder
- Inputs: Feature Registry / FeatureSnapshots only (no provider payloads, no polling)
- Outputs: canonical EngineState (`engine_state.schema.json`) with E01 metadata (axes, primary_regime, size_multiplier, …)
- Flags: `E01_P0=true`, `E01_HMM=false`, `E01_ML=false`
- ORCH: passive L2 ready-event consumer (`E01_MACRO` node)
- APIs: `GET /v1/e01/state`, `GET /v1/e01/history`, `GET /v1/e01/health`

### E14 Risk & Crowding Overlay P0 (WBS E14-001–005)

- Package: `app/engines/e14/` — Risk Feature Builder, rule-based taxonomy/risk_score, sizing/conf adj, E14Assessment, EngineState
- Inputs: Feature Registry + E01State only (no MarketDataClient, no polling)
- Outputs: canonical EngineState + E14Assessment; fail-closed without E01
- Flags: `E14_P0=true`, `E14_ML=false`, `E14_BAYES=false`
- ORCH: passive consumer of FeatureSnapshot + E01State (`E14_FIRM_PRIOR` / `E14_ASSESS`)
- APIs: `GET /v1/e14/state`, `GET /v1/e14/history`, `GET /v1/e14/health`

### E02 Factor & Style Engine P0 (WBS E02-001–005)

- Package: `app/engines/e02/` — Factor Feature Builder, exposure calculator, sector/universe normalisation, E02Exposure, EngineState
- P0 factors only: Momentum, LowVol, Size, Liquidity, Quality, Value
- Inputs: FeatureSnapshot + E01State + E14State only (no MarketDataClient, no polling)
- Flags: `E02_P0=true`, `E02_TIMING/ROTATION/SMART_BETA/ML=false`
- ORCH: passive Feature Ready / E01 Ready / E14 Ready consumer
- APIs: `GET /v1/e02/exposure/{symbol}`, `GET /v1/e02/history/{symbol}`, `GET /v1/e02/health`

### E04 Statistical Arbitrage & Relative Value P0 (WBS E04-001–005)

- Package: `app/engines/e04/` — Pair discovery, OLS/EG/half-life, E04State, EngineState
- P0 only: static/sector/index/user pairs, OLS hedge, spread z-score, Engle-Granger, half-life, mean-reversion signal, composite RV score
- Inputs: FeatureSnapshot + E01/E14/E02/E03 + available `RVAL_*` metadata only (no MarketDataClient)
- Flags: `E04_P0=true`, `E04_KALMAN/DYNAMIC_HEDGE/ETF_BASIS/ML=false`
- ORCH: passive Feature Ready / E01 / E14 / E02 / E03 Ready consumer
- CRE/Replay: auto-registered; promotion disabled
- APIs: `GET /v1/e04/state/{pair}`, `GET /v1/e04/history/{pair}`, `GET /v1/e04/health`

### E05 Event-Driven & Special Situations P0 (WBS E05-001–005)

- Package: `app/engines/e05/` — Event Feature Builder, Event State Builder, E05EventState, EngineState
- P0 only: earnings calendar, dividends, corporate actions (split/bonus/rights), guidance, basic EPS surprise, event decay/importance, composite event score
- Inputs: FeatureSnapshot + E01State + E14State + available `EVENT_*` + PIT corporate event objects only (no MarketDataClient / raw calendars)
- Flags: `E05_P0=true`, `E05_DEAL_PROBABILITY/TRANSCRIPTS/ML=false`
- ORCH: passive Feature Ready / E01 Ready / E14 Ready consumer
- CRE/Replay: auto-registered; promotion disabled
- APIs: `GET /v1/e05/events/{symbol}`, `GET /v1/e05/history/{symbol}`, `GET /v1/e05/health`

### E11 Sentiment & Alternative Data P0 (EPIC-015 / E11-001–005)

- Package: `app/engines/e11/` — Entity map, news tone/decay, soft `E11State` envelope, L4 soft-voter adapter
- P0 only: entity resolution, news sentiment + exponential decay, social ≤5% weight cap (social disabled), soft voter
- Inputs: FeatureSnapshot + E01State + E14State + `SENT_*` / `NEWS_*` PIT metadata only (no MarketDataClient)
- Flags: `E11_P0=true`, `E11_SOCIAL/TRANSCRIPTS/LLM/ML/ALTDATA=false`
- ORCH: passive Feature Ready / E01 Ready / E14 Ready consumer
- L4: optional soft voter; absent E11 ⇒ weight 0 (chaos path)
- CRE/Replay: auto-registered; promotion disabled
- APIs: `GET /v1/e11/sentiment/{symbol}`, `GET /v1/e11/state/{symbol}`, `GET /v1/e11/history/{symbol}`, `GET /v1/e11/health`

### E09 CTA Trend Engine P0 (WBS E09-001–005)

- Package: `app/engines/e09/` — Trend Feature Builder, Trend State Builder, E09State, EngineState
- P0 only: time-series momentum, short/medium/long horizons, volatility scaling, persistence, exhaustion, composite CTA score
- Inputs: FeatureSnapshot + E01State + E14State + `TECH_*` / `VOL_*` only (no MarketDataClient, no portfolio/cross-asset/ML)
- Flags: `E09_P0=true`, `E09_BREAKOUT/CROSS_ASSET/ML=false`
- ORCH: passive Feature Ready / E01 Ready / E14 Ready consumer
- CRE/Replay: auto-registered; promotion disabled
- APIs: `GET /v1/e09/state/{symbol}`, `GET /v1/e09/history/{symbol}`, `GET /v1/e09/health`

### E08 Volatility & Options Intelligence P0 (WBS E08-001–005)

- Package: `app/engines/e08/` — Volatility Feature Builder, Volatility State Builder, E08State, EngineState
- P0 only: historical/realized vol, regime, expansion/compression, basic expected move (when IV metadata available), composite score
- Inputs: FeatureSnapshot + E01State + E14State + `VOL_*` / available `OPTIONS_*` registry metadata only (no MarketDataClient)
- Flags: `E08_P0=true`, `E08_GAMMA/DEALER/SURFACE/ML=false`
- ORCH: passive Feature Ready / E01 Ready / E14 Ready consumer
- CRE/Replay: auto-registered; promotion disabled
- APIs: `GET /v1/e08/state/{symbol}`, `GET /v1/e08/history/{symbol}`, `GET /v1/e08/health`

### E13 Equity Fundamental L/S P0 (WBS E13-001–005)

- Package: `app/engines/e13/` — Fundamental Feature Builder, Composite Fundamental Scorer, E13Fundamental, EngineState
- P0 only: Revenue/EPS growth, margins, ROE/ROIC/ROCE, debt metrics, cash-flow quality, basic valuation → Quality / Value / Composite scores
- Inputs: FeatureSnapshot + E01State + E14State + PIT `FUND_*` registry features only (no MarketDataClient, no ML/NLP/moat)
- Flags: `E13_P0=true`, `E13_REVISIONS/MOAT/ML=false`
- ORCH: passive Feature Ready / E01 Ready / E14 Ready consumer
- CRE/Replay: auto-registered in Historical Engine Runner + CRE scorecards; promotion disabled
- APIs: `GET /v1/e13/fundamental/{symbol}`, `GET /v1/e13/history/{symbol}`, `GET /v1/e13/health`

### E03 Cross-Sectional Quant Engine P0/M0 (WBS E03-001–005)

- Package: `app/engines/e03/` — Technical Feature Adapter, `SM_AGI_TECH` (production `score_research` parity), E03Alpha, EngineState, ParityReport
- Behavioural migration only: RSI / MACD / SMA / returns / volume / range / ROC thresholds identical to `nifty500_research_engine.py`
- Inputs: FeatureSnapshot + E01State + E14State + E02Exposure only (no MarketDataClient, no polling)
- Flags: `E03_P0=true`, `E03_PARITY=true`, `E03_COMPOSITE/XS_MODE/ML=false`
- ORCH: passive Feature Ready / E01 Ready / E14 Ready / E02 Ready consumer
- APIs: `GET /v1/e03/alpha/{symbol}`, `GET /v1/e03/history/{symbol}`, `GET /v1/e03/parity`, `GET /v1/e03/health`

### L4 Composite Intelligence P0 Shadow (WBS L4-001–005)

- Package: `app/engines/l4/` — EngineState collector, evidence aggregator, conflict resolver, rule-based vote, L4Opinion, ShadowComparison
- Shadow only: never influences production; never replaces E03
- Inputs: E01State + E14State + E02Exposure + E03Alpha only (no MarketDataClient, no FeatureSnapshot)
- Flags: `L4_SHADOW=true`, `L4_PRIMARY/BAYES/ML/PROBABILITY=false`
- ORCH: passive E01 / E14 / E02 / E03 Ready consumer
- APIs: `GET /v1/l4/opinion/{symbol}`, `GET /v1/l4/history/{symbol}`, `GET /v1/l4/health`

### E10 Portfolio Construction P0 (WBS E10-001–005)

- Package: `app/engines/e10/` — Top-N selection, inverse-volatility, vol targeting, name/sector caps, cash floors, E10Portfolio validation
- Model portfolio only: no execution, OMS, broker routing, BL/MVO/HRP/ERC
- Inputs: L4Opinion + E14State + E02Exposure only
- Flags: `E10_P0=true`, `E10_OPTIMIZER/HRP/MVO=false`
- ORCH: passive L4 Ready consumer
- APIs: `GET /v1/e10/portfolio`, `GET /v1/e10/history`, `GET /v1/e10/health`

### Validation & Backtesting P0 (WBS BT-001–005)

- Package: `app/validation/` — Replay Engine, Golden Dataset Loader, Historical Engine Runner, Metrics, Dashboard payload
- Pipeline: Snapshot → E01 → E14 → E02 → E13 → E08 → E09 → E05 → E11 → E03 → E04 → L4 → E10 → Metrics (isolated instances; replay store only)
- Metrics: daily/benchmark return, hit/win rate, IC, Sharpe, Sortino, max DD, turnover, confidence calibration, bucket accuracy, parity stability
- Flags: `BACKTEST=true`, `LIVE=false`
- APIs: `POST /v1/validation/replay`, `GET /v1/validation/runs`, `GET /v1/validation/runs/{id}`, `GET /v1/validation/dashboard/{id}`, `GET /v1/validation/health`

### Continuous Research Evaluation P0 (WBS CRE-001–005)

- Package: `app/cre/` — Daily Evaluation Runner, Rolling Metrics Store, Drift Detection, Research Scorecards, Promotion Evidence, Dashboard
- Not a research/trading engine: consumes Historical Replay, Daily Shadow Runs, EngineStates, L4Opinion, E10Portfolio
- Rolling windows: 30 / 90 / 252 days (adaptive `days_used` when series shorter)
- Drift: model, confidence, feature, distribution, performance + regression alerts
- Outputs: EngineScorecard, CompositeScorecard, PromotionReport, DriftAlert, RegressionAlert
- Flags: `CRE=true`, `PROMOTION=false` (evidence-only; never promotes / no production influence)
- APIs: `POST /v1/cre/evaluate`, `GET /v1/cre/scorecards`, `GET /v1/cre/scorecards/{engine}`, `GET /v1/cre/alerts`, `GET /v1/cre/promotion`, `GET /v1/cre/dashboard`, `GET /v1/cre/health`

### Knowledge Intelligence Platform P0 (KIP)

- Package: `app/kip/` — institutional memory layer for AGI (does **not** redesign research engines)
- Pipeline: OCR → clean → metadata → entity/theme/sector → metrics/tables/timeline → thesis/bull/bear/risks/catalysts/valuation → confidence → chunk → embed → hybrid index → knowledge graph → KB
- Sources: AGI research/CIO/briefs + broker PDFs/emails, newsletters, filings, transcripts, macro/industry/commodity reports
- Immutable document versioning with supersession + knowledge lineage
- Company research timeline; hybrid/keyword/semantic/entity/company/sector/theme/broker/similarity search
- RAG evidence packs: retrieved docs, supporting evidence, conflicting opinions, freshness, confidence
- Self-learning: completed Research Director runs auto-ingest into KIP; writer retrieves prior institutional context
- Flags: `KIP=true`, `KIP_RAG=true`, `KIP_GRAPH=true`, `KIP_VERSIONING=true`, `KIP_OCR=true`, `KIP_LLM_SUMMARY=true`
- Out of scope: model fine-tuning, broker execution, portfolio management, research engine redesign
- APIs: `POST /v1/kip/ingest`, `GET /v1/kip/document/{id}`, `GET /v1/kip/company/{ticker}`, `GET /v1/kip/theme/{id}`, `GET /v1/kip/search`, `GET /v1/kip/timeline/{ticker}`, `GET /v1/kip/similar/{document}`, `GET /v1/kip/graph/{entity}`, `GET /v1/kip/rag`, `GET /v1/kip/health`

### Knowledge Intelligence Platform P1 (House Intelligence)

- Extends KIP into a living institutional knowledge system (no engine redesign, no fine-tuning)
- Auto-ingest channels: AGI published research, broker bulk (PDF/DOCX/MD/Email/ZIP), newsletters, internal notes
- House View engine per ticker: current view, historical views, thesis evolution, changed/stable/failed assumptions, catalysts, confidence, prediction accuracy
- Priority RAG / client search: AGI research → Engine states → L4 → Broker → News → Filings → General; homepage search **never answers directly**
- Prediction tracking + 3m/6m/12m self-evaluation (hit rate, average return, sector/analyst/catalyst accuracy)
- Company dossier + research continuity context for Research Writer
- Flags: `KIP_AUTO_INGEST=true`, `KIP_HOUSE_VIEW=true`, `KIP_PREDICTION_TRACKING=true`, `KIP_RAG=true`, `KIP_GRAPH=true`, `KIP_TIMELINE=true`
- APIs: `POST /v1/kip/ingest/agi|broker|newsletter|internal`, `GET /v1/kip/house-view/{ticker}`, `GET /v1/kip/research-history/{ticker}`, `GET /v1/kip/predictions/{ticker}`, `GET /v1/kip/company-dossier/{ticker}`, `POST /v1/kip/client-search`, `GET /v1/kip/search`, `GET /v1/kip/rag`

### Reasoning & Research Synthesis Platform P0 (RSP)

- Package: `app/rsp/` — institutional **Research Committee** layer (does **not** redesign engines)
- Contract: **KIP retrieves → RSP reasons → LLM writes** (LLM never receives raw retrieved documents)
- Pipeline: retrieve → dedupe → rank → contradictions → cluster opinions → separate facts/opinions → extract/score evidence → consensus → house-view compare → change detection → ReasoningPackage
- Consensus: AGI view, broker consensus, market consensus, contrarian view, unknowns
- Contradiction engine: AGI vs broker, broker disagreement, news vs fundamentals, macro vs technicals, events vs house view, conflicting targets
- Synthesis: research brief, thesis, counter-thesis, catalysts, risks, valuation, confidence, evidence tree
- Soft-wired into Research Director as `rsp_reasoning_package` for institutional writing
- Flags: `RSP=true`, `RSP_CONSENSUS=true`, `RSP_CONTRADICTIONS=true`, `RSP_REASONING=true`
- Out of scope: fine-tuning, engine redesign, broker execution, portfolio optimisation, autonomous decisions
- APIs: `POST /v1/rsp/reason`, `POST /v1/rsp/synthesize`, `POST /v1/rsp/committee`, `GET /v1/rsp/reasoning/{id}`, `GET /v1/rsp/evidence/{id}`, `GET /v1/rsp/health`

### Research Management System P0 (RMS)

- Package: `app/rms/` — institutional research workflow (does **not** redesign engines/CMS/website)
- Lifecycle: Idea → Request → Knowledge Collection → RSP Reasoning → Draft → Internal Review → Compliance Review → Approval → Publication → Automatic KIP Ingestion → Prediction Tracking
- Research object: status, owner, reviewer, version, evidence package, reasoning package, engine snapshot, house view, prediction horizon, publishing history, compliance audit
- Publishing creates website article, newsletter, LinkedIn draft, internal archive stubs; then KIP ingest + prediction records
- Dashboard: pipeline, draft/review queues, publication calendar, prediction tracker, company/sector coverage
- Flags: `RMS=true`, `RMS_REVIEW=true`, `RMS_APPROVAL=true`, `RMS_PUBLISH=true`
- Out of scope: CMS redesign, website redesign, trading, engine redesign
- APIs: `POST /v1/rms/request`, `POST /v1/rms/draft`, `POST /v1/rms/review`, `POST /v1/rms/approve`, `POST /v1/rms/publish`, `GET /v1/rms/dashboard`, `GET /v1/rms/research/{id}`, `GET /v1/rms/health`

### AGI Analyst Workspace P0 (AWS)

- Package: `app/aws/` — internal Bloomberg-style institutional terminal (**not** a public website)
- Consumes existing platforms only: KIP, RSP, E01–E05/E08–E11/E13–E14, L4, E10, Replay, CRE, RMS
- Creates **no** new research logic; soft-aggregates workspace views
- Workspaces: Company, Sector, Theme, Macro, Portfolio, Research, Replay, CRE + Knowledge Explorer
- Global search: companies, themes, reports, people, sectors, broker notes, research, predictions
- Context-aware AI Copilot — never starts from an empty prompt (workspace + KIP + RSP + L4 + portfolio + research)
- Flags: `AWS=true`, `AWS_COPILOT=true`, `AWS_REPLAY=true`, `AWS_CRE=true`
- Out of scope: research engine changes, trading, OMS, broker execution, architecture amendments
- APIs: `GET /v1/aws/company/{ticker}`, `GET /v1/aws/theme/{id}`, `GET /v1/aws/sector/{id}`, `GET /v1/aws/replay/{date}`, `GET /v1/aws/dashboard`, `GET /v1/aws/search`, `GET /v1/aws/copilot`, plus `/macro`, `/portfolio`, `/research`, `/cre`, `/knowledge/{entity}`, `/health`

### Investment Operations Centre P0 (IOC)

- Package: `app/ioc/` — operational mission control for the AGI Investment Office
- **Monitors only** — no investment opinions, no research, no portfolio logic, no engine redesign
- Monitors: Market Data, Feature Registry, ORCH, all engines, L4, E10, Replay, CRE, KIP, RSP, RMS, AWS
- Health model: healthy / warning / critical / offline / stale / recovering
- Checks: provider/feature freshness, engine completion, ORCH queue, API/DB latency, replay/CRE success, research publication, knowledge ingestion, prediction tracking, portfolio generation
- Alerts + reports: daily ops, morning readiness, market open checklist, EOD, weekly summary
- Flags: `IOC=true`, `IOC_ALERTS=true`, `IOC_REPORTS=true`
- Out of scope: trading, research, portfolio logic, architecture changes
- APIs: `GET /v1/ioc/dashboard`, `GET /v1/ioc/health`, `GET /v1/ioc/alerts`, `GET /v1/ioc/providers`, `GET /v1/ioc/readiness`, `GET /v1/ioc/report`

### UI Aggregation Layer (Client Facade)

- Package: `app/ui/` — **client-facing aggregation**, not a new research platform
- Architecture v1.0.1 **LOCKED** — no visual redesign mandate on the website; no engine exposure to public clients
- Soft-consumes AWS / KIP / RSP / RMS / IOC / CRE / Validation / AIP
- Frontend must call `/api/ui/*` (Express) → `/v1/ui/*` (engine) — never E01–E14 directly
- Surfaces: home, company, search, autocomplete, article, research, theme, sector, dashboard, macro, portfolio, copilot, workflow, timeline
- **Public Product Experience V1**: homepage Ask AGI + Popular Investor Questions; search returns full institutional answer (executive summary, house view, confidence, thesis, bull/bear, risks, catalysts, evidence, timeline, follow-ups)
- **IAX (Institutional Answer Experience)**: `/ask` becomes an interactive research workspace — house view card, what's changed, supporting/conflicting evidence, research panel, knowledge graph, market intelligence summaries (no engine names), charts descriptors, related ideas, portfolio context, in-page follow-ups, save/export/share
- **AGI Product V1**: product excellence layer on existing Investment Office — Company/Sector/Theme/Macro intelligence desks, living research articles, Prediction Centre (`/predictions`), Personal Workspace (`/workspace`), discovery rails, SEO metadata, local product analytics; still only `/api/ui/*` → `/v1/ui/*`
- **Investment Office Homepage V1**: dark premium institutional homepage — Morning Intelligence, Ask AGI hero, live market snapshot (BFF-enriched), popular questions, research/dashboard/themes/companies, calendar/knowledge/predictions/newsletter, footer metrics; `/` consumes `/api/ui/home` (+ `/api/ui/calendar`, search/autocomplete)
- Flags: `UI=true`
- APIs: `GET /v1/ui/home`, `GET /v1/ui/company/{ticker}`, `POST /v1/ui/search`, `GET /v1/ui/autocomplete`, `GET /v1/ui/article/{id}`, `GET /v1/ui/research/{id}`, `GET /v1/ui/theme/{id}`, `GET /v1/ui/sector/{id}`, `GET /v1/ui/timeline/{entity}`, `GET /v1/ui/predictions`, `GET /v1/ui/calendar`, `GET /v1/ui/dashboard`, `GET /v1/ui/macro`, `GET /v1/ui/portfolio`, `GET /v1/ui/copilot`, `GET /v1/ui/workflow`, `GET /v1/ui/health`

### Alpha Improvement Programme (AIP) — Research Roadmap

- Package: `app/aip/` — **research programme**, not a new platform
- Architecture v1.0.1 **LOCKED** — no platform / infrastructure / workflow redesign; no duplicate engines
- Mission: improve measurable investment performance (prediction accuracy, risk, portfolio construction, research quality, calibration, explainability)
- L4 remains **shadow**; AIP never mutates `app/engines/l4/mapping.py` production weights
- Capabilities: Dynamic Weight Registry, engine contribution / marginal information gain, calibration optimisation, confidence recalibration, regime- & sector-specific shadow weights, prediction attribution, House View evolution, research/client quality scoring
- Experiment framework (every run): hypothesis → metrics → historical replay → CRE → statistical significance → rollback plan
- Baselines: current L4, current E03, historical replay, golden dataset, paper portfolio
- Validation deltas: Sharpe, Sortino, IC, hit rate, calibration, max drawdown, turnover, prediction accuracy
- Promotion: evidence-only when `AIP_PROMOTION=false`; requires replay superiority, CRE superiority, significance, risk approval, architecture approval
- Workstreams: AIP-01 … AIP-10 (cross-engine calibration → client answer quality)
- Flags: `AIP=true`, `AIP_EXPERIMENTS=true`, `AIP_PROMOTION=false`
- APIs: `GET /v1/aip/health`, `GET /v1/aip/roadmap`, `GET|POST /v1/aip/weights`, `POST /v1/aip/experiment`, `GET /v1/aip/experiments`, `GET /v1/aip/contribution`, `GET /v1/aip/calibration`, `GET /v1/aip/attribution`, `GET /v1/aip/house-view-evolution/{ticker}`, `POST /v1/aip/quality`, `GET /v1/aip/promotion`, `GET /v1/aip/dashboard`
