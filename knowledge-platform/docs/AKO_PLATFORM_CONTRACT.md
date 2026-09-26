# Adaptive Knowledge Orchestrator (AKO) — Sprint 6.5

**Service:** AGI Knowledge Acquisition Platform (KAIP)  
**Layer:** Adaptive Knowledge Orchestrator  
**Version:** 0.5.0  
**Depends on:** 6.1–6.4 (KAIP → IKO → ILE → KRIG)  
**Boundary:** Orchestrate collectors. Never collect, parse, or reason.

---

## 1. Objective

AKO is the **operating system** of the Knowledge Platform.

It schedules, prioritises, monitors and coordinates all knowledge acquisition jobs across Yahoo Finance, NSE, BSE and Company IR — converting a fixed scheduler into an **event-driven institutional learning system**.

```text
AGI should continuously learn from the market,
not continuously research for the user.
```

---

## 2. Core principles

1. Never poll every source at the same interval.  
2. Poll according to the nature of the data.  
3. Increase polling automatically around important events.  
4. Decrease polling during quiet periods.  
5. Ask must never trigger collectors.  
6. Intelligence Engine only consumes published knowledge.  
7. Heavy processing occurs when users are least active.  
8. Every scheduling decision is deterministic and observable.

---

## 3. Architecture

```text
                 Adaptive Knowledge Orchestrator

                          Market Clock
                               │
                               ▼
                 Session & Event State Manager
                               │
         ┌─────────────────────┼──────────────────────┐
         ▼                     ▼                      ▼
   Schedule Engine       Priority Engine       Event Engine
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               ▼
                     Collector Dispatcher
                               │
       ┌──────────────┬────────┼──────────┬─────────────┐
       ▼              ▼        ▼          ▼
    Yahoo           NSE       BSE     Company IR
                               │
                               ▼
               Knowledge Acquisition Platform
```

AKO does **not** collect data itself.

---

## 4. Market sessions

| Session | IST window (approx.) | Behaviour |
|---|---|---|
| `PRE_MARKET` | 08:30–09:15 | Warm-up; reduced live polling |
| `MARKET_OPEN` | 09:15–09:30 | Aggressive announce/quote cadence |
| `LIVE_MARKET` | 09:30–15:30 | Full live schedule |
| `POST_MARKET` | 15:30–16:00 | Close processing begins |
| `AFTER_CLOSE` | 16:00–19:00 | Bhavcopy, corporate actions, KO updates |
| `OVERNIGHT` | 23:00–06:00 | Heavy rebuilds (knowledge, relationships, learning) |
| `WEEKEND` | Sat–Sun | Minimal polling |
| `HOLIDAY` | Exchange holiday calendar | Minimal polling |

Collectors behave differently in each session.

---

## 5. Base collector schedule (adaptive around this)

| Job | Knowledge | Base frequency |
|---|---|---|
| `YahooCollector` / market snapshot | Live quotes | 30–60s in LIVE_MARKET |
| Yahoo company profile facet | Profile | Daily (overnight) |
| Yahoo financials facet | Financial statements | 30 min earnings season; else 6–12h |
| Yahoo news facet | News | 5 min live; slower overnight |
| `NSEAnnouncementCollector` | Announcements | 30s live |
| `BSECorporateActionCollector` | Corporate actions | 30 min |
| `NSEBhavcopyCollector` | Bhavcopy | Once AFTER_CLOSE |
| `CompanyIRCollector` | IR docs | 10 min live; hourly otherwise |

Sprint 6.5 orchestrates the **registered Sprint 6.1 collectors** with adaptive intervals. Facet-level Yahoo jobs are represented as schedule profiles even when a single collector body runs.

---

## 6. Event-driven boosts

High-priority events temporarily increase polling:

- Quarterly earnings / annual results  
- Dividends, buybacks, M&A  
- Credit rating changes  
- RBI monetary policy  
- Union Budget  
- Major regulatory announcements  

Example:

```text
Infosys Earnings Today
  → boost Yahoo + Company IR + NSE announcements
  → publish updated Company Knowledge
  → create Monitoring / Learning signals
  → return to normal schedule after boost window
```

---

## 7. Ask separation (hard rule)

```text
User Question → KRIG → Knowledge Store → Judgment → Answer
```

Collectors remain **background-only**. AKO never exposes a “collect for this Ask” API to the Intelligence Engine.

---

## 8. Scheduler responsibilities

- Register collectors  
- Manage execution schedules  
- Dynamic polling frequency  
- Retry + exponential backoff  
- Failure recovery  
- Dead-letter queue  
- Collector prioritisation  
- Event-triggered scheduling  
- Market session transitions  
- Knowledge freshness monitoring  
- Health metrics + execution telemetry  

---

## 9. Telemetry (every execution)

Collector · start/end · duration · success/failure · objects collected/published · retry count · queue latency · freshness impact · session · priority · trigger reason

Mission Control surface (KAIP internal):

- Collector health  
- Current polling interval  
- Next scheduled execution  
- Queue depth  
- Freshness score  
- Source availability  
- Daily collection statistics  

---

## 10. Operate extensions (KFE + KCE)

Sprint 6.5 Operate also includes:

- **KFE** — every Knowledge Object reports age, `Fresh` / `Needs Refresh`, and a `current_as_of` statement  
- **KCE** — every Knowledge Object reports trust (`confidence_pct`) from multi-source agreement  

See [`KFE_KCE_OPERATE_CONTRACT.md`](KFE_KCE_OPERATE_CONTRACT.md).

---

## 11. Success criteria

- Market session transitions are automatic  
- Schedules are adaptive, not fixed  
- Earnings / major events temporarily boost polling  
- Overnight rebuilding does not compete with Ask  
- Ask never performs live collection  
- IE consumes only published knowledge  
- Every scheduling decision is observable  
- Freshness SLOs met without unnecessary polling  
- Published KOs carry freshness + confidence for IE weighting  

---

## 12. Non-goals

- New collectors  
- Reasoning / LLM  
- KRIG redesign  
- Full Hostinger Mission Control UI polish (soft API surface only)
