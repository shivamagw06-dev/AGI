# AGI Investment Office

Operational layer above every existing AGI capability — the AI Chief Investment Officer workspace.

**Does not execute trades. Does not invent assumptions, event dates, or forecast changes.**

## Folder structure

```
intelligence-engine/app/investment_office/
  __init__.py
  playbooks.py      # Sector playbooks (structural templates)
  queue.py          # Research prioritisation
  calendar.py       # Investment calendar (withhold without evidence)
  journal.py        # Decision journal + research timeline
  graph.py          # Market knowledge graph
  pack.py           # InvestmentOfficePackage + daily brief + scenarios

intelligence-engine/app/agents/investment_office_desk/
  brief.py / queue_calendar.py / knowledge.py / summary.py

src/beta/surfaces/InvestmentOfficeStory.jsx
```

## Files created

- `intelligence-engine/app/investment_office/*`
- `intelligence-engine/app/agents/investment_office_desk/*`
- `intelligence-engine/tests/test_investment_office.py`
- `src/beta/surfaces/InvestmentOfficeStory.jsx`
- `intelligence-engine/INVESTMENT_OFFICE.md` (this file)

## Files modified

- `intelligence-engine/app/schemas/models.py` — `DeskType.INVESTMENT_OFFICE`, office schemas
- `intelligence-engine/app/orchestration/director.py` — desk plan + AGIB/memory packaging
- `intelligence-engine/app/agents/cio_synthesizer.py` — `_synthesize_investment_office`
- `intelligence-engine/app/agents/registry.py`
- `intelligence-engine/app/api/routes.py` — `/v1/investment-office/*`
- `server/routes/intelligence.js`
- `src/lib/intelligenceApi.js`
- `src/beta/BetaApp.jsx`, `src/beta/components/StoryNav.jsx`

## Components reused (no duplicates)

Intelligence Core · Research Director · Memory (RAG) · Evidence / Confidence / Debate / Citation · Market Intelligence (AGIB caches) · Equity Research · Forecast Intelligence (withheld until wired) · Portfolio Office · Screener / Watchlist / Comparison / Copilot / Validation / Visualization markers · CIO Committee

Packaging agents only — **no new research engines**.

## Workspace integration

- Route: `/beta/investment-office`
- Desk: `POST /v1/research/runs` with `desk: "investment_office"`
- Shortcuts: `POST /v1/investment-office/package|scenario|run`, `GET .../playbooks`
- Tabs: Today's Brief · Research Queue · Investment Calendar · Scenario Center · Decision Journal · Knowledge Graph · Playbooks · Portfolio Office · CIO Summary

## New user workflows

1. **Morning** — open Today's Brief (market story, risks, opportunities, priorities)
2. **Prioritise** — work Research Queue high → medium → low
3. **Calendar** — scan evidenced events; withheld dates stay blank
4. **Scenarios** — ask oil/RBI/inflation/China; assumptions explained, outcomes withheld without engines
5. **Journal** — review how views evolved from prior runs / portfolio reviews
6. **Graph / Playbooks** — explore relationships and sector templates
7. **Portfolio Office** — drill into linked holdings health
8. **CIO Summary** — Director + CIO Neutral/Review synthesis

## Tests added

`intelligence-engine/tests/test_investment_office.py`

- Playbooks + research prioritisation language bans
- Calendar withhold
- Package (brief/queue/journal/timeline/graph/portfolio link)
- Scenario withhold
- Agent registration
- Director CIO run + memory markers
- API package / scenario / run

## Remaining work

- Attach live Forecast Layer deltas into brief + queue
- Corporate calendar / earnings feed for scheduled (not withheld) dates
- Persist Decision Journal across sessions
- Interactive knowledge-graph visualization (Research Visualization)
- Multi-user office preferences / saved watchlists from Watchlist Intelligence API
