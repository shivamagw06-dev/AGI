# Private Growth + Momentum experiment

Admin URL: `/admin/growth-momentum`, linked from the admin portfolio editor.

The server derives the allocation from the existing `in-growth` and `in-momentum` catalog records. Each receives 50%; each source's internal weights are retained, normalized only within the existing 0.05-point rounding tolerance. Duplicate tickers across the two sources become one holding with both contributions. Missing, incomplete, invalid or conflicting sources fail closed; the public scheduler continues without the private candidate.

The private API `/api/portfolios/admin/growth-momentum` requires the existing server-validated administrator session and returns `private, no-store`. Public catalog and tracking endpoints exclude the reserved private ID and admin-visible documents. No private holdings are bundled into frontend assets. The reserved ID cannot be created or overwritten using the flat public catalog editor.

The existing daily tracker starts this candidate on 5 October 2026 only after a full fresh Upstox quote batch. Launch units and contribution weights are frozen. Dated daily closes produce stock and composite charts after 4 pm IST. Missing prices do not produce portfolio returns. No new worker or paid service is added. The experiment uses existing protected tracking tables; no schema changes.

The comparison table shows Growth, Momentum and the combined candidate with each actual launch timestamp and latest complete date. Different launch timestamps or incomplete dates are disclosed; it is not a matched historical backtest. Fees, dividends and corporate actions remain outside automated price-return tracking. No broker orders or automatic rebalance occurs.

Validation: combination arithmetic, overlap, source identity checks, anonymous/non-admin denial, public response exclusion, and existing catalog/daily-tracking tests.
