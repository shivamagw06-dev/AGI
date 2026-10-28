# Fix: cannot sign up / no verification email

## Confirmed production failures (fixed)

### 1) Database trigger (fixed in Supabase)

Supabase Auth returned `Database error saving new user` because three
`auth.users` AFTER INSERT triggers used `ON CONFLICT` without matching unique
constraints:

| Trigger | Function | Missing constraint |
| --- | --- | --- |
| `_on_auth_user_created` | `_on_auth_user_created()` | `user_index.user_id` PK |
| `on_auth_user_created` | `handle_new_user()` | `profiles.id` PK |
| `on_auth_user_created_subscribe` | `handle_new_user_subscribe()` | `subscribers.user_id` unique |

Applied migration:

`supabase/migrations/20260811100000_fix_auth_signup_triggers_constraints.sql`

### 2) Supabase SMTP (bypassed in app)

After the trigger fix, `/auth/v1/signup` still returned:

`Error sending confirmation email` / SMTP `535 "Invalid username"`

GoTrue rolls the signup back when confirmation mail fails. AGI now creates
accounts through the Node API instead of relying on Supabase SMTP:

`POST /api/auth/signup` → `admin.createUser` + Resend branded verification

Also:

- `POST /api/auth/send-verification`
- `POST /api/auth/send-password-reset`

## Optional: repair Supabase SMTP (dashboard)

Authentication → SMTP (Resend example):

- Host: `smtp.resend.com`
- Port: `465`
- Username: `resend`
- Password: Resend API key
- Sender: `support@agarwalglobalinvestments.com`

Until SMTP is fixed, keep using the AGI branded API path.

## Deploy checklist

1. Supabase migration applied (already done on `zrvdtpxfmuijhionbaxr`)
2. Redeploy **Render** `finance-news-backend` so `/api/auth/signup` is live
3. Redeploy **Hostinger** frontend so `AuthContext` calls the AGI signup API
4. Confirm Render env has:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `RESEND_API_KEY`
   - `PUBLIC_SITE_URL=https://agarwalglobalinvestments.com`
   - `FROM_EMAIL=Agarwal Global Investments <support@agarwalglobalinvestments.com>`

## Verify

```bash
# Health
curl -sS https://finance-news-backend-19i5.onrender.com/api/auth/health

# Signup (after Render deploy)
curl -sS -X POST https://finance-news-backend-19i5.onrender.com/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"agi.probe.$(date +%s)@example.com\",\"password\":\"TestPass123!@#\",\"fullName\":\"Probe User\"}"

# Resend verification for an existing address
curl -sS -X POST https://finance-news-backend-19i5.onrender.com/api/auth/send-verification \
  -H 'Content-Type: application/json' \
  -d '{"email":"avaishnavi294@gmail.com","fullName":"Vaishnavi","redirectTo":"https://agarwalglobalinvestments.com/verify-email"}'
```

Expected signup: HTTP 201 with `ok: true` and `provider: "resend"`.
