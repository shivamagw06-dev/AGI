# AGI Portfolio Office

AI-powered portfolio monitoring and research packaging for the AGI Intelligence Platform.

**Does not execute trades. Does not invent returns, risk, or scenario outcomes.**

## Folder structure

```
intelligence-engine/app/portfolio/
  __init__.py
  normalize.py          # Manual / CSV / model → PortfolioSnapshot
  recommend.py          # Review/Research/Monitor recommendations + Action Center
  pack.py               # PortfolioPackage builder, scenarios, dashboards

intelligence-engine/app/agents/portfolio_desk/
  health.py / risk.py / recommendations.py / summary.py   # Packaging agents only

src/beta/surfaces/PortfolioOfficeStory.jsx   # Client + Advisor workspace UI
```

## Files created

- `intelligence-engine/app/portfolio/*`
- `intelligence-engine/app/agents/portfolio_desk/*`
- `intelligence-engine/tests/test_portfolio_office.py`
- `src/beta/surfaces/PortfolioOfficeStory.jsx`
- `intelligence-engine/PORTFOLIO_OFFICE.md` (this file)

## Files modified

- `intelligence-engine/app/schemas/models.py` — Portfolio schemas, `DeskType.PORTFOLIO`
- `intelligence-engine/app/orchestration/director.py` — Portfolio desk plan + package attach
- `intelligence-engine/app/agents/cio_synthesizer.py` — `_synthesize_portfolio`
- `intelligence-engine/app/agents/registry.py` — register portfolio_desk
- `intelligence-engine/app/api/routes.py` — `/v1/portfolio/*`
- `server/routes/intelligence.js` — Node proxy
- `src/lib/intelligenceApi.js` — client helpers
- `src/beta/BetaApp.jsx`, `src/beta/components/StoryNav.jsx` — `/beta/portfolio`

## Components reused (no duplicates)

- Intelligence Core / Evidence / Confidence / Debate / Citation engines
- Research Director + Memory (RAG) store
- Equity Research Desk (holding research attach via metadata; not fabricated)
- CIO Committee (`ChiefInvestmentOfficer`)
- Packaging agents only under `portfolio_desk` (no new analysis engines)

## Workspace integration

- Route: `/beta/portfolio`
- Desk: `POST /v1/research/runs` with `desk: "portfolio"` + `metadata.portfolio`
- Shortcuts: `POST /v1/portfolio/normalize|ingest|scenario|office`
- Tabs: Overview · Portfolio · Research · Forecast · Risk · Events · Action Center · Timeline · Reports · CIO Summary

## Recommendation workflow

1. Ingest → common `PortfolioSnapshot`
2. `build_portfolio_package` → scores (withhold missing), sector map, health summary
3. `generate_recommendations` → verbs: Review / Research / Monitor / Consider / Investigate
4. Action Center bands: high / medium / low (each with evidence + confidence + reason)
5. Director runs packaging agents → Evidence/Confidence/Debate → CIO Neutral/Review summary
6. Forbidden language filtered: Buy / Sell / Execute

## Tests added

`intelligence-engine/tests/test_portfolio_office.py`

- Portfolio ingestion (CSV / model / manual)
- Recommendation generation + language bans
- Scenario analysis withhold
- Action Center / monthly report / timeline / workspace
- Director Portfolio Office run + CIO Summary
- API normalize / scenario / office
- Memory / components_reused markers

## Remaining work

- Wire live Forecast Layer + Macro Intelligence into scenario outcomes (still withheld)
- Persist timeline baselines for week/month/quarter/year compare
- Attach Equity desk child runs per holding when equity agents expand
- Continuous monitoring detectors against market feeds
- Broker connector implementing `source=broker_future` → same schema
- Multi-client advisor book ranking across stored portfolios
