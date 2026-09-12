# Integrate — Phase 2 stack onto main

Integration branch: `cursor/integrate-phase2-stack-4cc0` → `main`

## Already on main

- FIRE-06 → WO-01 application stack via #356  
  (Business Quality, Investment Office, CIO, Office SDK, Portfolio Office, PEB, Watchlist Office)

## Brought onto main by this integration

| Workstream | Deliverable |
| ---------- | ----------- |
| **CW-01** | Company Workspace (presentation UX assembly) |
| **IST-01** | Kotak / RBI institutional stress test |
| **IST-02** | Raw-evidence institutional research validation |
| **IBS-01** | AGI Institutional Benchmark Suite (39 cases) |
| **Phase 2 UX** | Product shell at `/agi` — Dashboard, Ask AGI, Company Workspace |

## Product entry

- Platform: `/agi`
- Ask AGI: `/agi/ask`
- Company: `/agi/companies/:ticker`

Users operate in Companies · Portfolios · Research · Markets · Ideas · Ask AGI — not engine module IDs.

## Verification

- Frontend build: pass
- Pytest (CW / IST-01 / IST-02 / IBS): 31 passed
