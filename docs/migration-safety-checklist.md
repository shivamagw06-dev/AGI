# Migration Safety Checklist

Use this checklist before approving any database migration for production.

## Change scope

- [ ] Schema changes are listed and reviewed.
- [ ] Data transformations are listed, bounded, and reversible.
- [ ] Existing data is not silently reinterpreted.
- [ ] Constraints preserve valid existing rows.
- [ ] Indexes support the expected access paths.
- [ ] Functions have explicit security and search-path behavior.

## Access control

- [ ] Row Level Security is enabled on every exposed table.
- [ ] `USING` checks ownership of the existing row.
- [ ] `WITH CHECK` checks ownership of the resulting row.
- [ ] Changing `portfolio_id` cannot transfer a row to another user.
- [ ] Authenticated clients can access only their own portfolio records.
- [ ] Authenticated clients cannot modify methodology definitions.
- [ ] Founder Portfolio private records remain founder-admin only.
- [ ] Anonymous users cannot read private records or perform writes.
- [ ] Table and function grants match the RLS design.

## Validation

- [ ] Static SQL and schema review passes.
- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] Migration dry run passes in an isolated database.
- [ ] Live RLS tests pass for User A, User B, founder admin, and anonymous roles.
- [ ] Rollback restores the previous schema, defaults, and security behavior.
- [ ] Reapplication after rollback passes.
- [ ] Full regression suite passes with no skipped dependency failures.

## Release evidence

- [ ] Migration history is consistent between the repository and the remote project.
- [ ] A reviewed rollback procedure is available before production apply.
- [ ] Production backup or recovery point is confirmed.
- [ ] Deployment owner records the migration, test results, and approval.
- [ ] Post-deployment checks cover schema objects, RLS, application health, and logs.
