# Phase 0 Acceptance Checklist

## Completed Evidence

- [x] New architecture and feature development frozen.
- [x] Git commit and branch recorded in a reproducible snapshot.
- [x] Production health endpoints captured with latency and HTTP status.
- [x] Warehouse row counts and populated tables recorded.
- [x] KIP knowledge inventory recorded.
- [x] Forecast, dossier, engine, validation, and gather states recorded.
- [x] Runtime and scheduler ownership documented.
- [x] Snapshot utility redacts sensitive field names.
- [x] Current production probe failures retained as baseline evidence.

## Backup Gate

- [x] Confirm Render persistent disk snapshot/backup completed.
- [x] Confirm Supabase database backup or point-in-time recovery is enabled.
- [ ] Record backup timestamp, owner, retention period, and restore location below.
- [ ] Perform a read-only restore verification or documented restore drill.

| Evidence | Value |
|---|---|
| Render backup timestamp | Owner confirmed completed on 2026-08-14; provider timestamp not supplied |
| Supabase backup/PITR timestamp | Daily physical backup confirmed; latest visible 2026-08-13 23:15:17 UTC |
| Backup owner | Supabase managed (database); Render disk backup owner-confirmed by AGI administrator |
| Retention | Supabase: seven daily recovery points visible; Render: not recorded |
| Logical backup artifact | `/var/data/kip/backups/warehouse-restore-test.sqlite3` |
| Backup artifact size | 9,859,317,760 bytes (about 9.86 GB) |
| Backup artifact verification | PASS: file exists, is non-empty, and begins with `SQLite format 3\0` |
| Restore verification | Partial: artifact verified; isolated SQLite read/integrity test pending |

Supabase evidence was visually confirmed in `Database > Backups > Scheduled backups`
on 14 August 2026. The dashboard explicitly states that Storage API objects are not
included; only database records and Storage metadata are covered by these backups.

The Render `intelligence-data` persistent disk backup was confirmed completed by the
AGI administrator on 14 August 2026. The Render-generated timestamp and retention
period were not provided and therefore remain explicitly unverified.

On 14 August 2026, a logical SQLite backup was created at
`/var/data/kip/backups/warehouse-restore-test.sqlite3`. A file-level verification
confirmed that the 9,859,317,760-byte artifact exists and has the canonical SQLite
header. Full `integrity_check` and `quick_check` attempts against the copy were stopped
because they consumed excessive time and the full check temporarily blocked the live
service. A subsequent restart recovered the engine, warehouse, and KIP without data
loss: the warehouse reported 57 tables and 2,438,012 rows, while KIP reported durable
disk persistence and a healthy Supabase mirror.

This evidence proves backup creation and basic artifact validity, but not complete
database recovery. Run the remaining read/integrity validation in an isolated Render
one-off job or separate recovery instance; do not repeat it in the production web
service.

## Acceptance Conditions

Phase 0 is complete only when:

1. Both database and disk-backed intelligence have verified recovery paths.
2. The generated baseline contains no failed probes, or failures are explicitly accepted.
3. Runtime ownership is approved and no recurring operation has multiple owners.
4. Baseline findings are frozen as the comparison point for Phase 1.

Do not mark Phase 0 complete merely because the documentation has been committed.

**Accepted probe exception:** the 14 August 2026 09:12 UTC snapshot contains 25
timeouts. These are explicitly accepted as the incident baseline that Phase 1 must fix;
they do not satisfy the backup gate or make Phase 0 complete.
