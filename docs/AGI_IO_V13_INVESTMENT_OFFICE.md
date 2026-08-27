# AGI V1.3 — Investment Office (Institutional Morning Office)

## Mission

Build a world-class **Investment Office** for AGI — the morning command center used by an institutional research team before markets open.

This is **not** Knowledge Operations.

| Surface | Role |
|---|---|
| **Knowledge Operations** | Knowledge pipeline control room (gather → integrate → cover → repair) |
| **Investment Office** | Daily investment desk (overnight → priorities → markets → macro → calendar → monitoring) |

No BUY. No SELL. Monitoring only.

## Route

- Admin UI: `/admin/investment-office`
- Alias redirect: `/investment-office` → `/admin/investment-office`
- **Admin only** — non-admins receive **403 Forbidden**
- Full-bleed page (not CMS chrome), sibling of Knowledge Operations

## APIs

Engine + Node BFF under `/v1/investment-office/*` and `/api/intelligence/investment-office/*`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/overview` | Precomputed morning snapshot (V1.3.1 hot path) |
| GET | `/snapshot` | Snapshot metadata + rebuild job status |
| GET | `/system-health` | Live operational status (seconds freshness) |
| GET | `/morning-office` | Header + summary + brief + priorities + overnight |
| GET | `/daily-brief` | Executive + AI brief |
| GET | `/research-queue` | Staged research queue |
| GET | `/opportunities` | Monitoring opportunities (not recommendations) |
| GET | `/market-summary` | India / global / commodities / FX |
| GET | `/macro` | Macro events + calendar |
| GET | `/calendar` | Earnings + corporate actions |
| GET | `/portfolio-monitor` | Watchlist / review alerts |
| GET | `/sector-monitor` | Sector board |
| GET | `/metrics` | Daily research metrics |
| POST | `/refresh` | Async snapshot rebuild (existing snapshot keeps serving) |

See also: `docs/AGI_IO_V131_PERFORMANCE_OPS.md` (Performance & Operations).
| POST | `/generate-morning-brief` | Regenerate AI / executive brief |

Existing IO-01 endpoints (`/health`, `/dashboard`, `/company/{ticker}`, `/query`, `/package`) remain unchanged.

## Soft wiring

The morning desk soft-aggregates:

- Investment Office desk (`dashboard` / cached desk)
- Investment Operations morning office (when available)
- Continuous Gather & Learn (CGL) overnight cycles
- Institutional Coverage Factory (ICC metrics)
- Knowledge Operations missing-inbox counts (link out, do not duplicate KOC UI)

## UI sections

1. Morning Executive Brief  
2. Today's Priorities  
3. Overnight Activity  
4. Research Queue  
5. Morning Opportunities (monitor only)  
6. Market Dashboard  
7. Macro Intelligence  
8. Corporate Calendar  
9. Portfolio Monitoring  
10. Sector Monitoring  
11. Daily Research Metrics  
12. Analyst Workspace  
13. Investment Calendar  
14. Daily AI Summary  

Bottom action bar: Refresh Morning Office · Run Morning Brief · Open Knowledge Operations · Research Queue · Macro · Portfolio · Export.

## Design

White institutional interface · Financial Times typography · Bloomberg precision · newspaper masthead · timeline-driven · everything drillable.

## Success criteria

- Every morning the investment team has a complete institutional briefing.
- Overnight knowledge becomes analyst priorities.
- Research queue is prioritized by impact.
- Macro, markets, earnings and corporate events are unified.
- Portfolio monitoring is integrated (no recommendations).
- Morning briefing is AI-generated every day.
- Complements Knowledge Operations without duplicating it.

## Version

- Workstream: `IO-V1.3`
- Product version: `io-v1.3.1` (Performance & Ops — see `docs/AGI_IO_V131_PERFORMANCE_OPS.md`)
- Platform: `AGI V1.3.1`

## Performance note (v1.3.1)

`/overview` reads a **precomputed morning snapshot**. Heavy ICF/IEP/CGL scans run in the overnight pipeline or via async `POST /refresh`, not on page load.
