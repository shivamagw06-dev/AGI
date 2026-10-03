# AGI newsletter emails with Resend

Use Resend for:

- welcome emails when someone subscribes
- new-article emails when you publish from CMS

Sender:

`AGI Updates <updates@agarwalglobalinvestments.com>`

Auth emails stay on:

`support@agarwalglobalinvestments.com`

## 1) Resend

1. Domain `agarwalglobalinvestments.com` must be **Verified**
2. Keep your API key ready

## 2) Render (Node API)

In your Render backend env, set:

```bash
RESEND_API_KEY=re_xxxxxxxx
NEWSLETTER_FROM_EMAIL=AGI Updates <updates@agarwalglobalinvestments.com>
PUBLIC_SITE_URL=https://agarwalglobalinvestments.com
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

Redeploy the API.

Health check:

`GET https://finance-news-backend-19i5.onrender.com/api/newsletter/health`

Expected:

```json
{ "ok": true, "resend": true, "from": "AGI Updates <updates@agarwalglobalinvestments.com>", "supabaseAdmin": true }
```

## 3) What happens automatically

- Homepage / newsletter forms → save subscriber + send welcome email
- CMS **Publish to Website** → email active subscribers about the new article

API endpoints:

- `POST /api/newsletter/welcome` `{ "email": "..." }`
- `POST /api/newsletter/notify-subscribers` `{ "title": "...", "slug": "...", "summary": "..." }`
- Legacy alias: `POST /api/notify-subscribers`

## 4) Quick test

1. Subscribe with your own email on the website
2. Confirm welcome mail from `updates@agarwalglobalinvestments.com`
3. Publish a test article from CMS
4. Confirm article mail arrives
5. Check Resend → Emails / Logs
