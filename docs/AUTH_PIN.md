# AGI PIN Authentication

Institutional research portal auth: **email OTP once → 6-digit PIN forever on trusted devices**.

## Flow

### First visit
1. Enter email → Supabase sends a 6-digit OTP (`signInWithOtp`)
2. Verify OTP (`verifyOtp` type `email`)
3. Create a 6-digit PIN (PBKDF2 hash only — never plaintext)
4. Optionally **Trust this browser for 90 days**
5. Redirect to `/portal`

### Returning visit (same trusted browser, valid Supabase session)
1. Welcome back + email
2. Enter PIN → unlock (sessionStorage for the tab)
3. Instant access to Research Portal

### OTP again when
- New browser / device
- Trusted device expired or removed
- Explicit logout + “forget device”
- PIN reset
- Supabase session expired (long inactivity)

### Forgot PIN
OTP → create new PIN (no password).

## Security model

| Layer | Role |
|--------|------|
| Supabase Auth | Identity + long-lived session |
| `profiles.pin_hash` / `pin_salt` | Server-side PIN material (PBKDF2, 120k iters) |
| `localStorage` pin vault | Offline unlock material mirror |
| `agi_trusted_device_v1` | 90-day device trust marker |
| `sessionStorage` unlock | Per-tab lock screen |

PIN plaintext is never written to disk, network, or logs.

## Supabase setup

1. Apply migration `supabase/migrations/20260724220000_pin_auth_trusted_devices.sql`
2. Auth → Email templates: use a template that shows `{{ .Token }}` (the 6-digit code), not only the magic link
3. Keep magic-link as optional fallback — opening the link still establishes a session, then the app prompts for PIN setup/unlock

## Routes

| Path | Purpose |
|------|---------|
| `/login` | Email → OTP → PIN setup / unlock |
| `/portal` | Personalised research dashboard (requires unlocked PIN) |
| `/account` | Account + notification defaults |
| `/account/security` | Devices, PIN reset entry, forget device |

## Design

Apple × Linear × Bloomberg: white cards, navy (`#0a1e38`) accents, Georgia display type, no gradients / glassmorphism.
