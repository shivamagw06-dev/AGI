# AGI Letters

Four branded publications from Agarwal Global Investments.

| Letter | Schedule | Tagline | CMS sections that route here |
| --- | --- | --- | --- |
| **AGI Markets** | Flagship | Market hub for equities, macro, commodities, FX, fixed income | Market News, 12 PM Market Update, Research, general |
| **AGI Morning Brief** | 7:00–8:00 AM IST | Everything you need before the opening bell. | Pre-Market Update, Morning Market Update |
| **AGI Evening Brief** | 4:30–6:00 PM IST | What moved markets today—and why. | Market Close Update, Day Close Update |
| **AGI Macro** | Weekly / major events | Understanding the forces shaping global markets. | Macro Intelligence, Economy, Global Markets, Commodities |

Sender mailbox for all letters:

`updates@agarwalglobalinvestments.com`

Display names change per letter, e.g. `AGI Morning Brief <updates@...>`.

## Setup

1. Merge the newsletter + letters PRs
2. Run SQL migration in Supabase:
   - `supabase/migrations/20260725180000_agi_letter_preferences.sql`
3. Keep Render env:
   - `RESEND_API_KEY`
   - `NEWSLETTER_FROM_EMAIL` (optional; letter display names override From name)
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

## How it works

- Homepage signup lets readers pick one or more letters
- Preferences are stored on `subscribers.preferences`
- CMS publish maps `section` → letter and emails only matching subscribers

## Editorial guide (quick)

### AGI Morning Brief
Include overnight US/global, Asia setup, SGX GIFT Nifty, macro events, earnings, stocks to watch, institutional insights, calendar.

### AGI Evening Brief
Include market wrap, gainers/losers, sectors, FII/DII, breaking developments, tomorrow watchlist, closing commentary.

### AGI Macro
RBI/Fed, inflation/employment, bonds, FX, geopolitics, fiscal policy, trade, long-form analysis.

### AGI Markets
Flagship hub / general market coverage and the default newsletter list.
