# AGI Plus — manual UPI membership

Price: ₹199 INR total for 30 days, paid manually. No automatic renewal or debit mandate.
Articles and article discovery remain free. Tool pages require an active membership; the existing admin is exempt.

## Operations

- Checkout: `/subscribe` or `/pricing`; own payment history: `/account/subscription`.
- Review queue and launch switches: `/admin/plus-payments`.
- User-confirmed destination: `8859819548@ptaxis`, payee **Shivam Agarwal**. Customers must check the name and ₹199 in their payment app before paying.
- Customers sign in, pay using the local QR/UPI link, then submit the transaction reference. This only creates a pending claim.
- Check the actual settled bank credit, amount and bank reference. A screenshot or submitted reference alone is insufficient. Approve only a real ₹199 credit. Reject unmatched claims with a customer-readable note; never include bank balances or unrelated personal details.
- Approval starts 30 days of access, or adds 30 days after an existing unrevoked expiry. Repeated approval does not extend again. Each verified bank reference can be credited only once globally.
- No real payment or durable paid membership was generated during testing. Database approval/renewal/rejection/duplicate-reference checks ran in a rolled-back transaction.
- Refunds/support are handled manually through the existing contact channel; this release does not send money, initiate refunds or collect bank credentials.

## Release and rollback

The additive migration creates four RLS-enabled server-only tables, with browser roles denied all table access and RPC execution. Only the backend's existing Supabase service-role client handles payment records. Verified bearer identities establish ownership; admin authorization never uses editable user metadata.

Deploy the API and frontend before enabling `checkout_enabled` and `enabled`. Both start false. Confirm anonymous status/admin requests return 401, signed-in admin status works, and the checkout exposes the correct ₹199 destination. Then enable both in the admin settings. For an outage, disable checkout to stop new claims; do not delete payment history or alter approved expiry dates. Disabling the page gate reverts to legacy page access and is an explicit rollback, not normal billing operation.

## Access boundary and limitations

This release gates website tool pages and protects all billing/entitlement records on the server. It does **not** make the pre-existing public research JSON, bundled source datasets or legacy data APIs confidential. A client-side route boundary is not a replacement for API authorization. Before selling exclusive raw-data access, migrate each consumer and scheduled collector to authenticated API access and replace public static datasets with protected endpoints. Do not advertise those public datasets as exclusive or fully private.

The page membership check fails closed if entitlement cannot be verified. Free article routes remain available during a billing outage. The client refreshes on focus and every five minutes; expiry uses server time. Deliberate browser-code modification is outside the page-only boundary above.

## Verification

`node --test src/lib/agiPlus.test.js src/lib/accessPolicy.test.js server/routes/agiPlus.test.js`

Coverage includes browser role/expiry rules, free article routes, UPI amount and payee, redirect safety, authenticated ownership, non-admin review denial, actual-credit confirmation requirements, and fixed payment amount. Production database grants, RLS and service-only RPC privileges were checked separately; transaction tests covered approval idempotency, renewal, duplicate bank-credit rejection and rejected claims.
