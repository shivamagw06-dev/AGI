# AGI Publishing & Newsletter Platform

Research Distribution Engine — one-click publish from the existing CMS into newsletter + social packs + analytics.

**Does not replace the CMS. Does not duplicate article storage.**

## Folder structure

```
supabase/migrations/20260724210000_publishing_newsletter.sql

server/services/publishing/
  store.js              # file store + optional Supabase sync
  emailProvider.js      # Resend abstraction (Postmark/Brevo/SES ready)
  templates.js          # institutional newsletter HTML
  channels.js           # LinkedIn / X / Telegram / WhatsApp / SEO packs
  subscribers.js        # CRUD, CSV, prefs, segments, GDPR delete
  analytics.js
  workflow.js           # one-click distribution
  publishing.test.js

server/routes/newsletter.js

src/lib/publishingApi.js
src/pages/admin/publishing/*
src/pages/UnsubscribePage.jsx
```

## Files created

- Migration, publishing services, newsletter router, admin publishing UI, unsubscribe page, API client, tests, this doc

## Files modified

- `server/index.js` — mount `/api` newsletter routes, CORS PATCH/DELETE, 2mb JSON
- `src/pages/admin/AdminRoutes.jsx`, `AdminLayout.jsx`
- `src/pages/admin/ArticleEditor.jsx` — triggers distribution on Publish
- `src/components/Newsletter.jsx` — subscribe via API
- `src/App.jsx` — `/unsubscribe` routes

## Database schema

- Extends `subscribers` (name, source, status, verified, preferences, tags, tokens, engagement timestamps)
- `newsletter_imports`, `publish_jobs`, `newsletter_events`, `newsletter_campaigns`

## APIs

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/newsletter/subscribe` | public + rate limit |
| POST | `/api/newsletter/import` | admin |
| GET | `/api/newsletter/subscribers` | admin |
| PATCH | `/api/newsletter/preferences` | public (email/token) |
| DELETE/POST | `/api/newsletter/unsubscribe` | public |
| POST | `/api/newsletter/send` | admin |
| POST | `/api/publish/article` | admin |
| GET | `/api/newsletter/analytics` | admin |
| GET | `/api/newsletter/campaigns` / `jobs` | admin |
| POST | `/api/newsletter/preview` | admin |

Admin token: `PUBLISHING_ADMIN_TOKEN` or `INTELLIGENCE_ENGINE_TOKEN` (default `dev-intelligence-token`).

## Publishing workflow

CMS Publish → article saved in existing `articles` table → `POST /api/publish/article` →

1. Website (already published)
2. Channel packs (2-min email, 30s LinkedIn, X thread, 10-bullet Telegram, WhatsApp-ready, SEO)
3. Newsletter send to segment (skips unsubscribed)
4. Analytics events
5. Campaign + job archive

## Email workflow

Provider abstraction (`EMAIL_PROVIDER=resend|stub`). Missing Resend key → dry-run stub (safe for tests). Never sends to `status=unsubscribed`.

## Analytics dashboard

`/admin/publishing/analytics` — subscribers, growth, open/click/bounce rates, sources, topics, most distributed articles.

## Tests

```bash
cd /workspace && NEWSLETTER_DRY_RUN=1 node --test server/services/publishing/publishing.test.js
```

## Remaining work

- Wire Resend webhook → open/click events
- Live LinkedIn/X/Telegram API posting (packs are generated today)
- Sync file store ↔ Supabase subscribers in both directions on boot
- Welcome email via Resend template
- CAPTCHA on public subscribe for production
