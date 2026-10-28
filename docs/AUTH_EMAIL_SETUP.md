# AGI branded auth email setup

Verification and password-reset emails should come from:

`support@agarwalglobalinvestments.com`

not a generic Supabase sender.

## Recommended path: Supabase custom SMTP + templates

1. In Supabase Dashboard → **Project Settings → Authentication → SMTP**
   - Enable custom SMTP (SendGrid, Resend, or Hostinger mail)
   - Sender email: `support@agarwalglobalinvestments.com`
   - Sender name: `Agarwal Global Investments`
2. In **Authentication → Email Templates**
   - Customize **Confirm signup** and **Reset password**
   - Keep the `{{ .ConfirmationURL }}` / `{{ .Token }}` placeholders
   - Brand copy to match AGI (navy `#0d1d33`, support address above)
3. In **Authentication → URL Configuration**
   - Site URL: `https://agarwalglobalinvestments.com`
   - Redirect allow list:
     - `https://agarwalglobalinvestments.com/**`
     - `https://www.agarwalglobalinvestments.com/**`
     - local Vite origin if needed

## Primary path: Node branded signup (`/api/auth/signup`)

The login page prefers:

`POST /api/auth/signup`

This creates the user with the Supabase **service role** (so broken Supabase SMTP cannot roll back the signup) and sends the AGI branded verification email via Resend/SendGrid.

Related endpoints:

- `POST /api/auth/send-verification`
- `POST /api/auth/send-password-reset`

The Node API (Render) needs these env vars:

```bash
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
FROM_EMAIL=Agarwal Global Investments <support@agarwalglobalinvestments.com>
# one of:
SENDGRID_API_KEY=...
# or
RESEND_API_KEY=...
PUBLIC_SITE_URL=https://agarwalglobalinvestments.com
```

If email provider or service-role credentials are missing, the endpoint returns `skipped: true` and Supabase’s own confirmation email remains the source of truth.

## Frontend build secrets (Hostinger)

Hostinger builds must include:

```bash
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_API_URL=https://finance-news-backend-19i5.onrender.com
```

Prefer GitHub Actions Hostinger deploy secrets over a local `build:hostinger` that might bake placeholder values.

## Auth product routes

| Route | Purpose |
| --- | --- |
| `/login` | Password signup + sign-in |
| `/verify-email` | Post-signup verification helper |
| `/forgot-password` | Request reset email |
| `/reset-password` | Set new password from email link |
| `/unlock-pin` | Device PIN unlock for trusted session |
| `/account/security` | PIN, password, logout-all |

## Security notes

- Passwords are hashed by Supabase Auth (never stored by AGI).
- Device PIN is a local browser unlock hash only; it does not replace password auth.
- `/api/auth/send-verification` is rate-limited (12 / 15 min / IP).
- Use **Sign out all devices** from the account menu or Security page for global logout.
