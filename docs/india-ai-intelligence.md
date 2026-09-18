# India AI Intelligence

**Product specification — AGI Investment Intelligence**
Status: design. Nothing in this document is live until Phase 1 ships.

---

## 0. The source constraint, and why the universe is ours

This product was commissioned after reading a Goldman Sachs India strategy note on
Indian AI-infrastructure equities. That note is licensed per-seat and its terms say, in
the document itself, that the information may not be reverse engineered to develop any
index for disclosure or marketing, nor used to create derivative works or commercial
products. Nothing from the licensed note is used as data: not its figures, exhibits,
consensus tables, weights, returns, company-to-layer classifications or prose. Its
nine-sub-layer taxonomy was the starting point for AGI's own, and that is recorded
below as a weakness, not a strength.

**Third-party lists are leads, never membership.** On 18 September 2026 a list of 42
companies, reported by The Economic Times as named in that screen and relayed to the
analyst in a ChatGPT summary, was used as a reading queue. AGI could not open the
article, so the list is stored as relayed and unverified, in `externalLeads` in the
universe config. What that means in practice:

- Being on the list admits no one and decides no layer, sector, weight or date. Each of
  the 42 was read in its own filings against AGI's evidence standard: 24 admitted, 12
  held, 6 with nothing qualifying.
- The list itself is not returned by the public API. Each company read because of it
  carries `discoveredVia: EXTERNAL_LEAD_2026_09_18`, which *is* returned, so the
  provenance of every such decision is visible rather than hidden.
- Public availability of a document is not a licence to redistribute it. Third-party
  industry estimates quoted inside company filings are not, by that fact, permitted
  chart inputs.

**Every decision keeps four dates apart:** the disclosure date of the evidence, the date
AGI read it (`evidenceReadOn`), the date AGI decided (`membershipStart`), and, when it
happens, the exit date. Finding older evidence never creates earlier membership.

Every figure on the page must therefore carry a provenance tag, and the page must be able
to say it has nothing rather than show a number it cannot source:

| tag | meaning |
|---|---|
| `LIVE` | Upstox market feed, this session |
| `DERIVED` | computed by AGI from `LIVE` or `FILED` inputs, formula shown |
| `FILED` | company filing, exchange announcement, or transcript, with citation |
| `AGI` | AGI's own judgement or classification, with the evidence that produced it |
| `NEEDED` | the metric is specified but no source is wired yet |

A panel with no data renders `NEEDED` and names the source it wants. It does not render a
plausible number.

---

## PART 1 — What the theme actually is

Stripped to what matters for building a product, the investable claim has four parts, and
each one implies something the product must do.

**1. India's benchmark under-represents the theme.** The large-cap index is weighted
towards banks, energy and consumer names. The companies that build AI infrastructure —
switchgear, transformers, transmission, data centre shells, servers, assembly and test —
are mostly mid, small and micro caps. A cap-weighted index cannot express the theme, which
is precisely why a purpose-built basket has a reason to exist.
→ *The product must construct and maintain its own basket, and must justify its weighting.*

**2. The evidence arrives as language before it arrives as revenue.** A transformer maker
does not report an "AI" revenue line. It reports orders, and its management starts saying
words it did not say two years ago — hyperscaler, liquid cooling, GPU cluster, substation,
power purchase agreement. That vocabulary shift is observable in transcripts quarters
before it is observable in financials.
→ *The product must read transcripts, and must rank a new phrase below a signed order.*

**3. The move is earnings-led or it is not durable.** A basket can rise because estimates
rose or because the multiple rose. Those are different trades with different risks, and
the difference is measurable: decompose total return into the part explained by changes in
forward EPS and the part explained by changes in forward multiple.
→ *The product must decompose return into earnings and multiple, continuously.*

**4. The bottleneck is physical.** Compute needs megawatts, and megawatts need
transmission, transformers and substations. Data centre capacity announced is not data
centre capacity energised. A pipeline that outruns the grid is the risk the theme carries.
→ *The product must track announced megawatts against the power infrastructure being built
to serve them, and must be able to say when one is outrunning the other.*

Everything below follows from those four.

---

## PART 2 — Product architecture

```
                         ┌────────────────────────────────────────────┐
                         │  AGI INDIA AI INTELLIGENCE                 │
                         └────────────────────────────────────────────┘

  INGEST                    RESOLVE                 COMPUTE              SURFACE

  Upstox WS v3  ──┐                             ┌─ index engine ──┐
  (already built) │     ┌─ universe screen ─┐   │  attribution    │   ┌─ research
  Upstox REST  ───┼────▶│  public data only │──▶├─ signal engine  │──▶├─ live monitor
  NSE/BSE feeds ──┤     │  rerunnable       │   │  revision gap   │   ├─ watchlist
  transcripts  ───┤     └───────────────────┘   │  order impact   │   ├─ company page
  filings      ───┘                             └─ evidence store ┘   └─ alerts
```

Five services, each with one job:

| service | job | already exists |
|---|---|---|
| `aiEnablersUniverse` | run the screen, emit the universe, version it | no |
| `aiEnablersIndex` | basket levels, returns, attribution by layer and name | no |
| `aiSignalEngine` | classify observations into signals, attach evidence | no |
| `aiEvidenceStore` | every signal's supporting rows, immutable | no |
| `upstoxMarketFeedV3` | live ticks, protobuf decode, reconnect | **yes** |

The last one matters more than it looks. `server/services/upstoxMarketFeedV3.js` already
handles authorisation, the protobuf `FeedResponse` type, a synchronised snapshot store,
auth-error classification and reconnect; `liveAlphaRuntime.js` already loads a universe
file, maps members to sector indices and falls back to a second provider when the socket
drops. The live half of this product is wiring, not construction.

### The hierarchy the page is built on

```
THEME  →  LAYER  →  SUB-LAYER  →  COMPANY  →  MARKET BEHAVIOUR
                                          →  FUNDAMENTAL CHANGE
                                          →  CATALYST
                                          →  EVIDENCE
                                          →  RISK
```

Every panel sits at exactly one level and links down. Nothing on the page is a number
without a level.

---

## PART 9 — The universe, and how AGI derives it

*(Presented before the UI parts because everything else depends on it.)*

### Taxonomy

Three layers, nine sub-layers. The decomposition follows how the industry itself is
organised — generation, transmission and equipment on the power side; shell, operation and
hardware on the data centre side; assembly, materials and hardware on the silicon side.

| layer | sub-layer | admits a company that… |
|---|---|---|
| Power | Generation | sells electricity, or contracts capacity to a data centre |
| | Transmission | builds or operates transmission, substations, HVDC |
| | Equipment | makes transformers, switchgear, cable, gensets, drives |
| Data Centre | Developer | builds the shell, holds the land, does the EPC |
| | Operator | owns and runs capacity, sells colocation or cloud |
| | Hardware | makes servers, racks, cooling, networking, fibre |
| Semiconductor | OSAT | assembles, packages, tests |
| | Materials | supplies chemicals, gases, substrates, wafers |
| | Hardware | supplies fab or test equipment |

A company may sit in two sub-layers. It is admitted to each on its own evidence, and its
index weight is split, not doubled.

A company may also be admitted and sit in **no** sub-layer. KEC International builds the
data centre and the semiconductor fab; the evidence is first-party and hard, and
"Developer" here means the owner of the campus, not the contractor who pours it. The
taxonomy has no slot for the builder. Such a member is held as a candidate rather than
forced into the nearest box, and the index reconciles its sub-layer breakdown separately
from its name breakdown so that a member with nowhere to go shows up as a shortfall
instead of disappearing.

### Coverage, as of 2026-09-17

Seven admitted, eleven candidates. Two sub-layers are empty and that is the finding, not a
gap to fill: India's semiconductor materials and fab-equipment layers are pre-revenue.
Every company found in them — Aether Industries developing low-dielectric monomers, Tanfac
"just evaluating various technologies", Centum claiming semiconductor-equipment capability
with no segment split — talks about the opportunity and discloses nothing done. Admitting
any of them would mean admitting on intent, which is the one thing this screen refuses.

| sub-layer | admitted |
|---|---|
| Power → Generation | CLEANMAX |
| Power → Transmission | POWERINDIA |
| Power → Equipment | POWERINDIA |
| Data Centre → Developer | ADANIENT, ANANTRAJ |
| Data Centre → Operator | ADANIENT, ANANTRAJ |
| Data Centre → Hardware | NETWEB |
| Semiconductor → OSAT | CGPOWER, KAYNES |
| Semiconductor → Materials | *(empty — nothing disclosed beyond intent)* |
| Semiconductor → Hardware | *(empty — nothing disclosed beyond intent)* |

**The two empty sub-layers have been checked against an independent screen.** That screen
asked the same question with a materially lower bar for AI exposure — company mentions in news
flow and management discussion, with partnerships counting as qualifying — and on that basis it
placed companies in both layers AGI reports empty. AGI had already examined those layers and
refused what it found: monomers being developed, technologies being evaluated, a capability claim
with no segment split, a product-positioning slide. The same companies, a different standard. The
empty layers are therefore a finding about what these companies disclose, not a gap in coverage.

A note on where the taxonomy came from: the three layers and nine sub-layers were derived from
published third-party research at the start of this build, not arrived at independently. An
independent screen using the same decomposition is not corroboration of it.

This is a partial universe from a partial pass: discovery ran over filing *content* via
semantic search, not over all ~2,300 NSE equities. Stages 2 and 3 have not run at all,
because their thresholds need the Upstox pass. The file says `status: "partial"` and the
page must say so too.

### The screen

Run monthly, and on demand. Every stage is reproducible from public data.

**Stage 1 — universe.** All NSE-listed equities. The repo already carries
`NIFTYstocks.csv` (~2,300 EQ/BE/SM), `Nifty500.csv` and `EQUITY_L.csv`.

Stage 1 now runs over all of `EQUITY_L.csv` (2,390 companies) and records one
outcome per company in `ai_enabler_universe_pass`:
`scripts/aiEnablersUniversePass.mjs` fetches each company's Upstox profile and
nominates it if its own business description names the plant a sub-layer is
about (`aiEnablersNomination.js`: transformers, switchgear, data centres,
servers, semiconductor packaging, and so on). **Nomination decides what is
read for Stage 4 evidence; it never admits.** The terms are broad on purpose,
since a false nomination costs one reading and a miss costs a member.

The pass measures its own blind spot. Every admitted member and held candidate
is a known qualifier, and any the pass fails to nominate is printed as a miss.
A company whose description omits the business that qualifies it will be
missed by this step; the miss rate on known qualifiers is the estimate of how
often, and a discovery route other than descriptions is still needed for
those. Companies with no ISIN, no profile, or a failed call are recorded as
such and are never counted as "not nominated". A run below 95% of addressable
companies is DEGRADED.

**First full run, 2026-09-18 (main board only).** 2,390 companies; 97.2% examined, no
failed calls, 67 without an Upstox profile; 495 nominated. Of the 18 known qualifiers,
13 were nominated. The five misses had three causes, and only one was the nomination
rules: CLEANMAX has no Upstox profile; AETHER's description says "specialty chemicals",
which no semiconductor-materials term matches; ESDS, Supreme Power and Tanfac were not
on the main-board list at all. Supreme Power is on NSE Emerge, so the SME list
(`SME_EQUITY_L.csv`, 572 companies) is now read too. ESDS and Tanfac appear on neither
NSE list, and a universe defined as NSE equities cannot contain them.

A check against obvious names found two kinds of miss. Wording the terms lacked - NTPC's
"generation and sale of bulk power", Blue Star's "air conditioning", Amara Raja's
"lead-acid batteries" - is now covered and pinned by tests. A business run through a
subsidiary the description does not name - Bharti Airtel's data centres in Nxtra - cannot
be found from descriptions at all, and needs another route.

Nominations are read in the order `readingPriority` gives: strong (the sector makes the
plant named), contractor (EPC only), incidental (a textile mill's captive windmill).
The order decides what is read first. Nothing is dropped from the list.

**Stage 2 — size and tradability.** Free-float market cap above a floor, and median daily
turnover above a floor, both measured over six months from Upstox history. Thresholds are
AGI's, stored in config, and printed on the page. A screen whose cut-offs are hidden is a
screen nobody can argue with, which makes it useless.

**Stage 3 — investment intensity.** Any one of: three-year revenue CAGR above the universe
median; capex growth above median; capex/sales above median; R&D/sales above median. This
stage is a filter for companies that are *building*, which is what an infrastructure theme
requires. Source: `company_facts` (the fact store built earlier in this repo), which
already refuses figures it cannot cite.

**Stage 4 — evidence of AI exposure.** This is the stage that decides membership, and it
is the stage that must never be a keyword count alone. A company is admitted on **at least
one hard item**, corroborated:

| evidence | weight | why |
|---|---|---|
| signed order naming a data centre, hyperscaler, or semiconductor project | hard | contractual |
| disclosed capex for an AI-relevant facility | hard | capital committed |
| operating disclosure: segment revenue, MW energised, racks shipped, wafers packaged | hard | physical |
| partnership or MoU with a named counterparty | soft | intent |
| transcript vocabulary appearing for the first time | soft | earliest, weakest |

Both halves have a source: Trendlyne, already connected to this workspace. Its news
endpoint returns Reg 30 (LODR) exchange filings, and its document search covers earnings
call transcripts and investor presentations. `aiEnablersEvidence.js` implements the
classification; see below for what it does to a real feed.

Two rules the classifier enforces that a keyword count cannot:

- **A capital raise is not evidence.** It is the most common false positive — exciting,
  price-moving, often reported beside AI commentary, and silent about what the company
  builds. It is classified explicitly so the reason is visible.
- **"AI" alone does not make a filing relevant.** Every company says it. The terms that
  carry information describe plant: racks, substations, packaging lines, megawatts. An
  order that "will use AI to improve efficiency" is not AI-infrastructure evidence.

Run against Netweb Technologies' real announcement feed, the last fortnight classifies as
four routine filings and one fundraise — **no evidence at all**, for a company that is
unambiguously an AI infrastructure business. Its investor presentation is what admits it:
AI Systems at 62.29% of revenue is an operating disclosure, and places it in data centre
hardware. That gap between a company's obvious identity and its recent filings is the
reason admission runs on a body of evidence over time rather than on a rolling window.

**Soft evidence alone never admits a company.** It raises a candidate to a watchlist that a
human reviews. This is the single most important rule in the screen: the cheapest way to
build a fake AI index is to count the word "AI" in transcripts.

**Stage 5 — exclusion review.** A named analyst removes companies whose exposure is
immaterial to earnings, records the reason, and the reason is stored. Removals are as
auditable as admissions.

### Output

```json
{
  "version": "2026-09-17",
  "benchmarkKey": "NSE_INDEX|Nifty 50",
  "thresholds": { "minMarketCapUsd": 0, "minAdvtUsd": 0, "…": "set in config" },
  "members": [
    {
      "symbol": "",
      "instrumentKey": "NSE_EQ|",
      "layer": "power|data_centre|semiconductor",
      "subLayer": "",
      "weightSplit": { "power_equipment": 1.0 },
      "admittedOn": [{ "type": "order", "date": "", "source": "", "excerpt": "" }],
      "reviewedBy": "",
      "reviewedAt": ""
    }
  ]
}
```

This is the same shape `liveAlphaRuntime.loadLiveAlphaUniverse` already consumes, plus the
layer fields and the admission evidence. It drops into the existing feed with no changes to
the socket layer.

**This file ships empty.** It is populated by running
`server/scripts/screenAiEnablers.mjs`, which reads public data and writes the result. No
member is hand-entered, because a hand-entered member is a claim nobody can reproduce.

### Weighting

Two constructions, both computed, one displayed.

- **Equal-weighted** — every member 1/N, rebalanced monthly.
- **Free-float cap-weighted** — capped at 10% per name, 40% per layer.

**Display equal-weighted by default.** The theme's information is in the small and mid
caps; a cap-weighted version of this basket is a bet on its three largest members and will
track them, not the theme. The cap-weighted line is shown alongside so the gap between them
is visible — that gap *is* the size skew, and it is worth watching. Both are labelled.
Neither is called "the" index without saying which.

---

## PART 3 — Desktop layout

One screen, 65/35, monitor sticky, research scrolls.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ AGI   Research  Markets  Intelligence  Companies  Themes  Portfolio   [search]│
├──────────────────────────────────────────────────────────────────────────────┤
│ Research › Themes › Artificial Intelligence › India AI Infrastructure        │
├───────────────────────────────────────────┬──────────────────────────────────┤
│                                           │ INDIA AI INTELLIGENCE MONITOR    │
│  India's Hidden AI Infrastructure Trade   │ ● LIVE · NSE OPEN  14:42 IST     │
│  The infrastructure opportunity beneath   │ ┌──────────────────────────────┐ │
│  India's laggard equity index             │ │ AGI AI ENABLERS  (equal-wt)  │ │
│                                           │ │ index · day% · YTD · vs Nifty│ │
│  ┌─ EXECUTIVE INTELLIGENCE ─────────────┐ │ │ layer sparklines ×3          │ │
│  │ five claims, each with its evidence  │ │ └──────────────────────────────┘ │
│  │ count and a link to it               │ │ ┌──────────────────────────────┐ │
│  └──────────────────────────────────────┘ │ │ TODAY'S MOVE — attribution   │ │
│                                           │ │ contribution in pp by layer  │ │
│  ┌─ RETURN DECOMPOSITION ───────────────┐ │ │ top 5 adds / top 5 drags     │ │
│  │ price vs forward EPS vs forward P/E  │ │ └──────────────────────────────┘ │
│  │ the earnings-vs-multiple question    │ │ ┌──────────────────────────────┐ │
│  └──────────────────────────────────────┘ │ │ EARNINGS REVISIONS  90d      │ │
│                                           │ │ upgrades / downgrades / gap  │ │
│  ┌─ THE THREE LAYERS ───────────────────┐ │ └──────────────────────────────┘ │
│  │ power · data centre · semiconductor  │ │ ┌──────────────────────────────┐ │
│  │ each: thesis, evidence, risk         │ │ │ ORDER FEED (live)            │ │
│  └──────────────────────────────────────┘ │ │ time · company · ₹ · impact  │ │
│                                           │ └──────────────────────────────┘ │
│  ┌─ POWER BEHIND AI ────────────────────┐ │ ┌──────────────────────────────┐ │
│  │ MW announced vs MW energised         │ │ │ DATA CENTRE PROJECTS         │ │
│  │ the bottleneck panel                 │ │ │ project · MW · status · ETA  │ │
│  └──────────────────────────────────────┘ │ └──────────────────────────────┘ │
│                                           │ ┌──────────────────────────────┐ │
│  ┌─ VALUATION VS GROWTH ────────────────┐ │ │ INTELLIGENCE HEATMAP 9×8     │ │
│  │ scatter, four quadrants, unlabelled  │ │ └──────────────────────────────┘ │
│  └──────────────────────────────────────┘ │ ┌──────────────────────────────┐ │
│                                           │ │ WATCHLIST (sortable)         │ │
│  ┌─ RISK REGISTER ──────────────────────┐ │ └──────────────────────────────┘ │
│  └──────────────────────────────────────┘ │                                  │
├───────────────────────────────────────────┴──────────────────────────────────┤
│ COMPANY INTELLIGENCE — full-width table, filters, export                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Why the monitor is on the right and sticky.** The research argues a position; the monitor
says whether it is still true this morning. A reader scrolling the argument must be able to
check it against the tape without losing their place. If the two ever disagree, that
disagreement is the most valuable thing on the page and it must be visible simultaneously.

**Quadrants are unlabelled.** The valuation-vs-growth scatter draws four quadrants and
names none of them "buy". Naming them converts a chart into advice.

---

## PART 4 — Mobile

Not a squeezed desktop. On a phone the monitor comes first, because a phone is what a
reader opens when something has moved.

```
┌───────────────────────┐   1  live strip (sticky): index, day%, breadth
│ ● LIVE  AGI AIE +1.8% │   2  today's move: attribution, three bars
├───────────────────────┤   3  what changed: orders + revisions, merged, newest first
│ TODAY'S MOVE          │   4  the argument: collapsed sections, expand on tap
│ ▇▇▇ power     +0.74pp │   5  watchlist: card per company, not a table
│ ▇▇  dc hw     +0.51pp │   6  risk register
│ ▇   semis     +0.32pp │
├───────────────────────┤   Tables become cards. A horizontally scrolling 18-column
│ WHAT CHANGED          │   table on a phone is a table nobody reads.
│ 10:18 L&T  ₹12,500cr  │
│      data centre EPC  │   The heatmap becomes a list of the three strongest and
│      HIGH · 8% of rev │   three weakest cells, with their evidence, because a 9×8
└───────────────────────┘   grid at 375px is decoration.
```

---

## PART 5 — Data model

Postgres, in the existing Supabase project. Service-role only; no anon grants.

```sql
-- identity ------------------------------------------------------------------
companies(id pk, symbol, isin, instrument_key, name, sector, listed_mcap,
          free_float, updated_at)

-- AGI's classification, versioned, never overwritten -------------------------
ai_classification(id pk, company_id fk, layer, sub_layer, weight_split numeric,
                  admitted_on date, retired_on date, reviewed_by, review_note)
ai_classification_evidence(id pk, classification_id fk, kind, hard boolean,
                           source_url, source_doc, excerpt, observed_at)

-- market --------------------------------------------------------------------
market_prices(company_id, ts, ltp, volume, primary key(company_id, ts))
daily_market_metrics(company_id, date, close, volume, adv20, rs_nifty,
                     dist_50dma, dist_200dma, dist_52w_high,
                     primary key(company_id, date))

-- estimates -----------------------------------------------------------------
earnings_estimates(company_id, fiscal_year, metric, value, n_analysts, as_of,
                   source, primary key(company_id, fiscal_year, metric, as_of))
estimate_revisions(company_id, fiscal_year, metric, window_days, pct_change,
                   breadth, n_changed, computed_at)

-- fundamentals: reuse the fact store already in this repo --------------------
-- company_facts(concept, definition_id, measurement_basis, value, source_page,
--               source_sentence, …)  ← already built, already refuses
--               figures whose value is not in the sentence it cites

-- capital -------------------------------------------------------------------
company_capex(company_id, period, announced, category, ai_relevant boolean,
              source, confidence)
ai_projects(id pk, company_id fk, kind, name, state, district, status,
            capacity_mw, investment_inr, power_source, renewable_share,
            expected_completion, customer, source_url, last_verified)
orders(id pk, company_id fk, announced_at, value_inr, customer, category,
       duration_months, source_url, ttm_revenue_at_announcement,
       significance numeric, significance_band)

-- language ------------------------------------------------------------------
transcripts(id pk, company_id fk, quarter, held_on, source_url)
transcript_mentions(transcript_id fk, term, count, first_seen boolean)
language_changes(company_id, quarter, phrase, first_seen_at, still_present)

-- output --------------------------------------------------------------------
signals(id pk, company_id fk, signal, direction, raised_at, cleared_at, method)
signal_evidence(signal_id fk, evidence_kind, ref_table, ref_id, weight)
index_levels(index_code, ts, level, construction)   -- construction: eq | cap
index_attribution(index_code, ts, company_id, contribution_pp)
```

**Update frequency and source, per table**

| table | frequency | source |
|---|---|---|
| `market_prices` | tick | Upstox WS v3 |
| `daily_market_metrics` | 1/day post-close | Upstox REST candles |
| `index_levels`, `index_attribution` | 1 min intraday | derived |
| `orders` | on announcement | NSE/BSE corporate announcements `NEEDED` |
| `ai_projects` | weekly | company IR, state filings `NEEDED` |
| `earnings_estimates` | daily | consensus vendor `NEEDED` |
| `transcript_mentions` | on transcript | IR sites, vendor `NEEDED` |
| `company_facts` | on filing | existing extraction pipeline |
| `ai_classification` | monthly + on evidence | AGI screen |

Four `NEEDED` rows are the honest state of this product: orders, projects, consensus
estimates and transcripts have no wired source yet. Sections depending on them render the
tag, not a number. See PART 8.

---

## PART 7 — Formulas

Every metric on the page resolves to one of these. Anything not on this list does not go on
the page.

**Market**

```
relative_strength(i,t)   = return(i,t) − return(NIFTY,t)
volume_ratio(i,t)        = volume_so_far(i,t) / median(volume_to_same_minute(i, 20d))
                           ← time-of-day matched; a raw 20-day average compares
                             10:00 against a full day and calls everything quiet
dist_52w_high(i)         = ltp(i) / max(high(i, 252d)) − 1
breadth(t)               = advancers(t) / (advancers(t) + decliners(t))
```

**Index**

```
level_eq(t)    = level_eq(t−1) × mean_i( ltp(i,t) / ltp(i,t−1) )
level_cap(t)   = level_cap(t−1) × Σ_i w_i × ( ltp(i,t) / ltp(i,t−1) ),  w capped
contribution_i = w_i × return_i                                    (in pp)
layer_pp(L)    = Σ_{i ∈ L} contribution_i
```

Contributions sum to the index return by construction. If they do not, the page shows the
residual rather than hiding it — a residual means a corporate action was missed.

**Earnings**

```
revision_momentum(i, fy, d) = eps_consensus(i, fy, today) / eps_consensus(i, fy, today−d) − 1
revision_breadth(basket)    = up_count / (up_count + down_count)
```

**The revision gap** — the product's central proprietary measure:

```
revision_gap(i, d) = revision_momentum(i, FY+1, d) − price_return(i, d)
```

Both terms are percentage changes over the same window, so the difference is in
percentage points and is directly readable.

- **Positive gap** — estimates are rising faster than price. Expectations are improving
  and the market has not paid for it yet. It is *not* a signal that it will.
- **Negative gap** — price is running ahead of estimates. The multiple is doing the work.
  That can persist for a long time and says nothing about timing.

A gap is meaningless without both windows stated, so the page always renders it as
`+14pp (90d)`, never as a bare number.

**Return decomposition** — the earnings-vs-multiple question, made arithmetic:

```
price_return   = (1 + eps_change) × (1 + pe_change) − 1
eps_change     = fwd_eps(t) / fwd_eps(t−1) − 1
pe_change      = fwd_pe(t)  / fwd_pe(t−1)  − 1
earnings_pp    = eps_change
multiple_pp    = price_return − eps_change          (residual, exact)
```

**Orders**

```
order_significance = order_value / ttm_revenue      ← revenue at announcement, not today's
```

| band | threshold | reading |
|---|---|---|
| Low | < 2% | noise |
| Moderate | 2–10% | visible in a year's revenue |
| High | 10–25% | changes the year |
| Transformational | > 25% | changes the company |

Also reported, never blended: `order_value / market_cap` and
`order_value / existing_order_book`. **No composite order score.** Three ratios that a
reader can hold in their head beat one number that hides which of them moved.

**Capex**

```
capex_intensity = capex / revenue
capex_growth    = capex(t) / capex(t−1) − 1
funding_cover   = operating_cash_flow / capex        ← < 1 means it is being financed
```

**Valuation**

Upstox key-ratios supplies the reported half - P/E, P/B, EV/EBITDA, ROE, ROCE, ROA -
each with a sector value beside it, through the `upstoxValuationRatiosRefresh` path that
already exists. Those are *trailing*. Forward P/E, expected growth and therefore PEG need
consensus estimates, which Upstox does not carry, so the valuation panel ships half-lit and
says which half:

```
peg = forward_pe / expected_eps_growth_pct     ← both inputs NEEDED
premium_to_sector = company_value / sector_value − 1     ← available now
```

PEG is reported with both inputs beside it, because a PEG of 1.3 built on 60% growth and
one built on 8% growth are not the same claim.

**Market attention proxy** — explicitly a behaviour proxy, not fund flow:

```
attention(i,t) = z(volume_ratio) + z(relative_strength_5d) + z(range_expansion)
```

Labelled on the page as *"market behaviour, not fund flows — AGI does not have
institutional flow data."* If that caveat is ever removed without the data arriving, the
metric is a lie.

**No composite scores.** There is no "AGI Score" out of 100. Every number above is one
thing, computed one way, from named inputs. A composite is a way of not saying which input
moved.

---

## PART 8 — What is missing, and what it would take

| need | blocks | candidate source | note |
|---|---|---|---|
| Corporate announcements | order feed, catalysts, alerts | **Trendlyne** (connected) | Reg 30 filings with PDFs; server-side API access still needed |
| Consensus estimates | revisions, gap, PEG, forward P/E | Refinitiv / FactSet / Capital IQ | the largest cost item; nothing else substitutes |
| Trailing valuation | the valuation panel's reported half | **Upstox key-ratios** (connected) | P/E, P/B, EV/EBITDA, ROE, ROCE, ROA, each with a sector value; already flows through `upstoxValuationRatiosRefresh` |
| Transcripts | language detector, mention momentum | **Trendlyne** (connected) | full transcripts and investor presentations, semantic search |
| Data centre projects | project tracker, MW pipeline | company IR, state industrial filings, press | no single source; manual + verification |
| Grid and transmission | the bottleneck panel | CEA, POSOCO, state discoms | public but poorly structured |
| Order books | order significance denominator | filings, already in `company_facts` | partially available now |
| Free float | cap-weighted construction | NSE shareholding filings | quarterly |

Two rows moved from `NEEDED` to available while this was being written: Trendlyne is
already connected to the workspace and covers both announcements and transcripts. It is an
MCP connection today, not a server integration, so the product still needs API credentials
of its own — but the data exists and has been tested against real filings, which is a
different problem from not having a source.

The honest reading of this table: **Phase 1 can ship on Upstox alone.** The index,
attribution, breadth, relative strength, the decomposition's price half, and the whole
research surface need nothing else. Revisions, orders and projects each need a source that
costs money or effort, and each should be added only when its panel can be filled
completely — a half-populated order feed is worse than none, because a reader cannot tell
silence from absence.

---

## PART 6 — Upstox integration

Most of this exists. `server/services/upstoxMarketFeedV3.js` already authorises against the
v3 feed endpoint, loads the protobuf `FeedResponse` type, decodes messages, normalises
epochs, holds a `SynchronizedSnapshotStore`, classifies auth errors and reconnects.
`server/services/liveAlphaRuntime.js` already loads a universe file, maps members onto
sector indices, persists state and falls back to a second provider when the socket drops.

```
Upstox WS v3 ──▶ protobuf decode ──▶ SynchronizedSnapshotStore (in process)
                                             │
                        ┌────────────────────┼────────────────────┐
                        ▼                    ▼                    ▼
                  index engine        metric engine        alert engine
                   (1 min)             (1 min)              (on trigger)
                        │                    │                    │
                        └──────▶ index_levels / daily_market_metrics / alerts
                                             │
                                   SSE ──▶ the monitor panel
```

**What to add**

1. `server/config/india-ai-enablers.universe.json` — the screen's output, same shape the
   runtime already reads, plus `layer` / `subLayer` / `weightSplit`.
2. `LIVE_ALPHA_UNIVERSE_PATH` already exists as an override, so a second runtime instance
   can track this universe without touching the first.
3. An index engine that reads the snapshot store each minute and writes `index_levels` and
   `index_attribution`.
4. SSE to the page. Not a second WebSocket — the browser needs a one-way stream of already
   computed numbers, and SSE reconnects by itself.

**Cadence**

| every | computed |
|---|---|
| tick | snapshot store only, no derived work |
| 1 min | index level, contribution, day %, breadth, volume ratio, RS |
| 5 min | momentum, breakouts, 52-week proximity, leadership changes |
| post-close | daily metrics, 50/200DMA distance, revision gap, decomposition |
| weekly | project tracker refresh |
| monthly | rerun the screen, version the universe |

**When the socket drops.** The existing runtime already falls back. The rule this product
adds: the monitor header shows the feed state, and a stale snapshot is rendered greyed with
its age in seconds. A price that stopped updating must never look like a price that stopped
moving.

---

## PART 10 — Page copy

> **India's Hidden AI Infrastructure Trade**
> The infrastructure opportunity beneath India's laggard equity index

Section headings, in order:

- **Executive Intelligence** — five claims, each with its evidence count
- **Is the move earnings or multiple?** — the decomposition
- **Power: the binding constraint** — MW announced against MW energised
- **Data Centres: shell, operator, hardware** — where the capital lands
- **Semiconductors: assembly first, fabs later** — OSAT before fab
- **What the transcripts said before the numbers did** — language detector
- **Valuation against growth** — the scatter, quadrants unnamed
- **What would break this** — the risk register
- **How this universe was built** — the screen, its thresholds, its exclusions

The last heading is not an appendix. A basket that will not show its screen is a basket
nobody should buy.

Standing footer on every data panel:

> Descriptive intelligence, not investment advice. Every figure carries its source.
> Figures tagged NEEDED have no wired source and are shown empty by design.

---

## PART 11 — Panel specifications

Each panel: the question it answers, its inputs, its refusal condition.

**Live index strip** — *Is the theme working today?*
Inputs `LIVE`. Shows equal-weighted level, day %, YTD, relative to Nifty, breadth,
construction label. Refuses if fewer than 80% of members have ticked in 60s: shows
coverage, not a level computed from a partial basket.

**Today's move** — *What drove it?*
Inputs `DERIVED`. Contribution in pp by layer and by name, five largest each way, plus
residual. Refuses if contributions and index return disagree by more than 5bp.

**Return decomposition** — *Earnings or multiple?*
Inputs `LIVE` + `NEEDED` (consensus). Two stacked areas. **Ships disabled** until consensus
data is wired; shows the price line alone with the panel's question and the source it wants.

**Earnings revisions** — *Where are expectations moving?*
Inputs `NEEDED`. Upgrades/downgrades by sub-layer, breadth, the revision gap. Entirely
blocked in Phase 1 and says so.

**Order feed** — *What was signed, and does it matter?*
Inputs `NEEDED` + `DERIVED`. Each row: time, company, value, customer, category,
significance band with its denominator shown. Never a bare rupee figure — ₹12,500cr means
nothing until it is 8% of revenue.

**Data centre projects** — *What is actually being built?*
Inputs `NEEDED`. Project, location, MW, status, expected energisation, customer if
disclosed, last verified date. A project unverified for 90 days is greyed.

**Power behind AI** — *Is the grid keeping up?*
Inputs `NEEDED`. MW announced against transmission and transformer capacity contracted, by
region. This panel is the thesis's strongest claim and its thinnest data. It states the
comparison it wants to make and does not make it until both series exist.

**Intelligence heatmap** — *Which sub-layer is strongest?*
9 sub-layers × 8 dimensions. Four states: weak, neutral, improving, strong. Every cell is
clickable and opens the rows that produced it. **A cell with no evidence is blank, not
neutral** — neutral is a finding, blank is an absence, and colouring the second like the
first is how a heatmap lies.

**Watchlist** — *Everything, sortable.*
Inputs mixed, per column tagged. Columns unavailable in Phase 1 render a dash and a
tooltip naming the source.

**Valuation vs growth** — *What is priced in?*
Inputs `NEEDED`. Scatter, x = expected growth, y = forward P/E, bubble = market cap, colour
= layer. Four quadrants drawn, none named.

**Risk register** — *What would break this?*
Inputs `AGI` + evidence. Standing risks: power availability, project slippage, customer
concentration, capex funded by debt, policy dependence, valuation, execution. Each carries
its supporting rows or is marked unevidenced.

---

## PART 12 — Signal engine

Signals classify observations. They are not recommendations, and there is deliberately no
BUY/SELL/HOLD. Every signal carries evidence rows and a method string, and clears on its
own condition rather than by expiry.

```
EARNINGS_ACCELERATION      revision_momentum(FY+1, 90d) > +5pp and breadth > 0.6
EARNINGS_DECELERATION      mirror
UPGRADE_CYCLE              4 consecutive weeks of positive breadth
ORDER_MOMENTUM             TTM announced orders / TTM revenue rising 2 quarters
CAPEX_ACCELERATION         capex growth > universe median and funding_cover < 1.5
BREAKOUT                   close > max(252d) and volume_ratio > 2
RELATIVE_STRENGTH          RS vs Nifty > 0 over 20d and 60d
VOLUME_EXPANSION           volume_ratio > 2 on 3 of 5 sessions
VALUATION_EXPANSION        forward P/E > 80th percentile of own 5y
PROJECT_MILESTONE          ai_projects.status advanced
AI_EXPOSURE_INCREASING     hard evidence added this quarter
AI_EXPOSURE_UNCONFIRMED    soft evidence only, no hard item in 2 quarters
FCF_PRESSURE               funding_cover < 1 for 2 consecutive periods
EXECUTION_RISK             project slipped ≥ 1 quarter, twice
```

`AI_EXPOSURE_UNCONFIRMED` is the one that earns its keep. A company that keeps talking
about AI and never signs anything should get *more* conspicuous over time, not quietly
remain a member.

```
function evaluate(company, asOf) {
  const evidence = evidenceFor(company, asOf);          // rows, not scores
  const raised = RULES
    .map((rule) => ({ rule, hit: rule.test(evidence) }))
    .filter((one) => one.hit);
  for (const { rule } of raised) {
    upsertSignal({ company, signal: rule.name, method: rule.describe(), raisedAt: asOf });
    attachEvidence(rule.rowsUsed(evidence));            // the rows, by id
  }
  for (const open of openSignals(company)) {
    if (open.rule.cleared(evidence)) clearSignal(open, asOf);
  }
}
```

A signal with no attached evidence rows is a bug, and the writer rejects it.

---

## PART 12b — The fact store behind the dashboard

Product B does not parse filings. It asks Product A, which has already made every
figure cite itself, and carries the citation through to the page. The alternative — a
second parser, tuned for AI names — would drift from the first within a quarter and
there would be no way to tell which was right.

`aiEnablersFundamentals.js` is the join. It reads the store once per company and answers
the dashboard's concepts (capex, debt, EBITDA, revenue, CFO) with provenance attached:
a stated figure carries `source_page` and `source_sentence`; a derived one carries the
`lineage()` tree, so "Kaynes capex intensity increased" opens into `capex@FY26 = 473`
from page 142 of the annual report, `revenue@FY26 = 3,000`, and the division between
them.

**The state the fact store did not have.** Product A's five resolution states describe a
filing that has been read. Ask `resolveConcept()` about a company with no ingested
document and it answers `NOT_DISCLOSED` — *"places in the filing were searched and none
disclosed it"* — which is a false statement about a filing nobody opened, and on a
dashboard reads as "this company discloses no capex". So this module checks ingestion
first and `NOT_INGESTED` is its own answer. The pair has to stay apart: one is a gap in
our reading, the other is a fact about the company.

**Two namespaces, joined once and visibly.** A universe member is an NSE symbol and an
ISIN. A fact belongs to a `company` key in the store. `factStoreKeyFor` reads only a
declared `factStoreKey` and never falls back to the symbol, because a fallback silently
attaches one company's filings to whatever happens to match. A member without a declared
mapping reads as unmapped, which is visible, rather than as a company with no
disclosures, which is not.

**What this unblocks.** Stage 3 of the screen took investment-intensity figures as
inputs and had nowhere to get them. `intensityForUniverse` now produces them —
capex/sales, capex growth, three-year revenue CAGR — from cited filing rows, in the
shape `stageThree` reads. A ratio missing an input is null and named; a three-year CAGR
is never computed from two disclosed years.

Endpoints: `/api/india-ai/fundamentals?period_end=YYYY-MM-DD` and
`/api/india-ai/screen/intensity`.

---

## PART 13 — Worked example

The five companies named in the brief are real listed entities and their business lines are
public knowledge: **ABB India** and **Hitachi Energy India** (power equipment),
**Netweb Technologies** (data centre hardware), **Kaynes Technology** (semiconductor
assembly and electronics manufacturing), **Tata Power** (power generation).

What the product would render for each is below **with no figures**, because AGI has not
yet run its own screen or wired its own data, and filling this table from the broker note
is the thing section 0 rules out. The shape is the deliverable; the numbers arrive when the
sources do.

```
NETWEB TECHNOLOGIES                                    NSE: NETWEB
Layer     Data Centre → Hardware              classification: AGI, pending screen
LIVE      ltp · day% · 1W · 1M · YTD · RS vs Nifty · volume ratio · 52w distance
DERIVED   contribution to index today (pp) · attention proxy
FILED     order book, capex, revenue          ← company_facts, on filing
NEEDED    consensus FY27/FY28 · revision gap · transcript mentions
SIGNALS   raised only when a rule's evidence rows exist
RISK      customer concentration · valuation  ← evidenced or marked unevidenced

AGI INTELLIGENCE SUMMARY
  Generated only when at least one LIVE and one FILED input are present.
  Template: "<company> shows <signals> across <dimensions>; <caveat>."
  Never generated from LIVE data alone — a price move is not intelligence.
```

That last rule is the point of the worked example. A summary built only from price is a
description of a chart wearing the clothes of research.

---

## PART 14 — Update cadence

| cadence | what | source |
|---|---|---|
| tick | ltp, volume into snapshot store | Upstox WS |
| 1 min | index, attribution, day %, RS, breadth, volume ratio | derived |
| 5 min | momentum, breakouts, leadership, alerts | derived |
| hourly | order feed poll, news poll | `NEEDED` |
| post-close | daily metrics, DMA distance, decomposition, revision gap | derived + `NEEDED` |
| weekly | project tracker verification sweep | `NEEDED` |
| monthly | rerun screen, version universe, rebalance equal weights | AGI |
| quarterly | transcripts, language detector, free float | `NEEDED` |

---

## PART 15 — Roadmap

**Phase 1 — the basket, live.** Ships on Upstox alone. Run the screen, publish the universe
with its thresholds and admissions, stand up the index in both constructions, attribution,
breadth, relative strength, the research surface, the risk register. Every panel needing
another source renders `NEEDED`. *This is a complete product.* It answers "is the theme
working, what is driving it, and what is in it" with nothing borrowed.

**Phase 2 — announcements.** Corporate announcement ingestion. Order feed, significance
with its denominators, catalyst timeline, market reaction measurement. Unlocks
`ORDER_MOMENTUM`, `PROJECT_MILESTONE`, and the alert system's most valuable trigger.

**Phase 3 — estimates.** Consensus vendor. Revisions, the revision gap, PEG, the
valuation-vs-growth map, and the second half of the decomposition. The largest cost and the
largest analytical gain: without it the product can say what moved but not whether earnings
justified it.

**Phase 4 — language.** Transcript ingestion, mention momentum, the new-phrase detector.
Earliest signal, weakest evidence, and the one most likely to be over-read — which is why
it arrives last of the data phases, on top of a product that already knows the difference
between a phrase and an order.

**Phase 5 — the bottleneck engine.** Grid and project data joined to the basket, so the
page can answer whether announced compute has the power to run. This is the claim the theme
ultimately rests on and the only one that needs data nobody sells cleanly.

---

## Appendix — rules this product does not break

1. No figure without a source tag.
2. No universe member without reproducible admission evidence.
3. Soft evidence never admits a company on its own.
4. No composite score.
5. No quadrant, signal or panel named "buy".
6. A stale price is rendered stale, never as a live one.
7. An empty panel says what it is missing and why.
8. The screen's thresholds are published on the page.
9. Nothing from a licensed third-party note ships in the product.
