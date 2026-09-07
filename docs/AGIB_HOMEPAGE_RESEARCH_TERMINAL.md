# AGIB Homepage — Research Terminal

Public `/` is a **research-first institutional terminal**, not a news homepage.

## Layout

1. **Header** — Logo · Home · Company Intelligence · Research Notes · IPO · Global · Universal Search · Sign In/Up (or Notifications + Account menu)
2. **Market Outlook Strip** — sticky with header; index direction (Bullish/Neutral/Bearish) + Market Health; links to Market Intelligence
3. **Hero** — brand **AGI** + AI Ask search + trending chips
4. **Session Switcher** — Pre / Morning / Afternoon / Post / Global (IST-aware, manually overridable)
5. **Main + right rail** — AI Highlights, Live Research Feed (research cards), Featured, Themes · Calendar, Trending, Watchlist, Most Read, Recently Viewed
6. **IPO Snapshot · Global Snapshot · Newsletter**
7. **Footer**

## Key files

| Piece | Path |
| --- | --- |
| Home | `src/components/Home/ResearchTerminalHome.jsx` |
| Outlook strip | `src/components/Home/MarketOutlookStrip.jsx` |
| Research cards | `src/components/Home/ResearchFeedCard.jsx` |
| Session helpers | `src/lib/marketSession.js` |
| Catalogs | `src/components/Home/homeTerminalData.js` |
| Header / Footer | `src/components/Layout/Header.jsx`, `src/components/Footer.jsx` |

## Guardrails

- Outlook strip uses AGI sentiment / health — not raw exchange prices.
- Ask search routes to `/ask` via existing `AskAgiBar` + UI BFF autocomplete.
- Logged-in personalisation (continue reading, watchlist) reads local workspace history.
- `/global` maps to Macro / Global Intelligence.

## Tests

```bash
node src/lib/marketSession.test.js
```
