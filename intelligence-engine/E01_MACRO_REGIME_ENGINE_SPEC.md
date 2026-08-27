# E01 — Macro & Regime Engine  
## Engineering Implementation Specification (AGI Investment Office)

**Owner:** CIO / Head of Quantitative Research  
**Pipeline position:** **First** engine executed. All downstream engines consume its output.  
**Nature:** Research intelligence only — no order routing, no portfolio execution.  
**Version:** 1.0  
**Status:** Implementation-ready specification  

### Relationship to current AGIB stack (reuse)

| Existing asset | Path | E01 role |
|----------------|------|----------|
| Macro context aggregator | `server/services/macroContextService.js` | L7 input adapters (extend) |
| Macro repository / TTLs | `server/services/macroRepository.js` | Feature + raw cache layer |
| Briefing + heuristic `workspace.regime` | `server/services/macroBriefingService.js` | **Replace heuristic** with E01 structured regime |
| Supabase tables | `supabase/migrations/20260724153000_macro_data_repository.sql` | Extend; add regime history |
| API | `GET /api/market/macro-briefing` | Keep; add `GET /api/intelligence/e01/state` |
| UI | `src/pages/MacroIntelligence.jsx` | Consume E01 widgets |
| Agent | `intelligence-engine/.../macro_economist.py` | Consume E01 state, not outlook string alone |

**Net-new:** HMM + threshold ensemble, feature store, regime history, submodel services, downstream weight multipliers, Bloomberg-grade regime UI, validation harness.

---

# 1. Engine Purpose

## 1.1 Investment questions answered

1. **What is the current global and India macro state?** (growth, inflation, policy, liquidity)  
2. **Which market regime are we in**, and how confident are we?  
3. **Is risk appetite expanding or contracting?**  
4. **How should research engines tilt** (trend vs mean-reversion, value vs momentum, vol harvest vs hedge)?  
5. **What is the implied position-size / vol-target multiplier** for institutional research books?  
6. **What would falsify the current regime call?**  

## 1.2 Why it exists

Institutional PnL is regime-conditional. Trend, factor, and vol strategies have orthogonal regime betas. Without a shared regime object:

- Engines disagree silently  
- CIO briefs mix incompatible playbooks  
- Risk overlays cannot scale exposure consistently  

E01 is the **single source of truth** for environment classification.

## 1.3 Hedge-fund / institutional analogues

| Firm / style | How regime is used |
|--------------|-------------------|
| Bridgewater | Growth/inflation regime boxes → asset tilts (All Weather / Pure Alpha research) |
| Two Sigma / DE Shaw | Statistical regime features in meta-models |
| AQR | Factor timing & style premia conditioned on macro/vol states |
| Man AHL / Winton | Trend overlays + vol targeting by environment |
| Brevan Howard | Macro regime narratives driving cross-asset risk |
| Citadel / Millennium multi-strat | Central risk → sleeve risk budgets by environment |

---

# 2. Market Regimes

AGI uses a **multi-axis regime vector**, not a single label. Downstream engines read axes independently and a fused `primary_regime`.

## 2.1 Regime axes (canonical)

| Axis ID | Name | Allowed states |
|---------|------|----------------|
| `R_MARKET` | Market direction | `bull`, `bear`, `sideways` |
| `R_VOL` | Volatility | `low_vol`, `normal_vol`, `high_vol`, `crisis_vol` |
| `R_RISK` | Risk appetite | `risk_on`, `risk_off`, `risk_mixed` |
| `R_INFL` | Inflation | `inflationary`, `disinflationary`, `deflationary_pressure`, `stable_prices` |
| `R_CYCLE` | Business cycle | `expansion`, `slowdown`, `recession`, `recovery` |
| `R_LIQ` | Liquidity | `liq_expansion`, `liq_neutral`, `liq_contraction` |
| `R_POLICY` | Policy stance | `easing`, `on_hold`, `tightening` |
| `R_EARN` | Earnings calendar | `pre_earnings`, `earnings_season`, `post_earnings` |
| `R_STRESS` | Systemic stress | `normal`, `elevated_stress`, `crisis` |

`primary_regime` = deterministic priority fuse (see §7.5):  
`crisis` > `recession+risk_off` > `recovery` > `expansion+risk_on` > `slowdown` > else composite label.

---

## 2.2 Regime dictionary

### Bull Market (`R_MARKET=bull`)
- **Definition:** Persistent positive drift in risk assets with higher highs / higher lows over medium horizon.  
- **Characteristics:** Broadening breadth, contained credit spreads, supportive financial conditions.  
- **Behaviour:** Dip-buying works; momentum positive; vol often compresses.  
- **Examples:** Post-GFC 2013–2017 equity bull; India FY21–FY24 large-cap bull phases.  
- **Expected performance:** Equities/credit ↑; duration mixed; gold mixed; VIX ↓.

### Bear Market (`R_MARKET=bear`)
- **Definition:** Persistent negative drift / lower highs; equity drawdown typically >20% peak-to-trough (global) or policy-driven India corrections.  
- **Characteristics:** Widening credit spreads, weak breadth, rising vol.  
- **Behaviour:** Rallies fail; trend-following short/underweight works; mean-reversion traps.  
- **Examples:** 2008; 2022 global rates shock; India 2008/2013 taper stress.  
- **Expected performance:** Equities/credit ↓; USD/quality ↑; vol ↑; gold often ↑.

### Sideways (`R_MARKET=sideways`)
- **Definition:** Range-bound index; realised trend weak relative to vol.  
- **Characteristics:** Oscillating breadth; factor rotation elevated.  
- **Behaviour:** Mean-reversion & relative value outperform pure trend.  
- **Examples:** Many mid-cycle consolidation years.  
- **Expected performance:** Neutral beta; stock-picking / RV ↑; CTA chop risk.

### High Volatility (`R_VOL=high_vol`)
- **Definition:** Realised/implied vol in upper historical quantile (e.g. India VIX / VIX > 75th %ile).  
- **Characteristics:** Fat tails, correlation spikes.  
- **Behaviour:** Reduce size; widen stat-arb bands; favour convex hedges.  
- **Examples:** Mar-2020; banking stress episodes.  
- **Expected performance:** Long vol / quality / USD often ↑.

### Low Volatility (`R_VOL=low_vol`)
- **Definition:** Vol in lower quantile; stable realised ranges.  
- **Characteristics:** Carry attractive; leverage creeps up.  
- **Behaviour:** Trend & carry work until regime breaks.  
- **Examples:** Mid-2017; parts of 2024.  
- **Expected performance:** Risk assets grind up; short-vol profitable until crash.

### Risk On / Risk Off (`R_RISK`)
- **Risk On:** Bid for cyclicals, EM, credit, high-beta.  
- **Risk Off:** Bid for USD, quality duration, gold, low-beta.  
- **Examples On:** Post-vaccine 2020–21. **Off:** 2011 EU crisis; 2022.  
- **Performance:** Maps to beta and credit beta exposure.

### Inflationary / Deflationary pressure (`R_INFL`)
- **Inflationary:** Rising CPI/PPI, rising breakevens/commodity impulse. Favours commodities, value/energy; hurts long duration.  
- **Deflationary pressure:** Falling demand/prices, rising real yields risk via growth shock. Favours duration/quality.  
- **Examples:** 2021–22 inflation; 2008–09 deflation scare.

### Expansion / Recession / Recovery (`R_CYCLE`)
- **Expansion:** Rising PMI/GDP above trend.  
- **Recession:** Contracting activity / rising unemployment.  
- **Recovery:** Early upturn from trough.  
- **Examples:** Expansion mid-2010s; Recession 2008–09; Recovery 2009 / mid-2020.

### Liquidity Expansion / Contraction (`R_LIQ`)
- **Expansion:** Rising global M2 / falling real rates / ample reserves / RBI surplus liquidity.  
- **Contraction:** QT, rising real yields, draining reverse-repo/TGA dynamics.  
- **Examples:** 2020–21 liquidity boom; 2022–23 contraction.

### Earnings Season (`R_EARN=earnings_season`)
- **Definition:** Dense corporate results window (India quarterly; US quarterly clusters).  
- **Behaviour:** Elevate PEAD / revision engines; reduce pure technical weight.  
- **Examples:** Nifty results seasons each quarter.

### Crisis (`R_STRESS=crisis`)
- **Definition:** Multi-asset dislocation: vol spike + credit blowout + liquidity failure.  
- **Behaviour:** Survival mode — cut gross, favour hedges, disable fragile arb.  
- **Examples:** Oct-2008; Mar-2020.

---

# 3. Sub Models

Each submodel is a Python package under `intelligence-engine/app/engines/e01/submodels/`.

Interface (all submodels):

```python
class SubModelResult(TypedDict):
    model_id: str
    state: str                 # model-specific enum
    score: float               # [-2, +2] standardized impulse
    confidence: float          # [0, 1]
    features: dict[str, float]
    evidence: list[str]        # human-readable
    as_of: str                 # ISO timestamp
    stale: bool
```

### 3.1 Business Cycle Model (`SM_CYCLE`)
| | |
|--|--|
| **Purpose** | Classify expansion / slowdown / recession / recovery for US + India |
| **Inputs** | GDP nowcasts, PMI mfg/services, industrial production, unemployment / claims, capacity util |
| **Outputs** | `cycle_us`, `cycle_in`, `cycle_global`, scores |
| **Dependencies** | Economic Surprise, Global Growth |
| **Confidence** | High when PMI+claims agree; low when mixed |

### 3.2 Liquidity Model (`SM_LIQ`)
| | |
|--|--|
| **Purpose** | Measure financial system liquidity impulse |
| **Inputs** | Global M2 (proxy), Fed balance sheet / TGA / RRP, RBI liquidity (LAF/reverse repo), real yields, credit growth |
| **Outputs** | `liq_state`, `liq_score` |
| **Dependencies** | Central Bank, Yield Curve |
| **Confidence** | Medium (publication lags) |

### 3.3 Central Bank Model (`SM_CB`)
| | |
|--|--|
| **Purpose** | Policy stance Fed + RBI (+ ECB optional) |
| **Inputs** | Fed funds, dots/summary (when available), RBI repo/SDF/MSF, statement hawkish/dovish NLP score |
| **Outputs** | `policy_us`, `policy_in`, `policy_score` |
| **Dependencies** | Inflation, Yield Curve |
| **Confidence** | High on rates; medium on language |

### 3.4 Yield Curve Model (`SM_CURVE`)
| | |
|--|--|
| **Purpose** | Curve shape & recession signal |
| **Inputs** | US 2Y/10Y/30Y, India 1Y/10Y G-Sec, swap spreads if available |
| **Outputs** | `curve_slope_us`, `curve_slope_in`, `inversion_flag`, `butterfly` |
| **Dependencies** | Central Bank |
| **Confidence** | High |

### 3.5 Inflation Model (`SM_INFL`)
| | |
|--|--|
| **Purpose** | Inflation level, momentum, surprise |
| **Inputs** | US CPI/Core/PPI, India CPI/Core, oil, food, USDINR |
| **Outputs** | `infl_state`, `infl_surprise`, `real_yield_us` |
| **Dependencies** | Commodity, Currency |
| **Confidence** | High |

### 3.6 Currency Model (`SM_FX`)
| | |
|--|--|
| **Purpose** | Dollar & INR conditions |
| **Inputs** | DXY (or proxy), USDINR, EURUSD, real rate differentials |
| **Outputs** | `usd_impulse`, `inr_pressure`, `fx_regime` |
| **Dependencies** | Liquidity, Central Bank |
| **Confidence** | High |

### 3.7 Commodity Model (`SM_CMDTY`)
| | |
|--|--|
| **Purpose** | Growth vs inflation commodity impulse |
| **Inputs** | WTI/Brent, Gold, Silver, Copper, Natural Gas, Baltic Dry / freight proxies |
| **Outputs** | `cmdty_growth_basket`, `cmdty_infl_basket`, `oil_shock_flag` |
| **Dependencies** | Global Growth |
| **Confidence** | Medium–High |

### 3.8 Risk Appetite Model (`SM_RISK`)
| | |
|--|--|
| **Purpose** | Cross-asset risk-on/off |
| **Inputs** | VIX / India VIX, MOVE (or US rates vol proxy), HY/IG spreads (or EMBI proxy), equity breadth, USD |
| **Outputs** | `risk_state`, `risk_score`, `stress_index` |
| **Dependencies** | Vol features, Credit |
| **Confidence** | High when vol+credit agree |

### 3.9 Economic Surprise Model (`SM_SURP`)
| | |
|--|--|
| **Purpose** | Data vs expectations impulse |
| **Inputs** | Citigroup-style surprise index if licensed; else PMI/CPI print vs consensus (Finnhub/FMP/manual) |
| **Outputs** | `surprise_us`, `surprise_in` |
| **Dependencies** | none |
| **Confidence** | Medium without paid surprise index |

### 3.10 Global Growth Model (`SM_GROWTH`)
| | |
|--|--|
| **Purpose** | Synchronised global growth score |
| **Inputs** | US/EU/China/India PMI, copper, Baltic Dry, world GDP nowcast proxies |
| **Outputs** | `growth_global`, `growth_em` |
| **Dependencies** | Business Cycle, Commodity |
| **Confidence** | Medium |

### 3.11 Volatility Regime Model (`SM_VOL`)
| | |
|--|--|
| **Purpose** | Map realised/implied vol to `R_VOL` / crisis |
| **Inputs** | VIX, India VIX, equity realised 20d/60d, MOVE proxy |
| **Outputs** | `vol_state`, `vol_percentile` |
| **Dependencies** | Risk Appetite |
| **Confidence** | High |

### 3.12 Earnings Calendar Model (`SM_EARN`)
| | |
|--|--|
| **Purpose** | Flag earnings season intensity |
| **Inputs** | Corporate results calendar density (India + US) |
| **Outputs** | `earn_state`, `earn_density_0_1` |
| **Dependencies** | none |
| **Confidence** | High if calendar feed present; else calendar heuristic |

---

# 4. Inputs

## 4.1 Market data
US10Y, US2Y, US30Y, India10Y, India1Y/2Y G-Sec, Fed Funds effective, RBI Repo / SDF / MSF, DXY proxy, USDINR, EURUSD, WTI/Brent, Gold, Silver, Copper, Nat Gas, VIX, India VIX, equity index levels (SPX, Nifty), credit spread proxies, Baltic Dry / freight proxy.

## 4.2 Economic data
US CPI, Core CPI, PPI, GDP, PMI mfg/services, NFP, Initial Claims, India CPI/Core, India GDP, India PMI, IIP, unemployment proxies.

## 4.3 Central bank / government
FOMC decisions & statement text, RBI MPC decisions & statement text, Fed/RBI balance-sheet / liquidity summaries, Treasury General Account (optional), RRP (optional).

## 4.4 Alternative / optional
Consensus estimates (for surprises), satellite crop (future), port congestion (future), news sentiment macro topics.

## 4.5 Input registry (canonical IDs)

| input_id | Description | Unit |
|----------|-------------|------|
| `US_DGS2` | US 2Y yield | % |
| `US_DGS10` | US 10Y yield | % |
| `US_DGS30` | US 30Y yield | % |
| `US_FEDFUNDS` | Fed funds | % |
| `IN_GSEC10` | India 10Y G-Sec | % |
| `IN_REPO` | RBI repo | % |
| `US_CPI_YOY` | US CPI YoY | % |
| `US_CORE_CPI_YOY` | US Core CPI YoY | % |
| `IN_CPI_YOY` | India CPI YoY | % |
| `US_PMI_MFG` | US PMI manufacturing | index |
| `IN_PMI_MFG` | India PMI manufacturing | index |
| `US_GDP_YOY` | US real GDP YoY | % |
| `IN_GDP_YOY` | India real GDP YoY | % |
| `USDINR` | USDINR spot | INR |
| `DXY_PROXY` | Dollar index proxy | index |
| `WTI` | WTI crude | USD/bbl |
| `GOLD` | Gold | USD/oz |
| `COPPER` | Copper | USD/t or lb |
| `VIX` | CBOE VIX | points |
| `INDIA_VIX` | India VIX | points |
| `HY_OAS_PROXY` | High-yield spread proxy | bps |
| `GLOBAL_M2_PROXY` | Global liquidity proxy | index |
| `CLAIMS` | US initial claims | count |
| `BDI_PROXY` | Baltic Dry / freight proxy | index |

---

# 5. APIs

| input_id | Primary API | Refresh | Cost | Reliability | Fallback |
|----------|-------------|---------|------|-------------|----------|
| US yields, FEDFUNDS, CPIAUCSL | **FRED** (`FRED_API_KEY`) | 1d | Free tier | High | Treasury.gov XML |
| India CPI/GDP (annual/lagged) | **World Bank** | 1d cache / update on release | Free | Medium (lag) | MOSPI / RBI DBIE manual CSV |
| India G-Sec 10Y | **IndianAPI** or RBI DBIE | 1d | Paid/free mix | Medium | Investing.com scrape **not allowed** — use RBI |
| Repo / policy | RBI press + manual/structured feed (`RBI_DATA_API_KEY` when live) | Event + 1d | Low | Medium | MPC calendar table in CMS |
| WTI, Gold | **Alpha Vantage** commodities | 1d | Free/premium | Medium | FRED `DCOILWTICO`, `GOLDAMGBD228NLBM` |
| Copper / NatGas | AV / FRED | 1d | Low–Med | Medium | Yahoo delayed **research-only** |
| USDINR | Frankfurter/ECB (existing) + FX mashup | 1d | Free | High | RBI reference rate |
| DXY proxy | Finnhub / Twelve Data (`FINNHUB_API_KEY` / `TWELVE_DATA_API_KEY`) | 1h–1d | Paid tiers | Medium | Synthetic from EURUSD+ |
| VIX | Finnhub / Twelve / FRED `VIXCLS` | 1d | Low | High | FRED |
| India VIX | Groww / NSE via existing market stack | 1d | Existing Groww token | Medium | NSE bhav copy |
| PMI | Manual calendar + FMP/Finnhub economic calendar | Event | Med | Med | Cached last print |
| Claims / NFP | FRED / Finnhub calendar | Event / 1d | Low | High | FRED |
| Credit spreads | FRED `BAMLH0A0HYM2` | 1d | Free | High | Proxy EMBI if needed |
| Baltic Dry | Dedicated freight API or manual | 1d–1w | Med | Low–Med | Optional until licensed |
| Global M2 proxy | FRED monetary aggregates basket | 1w | Free | Medium | Liquidity score without M2 |
| CB statements | Federal Reserve / RBI HTML → NLP | Event | Free | Medium | Human CMS override |
| Surprise index | Optional paid (Citi) | 1d | High | High | Print vs consensus table |

**AGI env vars (existing + planned):**  
`FRED_API_KEY`, `ALPHAVANTAGE_API_KEY`, `INDIANAPI_KEY`, `FINNHUB_API_KEY`, `TWELVE_DATA_API_KEY`, `FMP_API_KEY` (optional), `RBI_DATA_API_KEY` (optional), `OPENAI_API_KEY` (narrative only), `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

---

# 6. Features

Feature store path: `e01_features` table + in-memory `FeatureVector` for live run.

| feature_id | Definition (engineering) | Source inputs |
|------------|--------------------------|---------------|
| `yc_slope_us` | `US_DGS10 - US_DGS2` | yields |
| `yc_slope_in` | `IN_GSEC10 - IN_SHORT` | yields |
| `yc_inversion_us` | `1{yc_slope_us < 0}` | slope |
| `real_yield_us` | `US_DGS10 - US_CORE_CPI_YOY` | yields, CPI |
| `infl_yoy_us` | CPI YoY | CPI |
| `infl_yoy_in` | India CPI YoY | CPI |
| `infl_momentum_us` | Δ CPI YoY (3m) | CPI |
| `infl_surprise_us` | print − consensus | CPI, consensus |
| `pmi_us` | level | PMI |
| `pmi_in` | level | PMI |
| `pmi_momentum_us` | Δ PMI (3m) | PMI |
| `growth_impulse` | z(PMI basket + copper z + BDI z) | growth, cmdty |
| `oil_mom_63d` | 63d log return WTI | WTI |
| `gold_mom_63d` | 63d log return Gold | Gold |
| `copper_mom_63d` | 63d log return Copper | Copper |
| `cmdty_infl_basket` | z(oil)+z(food proxy) | cmdty |
| `cmdty_growth_basket` | z(copper)+z(BDI) | cmdty |
| `usd_mom_63d` | 63d return DXY proxy | FX |
| `usdinr_mom_63d` | 63d return USDINR | FX |
| `usd_strength` | z(usd_mom) | FX |
| `liq_trend` | z(Δ global_M2_proxy, Δ real_yield inverted) | liq |
| `policy_rate_us` | Fed funds | CB |
| `policy_rate_in` | Repo | CB |
| `policy_velocity_us` | Δ Fed funds over 90d | CB |
| `vix_level` | VIX | vol |
| `vix_pctile_5y` | percentile rank | vol |
| `india_vix_level` | India VIX | vol |
| `rv_equity_20d` | 20d realised vol Nifty/SPX | equity |
| `hy_oas` | HY OAS | credit |
| `credit_stress` | z(hy_oas) | credit |
| `risk_appetite` | −z(vix) −z(hy) −z(usd_mom) +z(copper_mom) | composite |
| `stress_index` | w1·vix_pctile + w2·credit_z + w3·curve_stress | composite |
| `surprise_composite` | 0.5·US + 0.5·IN surprise z | surprise |
| `earn_density` | results per week / norm | calendar |
| `rate_real_impulse` | Δ real_yield_us 20d | rates |

**Normalisation standard:** rolling 5y winsorize 1–99%, then z-score; binary flags uncapped `{0,1}`.

---

# 7. Mathematical Models

## 7.1 Core transforms

**Log return**  
\( r_{t,n} = \ln(P_t / P_{t-n}) \)

**Z-score**  
\( z_t = (x_t - \mu_{t,w}) / \sigma_{t,w} \), window \( w = 252 \times 5 \) business days when available; else expanding from 252.

**Percentile rank**  
\( pct_t = \mathrm{rank}(x_t) / N \) over trailing window.

## 7.2 Feature formulas, ranges, thresholds

| Feature | Formula | Norm | Range (typ.) | Bullish / supportive risk | Bearish / stress | Conf. weight |
|---------|---------|------|--------------|---------------------------|------------------|--------------|
| `yc_slope_us` | 10Y−2Y | raw bps/100 | −1.5…+2.5 | > +0.5 steepener (mid-cycle) | < 0 inversion | 0.08 |
| `real_yield_us` | 10Y−core CPI | raw | −2…+3 | Rising with growth | Spike with growth collapse | 0.07 |
| `infl_momentum_us` | Δ YoY 3m | z | −3…+3 | z<−0.5 disinflation | z>+1 reaccel | 0.08 |
| `pmi_us` | level | raw | 40–60 | >52 | <48 | 0.08 |
| `growth_impulse` | z-basket | z | −3…+3 | >+0.5 | <−0.5 | 0.10 |
| `oil_mom_63d` | log ret | raw | −0.4…+0.4 | mild + with growth | >+0.25 shock | 0.06 |
| `usd_mom_63d` | ret | raw | −0.15…+0.15 | falling USD risk-on | rising USD risk-off | 0.06 |
| `liq_trend` | z | z | −3…+3 | >+0.5 | <−0.5 | 0.09 |
| `vix_pctile_5y` | pctile | 0–1 | 0–1 | <0.4 | >0.8 | 0.10 |
| `risk_appetite` | composite z | z | −3…+3 | >+0.5 risk_on | <−0.5 risk_off | 0.12 |
| `stress_index` | weighted | 0–1 | 0–1 | <0.35 | >0.7 crisis watch | 0.10 |
| `hy_oas` | bps | z | — | z<0 | z>+1 | 0.06 |

**Historical behaviour notes (implementation comments):**  
- Curve inversion: lead recession signal (US) with long & variable lags — never used alone.  
- VIX percentile: mean-reverting; crisis = persistence above 0.9.  
- Oil shock flag: `oil_mom_63d > 0.25` AND `infl_momentum_us > 0`.

## 7.3 Submodel scores

Each submodel maps features → `score ∈ [-2,+2]`:

\[
s_m = \mathrm{clip}\Big(\sum_i w_{m,i}\, z(f_i),\, -2,\, 2\Big)
\]

Weights versioned in `e01_model_weights` (JSON), default equal within model.

## 7.4 Axis classifiers (threshold layer)

Example `R_VOL`:
```
if stress_index >= 0.85 or vix_pctile_5y >= 0.95: crisis_vol
elif vix_pctile_5y >= 0.75: high_vol
elif vix_pctile_5y <= 0.25: low_vol
else: normal_vol
```

Example `R_CYCLE` (India+US blend):
```
growth = 0.5*z(pmi_us)+0.5*z(pmi_in)+0.25*growth_impulse
if growth > 0.5 and pmi_us>50 and pmi_in>50: expansion
elif growth < -0.7 or pmi_us<47: recession
elif prior in {recession,slowdown} and growth rising: recovery
else: slowdown
```

## 7.5 HMM ensemble (statistical layer)

**Model:** Gaussian HMM, `n_states=4` on feature vector  
`[growth_impulse, infl_momentum_us, liq_trend, risk_appetite, yc_slope_us]`  
weekly sampling.

| Hidden state | Mapped label |
|--------------|--------------|
| 0 | recovery / early expansion |
| 1 | late expansion |
| 2 | slowdown |
| 3 | stress / recession |

**Training:** walk-forward, expanding window, min 8y weekly history when available; recalibrate quarterly job.

**Fusion:**  
\[
P(\mathrm{axis}) = 0.55\, P_{\mathrm{threshold}} + 0.45\, P_{\mathrm{HMM}}
\]
Emit `confidence = 1 - entropy(P)`.

## 7.6 Macro Score

\[
\mathrm{MacroScore} = 50 + 10\cdot\mathrm{clip}(
  0.25\cdot s_{\mathrm{growth}}
  + 0.15\cdot s_{\mathrm{liq}}
  - 0.15\cdot s_{\mathrm{infl\_stress}}
  + 0.20\cdot s_{\mathrm{risk}}
  - 0.15\cdot s_{\mathrm{stress}}
  + 0.10\cdot s_{\mathrm{policy\_ease}}
,\, -3,\, 3)
\]
Range **[20, 80]** typical; hard clip **[0, 100]**.

Interpretation: higher = more supportive for risk research sleeves (not a buy signal).

## 7.7 Position size multiplier & vol target

```
if R_STRESS == crisis:      size_mult = 0.35; vol_target = 0.06
elif R_VOL == high_vol:     size_mult = 0.60; vol_target = 0.08
elif R_RISK == risk_off:    size_mult = 0.70; vol_target = 0.09
elif R_RISK == risk_on and R_VOL == low_vol:
                            size_mult = 1.15; vol_target = 0.12
else:                       size_mult = 1.00; vol_target = 0.10
```
`size_mult` is a **research book scaler** for downstream engines, not broker order size.

---

# 8. Machine Learning

| Technique | Use | Library | Notes |
|-----------|-----|---------|-------|
| Gaussian HMM | Latent regime | `hmmlearn` | Primary statistical detector |
| Ordered logit / gradient boosting classifier | Axis labels from features | `sklearn` / `lightgbm` | Supervised vs historically labeled eras |
| Bayesian model average | Fuse threshold + HMM + GBM | custom | Posterior weights by recent log-score |
| Elastic net regression | MacroScore components | `sklearn` | Interpretable |
| SHAP | Feature importance | `shap` | CIO explainability |
| NLP classifier | CB statement hawk/dove | small transformer or keyword+LLM assist | OpenAI optional; store score only |

**Explainability requirements**
- Every live state must ship `top_features[5]` with signed contributions.  
- No black-box-only promotion to CIO brief.  
- LLM may narrate; **cannot** set regime alone.

**Feature importance job:** weekly, store in `e01_feature_importance`.

---

# 9. Outputs

## 9.1 Canonical output contract `E01State`

```json
{
  "engine": "E01",
  "version": "1.0.0",
  "as_of": "2026-07-25T10:30:00+05:30",
  "macro_score": 62.4,
  "primary_regime": "expansion_risk_on",
  "axes": {
    "R_MARKET": {"state": "bull", "confidence": 0.71},
    "R_VOL": {"state": "normal_vol", "confidence": 0.66},
    "R_RISK": {"state": "risk_on", "confidence": 0.68},
    "R_INFL": {"state": "disinflationary", "confidence": 0.60},
    "R_CYCLE": {"state": "expansion", "confidence": 0.64},
    "R_LIQ": {"state": "liq_neutral", "confidence": 0.55},
    "R_POLICY": {"state": "on_hold", "confidence": 0.70},
    "R_EARN": {"state": "post_earnings", "confidence": 0.80},
    "R_STRESS": {"state": "normal", "confidence": 0.75}
  },
  "confidence": 0.67,
  "risk_level": "moderate",
  "size_multiplier": 1.0,
  "vol_target": 0.10,
  "weight_adjustments": {
    "E03_xs_momentum": 1.10,
    "E04_stat_arb": 0.90,
    "E09_trend": 1.05,
    "E08_short_vol_research": 0.70,
    "E08_tail_hedge_research": 1.20,
    "E02_value": 1.00,
    "E02_quality": 1.05,
    "E10_risk_parity": 1.00
  },
  "submodels": {},
  "top_features": [],
  "falsifiers": ["VIX pctile > 0.85", "HY OAS z > 1.5"],
  "stale_inputs": [],
  "hash": "sha256:..."
}
```

`risk_level` ∈ `low|moderate|elevated|critical` from `stress_index` bands.

## 9.2 Compatibility shim for existing UI

Map into current `workspace.regime`:

| Legacy field | E01 source |
|--------------|------------|
| `macroRegime` | `Constructive` if macro_score≥55 else `Cautious` (or richer labels later) |
| `confidence` | `round(confidence*100)` |
| `cycle` | `axes.R_CYCLE.state` |
| `inflation` | map `R_INFL` |
| `policy` | map `R_POLICY` |
| `liquidity` | map `R_LIQ` |
| `volatility` | map `R_VOL` |
| `riskEnvironment` | map `R_RISK` |

---

# 10. Downstream Consumers

| Engine | On `risk_on` + `expansion` + `normal/low_vol` | On `risk_off` / `high_vol` | On `crisis` |
|--------|-----------------------------------------------|---------------------------|-------------|
| **E09 Trend** | `weight×1.05–1.20`; tighten entry | `weight×0.7`; longer confirmation | `weight×0.35` or disable new trends |
| **E03 Momentum** | Increase XS momentum book | Cut momentum; raise quality filter | Flat / defensive only |
| **E04 Stat Arb** | Slightly reduce (trend dominates) | **Increase** mean-reversion weight; widen z-entry | Disable fragile pairs; only hardest cointegration |
| **E10 Portfolio** | `vol_target` 10–12%; size_mult↑ | `vol_target` 7–9%; favour RP | `vol_target` 5–7%; max cash/hedge sleeve in research allocation |
| **E08 Options** | Lower short-vol research emphasis | Raise tail-hedge research; reduce short-vol | Tail scenarios primary |
| **E14 Risk** | Standard limits | Cut gross limits 20–40% | Hard de-risk playbook |
| **E02 Factors** | Momentum/value balanced | Quality + low-vol factors ↑ | Quality/defensive only |
| **E05 Event** | Normal deal spreads | Raise break probabilities | Stress deal-break scenarios |
| **E13 L/S Desk** | Net exposure research band +10–20% | Net band −20–40%; raise short quality | Near-neutral / hedge overlay |

**Contract:** Downstream engines **must** read `E01State.weight_adjustments[engine_id]` and multiply sleeve scores; they may not invent parallel regime logic except local microstructure flags.

---

# 11. Database Design

## 11.1 Reuse
- `macro_dataset_cache` — raw pulls  
- `macro_observation_history` — point history  
- `macro_briefing_cache` — activate for briefing blob (currently underused)

## 11.2 New tables

```sql
-- E01 feature snapshots (point-in-time)
CREATE TABLE e01_feature_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  as_of timestamptz NOT NULL,
  feature_id text NOT NULL,
  value double precision,
  z_value double precision,
  meta jsonb DEFAULT '{}',
  UNIQUE (as_of, feature_id)
);
CREATE INDEX e01_feature_asof_idx ON e01_feature_snapshot (as_of DESC);
CREATE INDEX e01_feature_id_idx ON e01_feature_snapshot (feature_id, as_of DESC);

-- E01 regime state time series
CREATE TABLE e01_regime_state (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  as_of timestamptz NOT NULL UNIQUE,
  macro_score double precision NOT NULL,
  primary_regime text NOT NULL,
  axes jsonb NOT NULL,
  confidence double precision NOT NULL,
  risk_level text NOT NULL,
  size_multiplier double precision NOT NULL,
  vol_target double precision NOT NULL,
  weight_adjustments jsonb NOT NULL,
  top_features jsonb NOT NULL DEFAULT '[]',
  falsifiers jsonb NOT NULL DEFAULT '[]',
  submodels jsonb NOT NULL DEFAULT '{}',
  model_version text NOT NULL,
  input_hash text NOT NULL,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX e01_regime_primary_idx ON e01_regime_state (primary_regime, as_of DESC);

-- Current pointer
CREATE TABLE e01_regime_current (
  id text PRIMARY KEY DEFAULT 'current',
  state_id uuid REFERENCES e01_regime_state(id),
  state jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Weight / calibration versions
CREATE TABLE e01_model_weights (
  version text PRIMARY KEY,
  weights jsonb NOT NULL,
  notes text,
  created_at timestamptz DEFAULT now(),
  is_active boolean DEFAULT false
);

CREATE TABLE e01_feature_importance (
  as_of date NOT NULL,
  feature_id text NOT NULL,
  importance double precision NOT NULL,
  method text NOT NULL,
  PRIMARY KEY (as_of, feature_id, method)
);

CREATE TABLE e01_validation_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at timestamptz,
  finished_at timestamptz,
  method text,
  metrics jsonb,
  model_version text
);
```

RLS: public read on `e01_regime_current` + latest state; service role write.

## 11.3 Caching
| Layer | TTL |
|-------|-----|
| Raw dataset cache | existing `MACRO_REFRESH_MS` |
| Feature snapshot | on each E01 run |
| `e01_regime_current` | overwritten each run; CDN Cache-Control 60s on API |
| Redis (optional) | `e01:state:current` 60s |

---

# 12. Backend

## 12.1 Package layout

```
intelligence-engine/app/engines/e01/
  __init__.py
  config.py
  pipeline.py          # orchestrator
  schema.py            # E01State pydantic
  features/
    registry.py
    transforms.py
    builder.py
  submodels/
    cycle.py
    liquidity.py
    central_bank.py
    yield_curve.py
    inflation.py
    currency.py
    commodity.py
    risk_appetite.py
    surprise.py
    growth.py
    volatility.py
    earnings.py
  models/
    thresholds.py
    hmm_regime.py
    fusion.py
    macro_score.py
    sizing.py
  adapters/            # pull from Node / FRED / etc.
    agib_macro.py
    fred.py
  persistence.py
  explain.py
```

Node gateway routes:

```
GET  /api/intelligence/e01/state          -> current E01State
GET  /api/intelligence/e01/history?limit=
POST /api/intelligence/e01/run            -> admin/service trigger
GET  /api/intelligence/e01/features
```

Proxy pattern: same as existing `server/routes/intelligence.js`.

## 12.2 Pipeline steps (`pipeline.run_e01`)

1. Acquire inputs (adapters; mark stale)  
2. Build features → persist snapshot  
3. Run submodels (parallel `asyncio.gather`)  
4. Threshold classifiers  
5. HMM infer (if model present; else skip with flag)  
6. Fuse axes + macro_score + sizing  
7. Explain top features  
8. Persist `e01_regime_state` + `e01_regime_current`  
9. Publish shim into macro briefing rebuild trigger  
10. Emit metrics (latency, stale count)

## 12.3 Jobs / cron (IST)

| Job | Schedule | Action |
|-----|----------|--------|
| `e01_intraday` | 08:45, 12:30, 15:45 IST weekdays | Full run |
| `e01_daily_close` | 16:30 IST weekdays | Full run + history seal |
| `e01_sunday_recal` | Sunday 18:00 IST | HMM light recalibration check |
| `e01_monthly_validate` | 1st 19:00 IST | Validation harness |
| Existing macro briefing scheduler | keep 6h | **Must read E01 current state** |

Workers: FastAPI service in `agib-intelligence-engine`; Node `cioMorningScheduler` waits on E01 health.

## 12.4 SLOs
- Run latency p95 < 45s  
- Output freshness < 6h in market week  
- If stale_inputs > 40%: `confidence *= 0.7`, flag `degraded=true`

---

# 13. Frontend (Bloomberg-quality)

Extend `/macro-intelligence` + optional `/beta/e01`.

## 13.1 Widgets

1. **Regime Hero** — primary regime, macro score gauge (0–100), confidence, risk level, as-of  
2. **Axis Heatmap** — 9 axes × state colour cells  
3. **Regime Timeline** — 5y stacked state ribbon (brushable)  
4. **Macro Score Strip** — sparkline + drivers waterfall (top features)  
5. **Submodel Panel** — 12 cards with score needles  
6. **Liquidity & Curve Panel** — yc slope, real yield, liq_trend  
7. **Inflation & Commodities** — CPI vs oil/copper  
8. **Risk Dashboard** — VIX pctile, HY OAS, stress index, size_mult, vol_target  
9. **Downstream Impact** — table of `weight_adjustments` per engine  
10. **Falsifiers** — checklist of break conditions  
11. **Data Health** — source latency / missing keys  

## 13.2 Visual language
- Colours: risk-on green `#0F7A4A`, risk-off red `#B42318`, neutral `#667085`, AGI navy `#0A1E38`  
- No retail candles as primary; prefer ribbons, heatmaps, sparklines  
- Every widget footnotes `as_of` + `model_version`

## 13.3 API bindings
```ts
getE01State(): Promise<E01State>
getE01History(limit: number)
```

---

# 14. Validation

## 14.1 Backtesting
- Reconstruct weekly E01State over max available history (target ≥10y global; India shorter OK).  
- Metrics vs subsequent 13w / 26w asset returns (Nifty, SPX, USDINR, Gold, US10Y).  
- Regime purity: average forward Sharpe of risk_on vs risk_off sleeves.

## 14.2 Walk-forward
- Expanding train, annual re-cal HMM; embargo 1 month.  
- Report degradation vs in-sample.

## 14.3 Stress tests
Replay: GFC, Taper 2013, COVID crash/recovery, 2022 inflation shock.  
Assert: `crisis` or `high_vol`+`risk_off` triggers within 2 weeks of event onset.

## 14.4 Cross-validation
- Time-series CV (purged K-fold à la Lopez de Prado) for supervised axis classifiers.

## 14.5 Accuracy targets (research-grade, not marketing)
| Metric | Target |
|--------|--------|
| Crisis capture recall (labeled stress windows) | ≥ 0.80 |
| False crisis rate | ≤ 0.10 of weeks |
| Risk_on/off hit rate vs subsequent 4w equity sign | ≥ 0.55 |
| Stability: regime flips / year | tracked; investigate if > 20 |

Store runs in `e01_validation_runs`.

---

# 15. Future Enhancements

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| Alt-data growth nowcasts | Card transactions, night lights | P2 |
| Satellite agri for India inflation | Crop health → food CPI | P2 |
| LLM reasoning layer | Debate falsifiers; cannot set state | P1 |
| RL meta-controller | Learn `size_multiplier` policy under constraints | P3 |
| Dynamic weight optimisation | Online Bayesian update of fusion weights | P2 |
| Cross-country HMM | US/EU/IN coupled regimes | P2 |
| Options surface features | Skew/term-structure into SM_VOL | P1 when data ready |
| Real-time push | WebSocket regime changes to Beta | P2 |

---

# 16. Implementation phases (engineering)

| Phase | Scope | Exit criteria |
|-------|-------|---------------|
| **P0** | Feature builder on existing macroContext + FRED/AV; threshold axes; E01State API; shim into `workspace.regime` | Live state on Macro UI |
| **P1** | All 12 submodels; weight_adjustments consumed by E03/E09/E10 stubs; regime history table | Downstream reads E01 |
| **P2** | HMM + validation harness + timeline UI | Stress recall targets measured |
| **P3** | NLP CB scores, surprise feeds, alt-data | Confidence uplift |

---

# 17. Non-functional requirements

- Deterministic given inputs + model_version (seeded HMM)  
- Full audit: `input_hash`, model_version, timestamps  
- Secrets only in server/engine env  
- Explainability mandatory for CIO  
- India + US dual lens on every major axis  

---

# 18. Acceptance tests (sample)

1. Given fixture `fixtures/e01/covid_2020_03.json`, output `R_STRESS=crisis` or `crisis_vol` with confidence ≥ 0.6.  
2. Given low VIX + rising PMI fixture, `R_RISK=risk_on`, `size_multiplier ≥ 1.0`.  
3. API `GET /e01/state` returns schema-valid JSON in < 300ms when current cache warm.  
4. Turning off FRED key marks `stale_inputs` and reduces confidence.  
5. `workspace.regime.cycle` matches `axes.R_CYCLE.state` after shim.

---

*End of E01 Macro & Regime Engine Specification v1.0*
