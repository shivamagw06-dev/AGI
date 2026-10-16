# LIVE DATA CERTIFICATION REPORT

**Programme:** AGIB v3.0 – Live Collector Activation & Production Verification  
**Version:** `live-collector-activation-v1.0.0`  
**Run ID:** `lidi_verify_7b650f912365`  
**Generated:** `2026-08-02T21:42:03Z`  
**Overall Live Data Readiness Score:** **3.9/10** — Not production-ready — collectors not consuming certified live institutional data.

## Freeze locks

Reasoning, Knowledge Factory, Ask Pipeline, Institutional Scheduler, and Research Office remain **frozen**. Track 2 only activates/verifies/certifies LIDI collectors.

## Collector Summary

| Collector | Official Source | Mode | Certification | Records Accepted | Validation Rate | Freshness | Replay |
|---|---|---|---|---:|---:|---|---|
| NSE Bhavcopy | NSE India | INJECTED | TESTING | 5 | 1.0 | INJECTED | OK |
| NSE Corporate Announcements | NSE India | INJECTED | TESTING | 3 | 1.0 | INJECTED | OK |
| BSE Corporate Actions | BSE India | INJECTED | TESTING | 3 | 1.0 | INJECTED | OK |
| RBI DBIE | Reserve Bank of India DBIE | INJECTED | TESTING | 7 | 1.0 | INJECTED | OK |
| Company Investor Relations | Company IR websites | INJECTED | TESTING | 2 | 1.0 | INJECTED | OK |

## Production Status

- Collectors: **5**
- CERTIFIED: **0** (requires 7 consecutive LIVE days)
- PRODUCTION_READY: **0**
- STAGING: **0**
- TESTING: **5**
- DEVELOPMENT: **0**
- All certified: **False**

## Validation Statistics

- **NSE Bhavcopy**: retrieved=5, accepted=5, rejected=0, checklist=15/16 (0.9375)
- **NSE Corporate Announcements**: retrieved=3, accepted=3, rejected=0, checklist=15/16 (0.9375)
- **BSE Corporate Actions**: retrieved=3, accepted=3, rejected=0, checklist=15/16 (0.9375)
- **RBI DBIE**: retrieved=7, accepted=7, rejected=0, checklist=15/16 (0.9375)
- **Company Investor Relations**: retrieved=2, accepted=2, rejected=0, checklist=15/16 (0.9375)

## Live Endpoint Probes

- Reachable: **0/0**
- Download OK signal: **0/0**

## Knowledge Coverage

- Object counts: `{'ALTERNATIVE_DATA': 0, 'COMPANY': 5, 'CORPORATE_EVENT': 6, 'EXPECTATION': 2, 'HISTORICAL': 1, 'MACRO': 7, 'TIMELINE': 1}`
- Pack IDs: `['lidi-bhavcopy-2026-08-02', 'lidi-announcements-2026-08-02', 'lidi-corp-actions-2026-08-02', 'lidi-rbi-macro-2026-08-02', 'lidi-company-ir-2026-08-02']`
- Fixture collectors disabled for LIDI sources: `True`

## Evidence Coverage

- Pack count: **5**
- Knowledge Factory soft emit: `{'attempted': True, 'emitted': False, 'error': "No module named 'knowledge_factory.events'"}`

## Replay Status

- Deterministic checksum replay: **PASS**
- Detail: `{'checksum_stable': True, 'fabricated': False, 'ok': True, 'sample': 'nse_bhavcopy'}`

## Platform Integration

- **Scheduler**: OK — `{'fabricated': False, 'ok': True, 'scheduler_status': {'current_run_id': None, 'current_workflow': None, 'dag': {'acyclic': True, 'dag_id': 'morning_operations_0600', 'dangling': [], 'edges': [{'from': 'universe_update', 'to': 'historical_update'}, {'from': 'historical_update', 'to': 'company_intelligence'}, {'from': 'historical_update', 'to': 'government_intelligence'}, {'from': 'company_intelligence', 'to': 'corporate_events'}, {'from': 'company_intelligence', 'to': 'industry_intelligence'}, {'from': 'industry_intelligence', 'to': 'economic_relationships'}, {'from': 'economic_relationships', 'to': 'alternative_data'}, {'from': 'company_intelligence', 'to': 'market_expectations'}, {'from': 'alternative_data', 'to': 'market_expectations'}, {'from': 'company_intelligence', 'to': 'evidence_pack_generation'}, {'from': 'market_expectations', 'to': 'evidence_pack_generation'}, {'from': 'evidence_pack_generation', 'to': 'coverage_validation'}, {'from': 'coverage_validation', 'to': 'quality_gates'}, {'from': 'quality_gates', 'to': 'mission_control'}, {'from': 'quality_gates', 'to': 'daily_health'}, {'from': 'mission_control', 'to': 'research_queue'}, {'from': 'daily_health', 'to': 'research_queue'}, {'from': 'research_queue', 'to': 'morning_reports'}, {'from': 'morning_reports', 'to': 'ready_declaration'}, {'from': 'quality_gates', 'to': 'ready_declaration'}], 'levels': [['universe_update'], ['historical_update'], ['company_intelligence', 'government_intelligence'], ['corporate_events'], ['industry_intelligence'], ['economic_relationships'], ['alternative_data'], ['market_expectations'], ['evidence_pack_generation'], ['coverage_validation'], ['quality_gates'], ['mission_control', 'daily_health'], ['research_queue'], ['morning_reports'], ['ready_declaration']], 'max_parallelism': 2, 'parallel_supported': True, 'schedule': '06:00', 'workflows': ['universe_update', 'historical_update', 'company_intelligence', 'government_intelligence', 'corporate_events', 'industry_intelligence', 'economic_relationships', 'alternative_data', 'market_expectations', 'evidence_pack_generation', 'coverage_validation', 'quality_gates', 'mission_control', 'daily_health', 'research_queue', 'morning_reports', 'ready_declaration']}, 'fabricated': False, 'freeze_locks': {'ask_pipeline': True, 'committees': True, 'continuous_adaptive_learning': True, 'decision_quality': True, 'evidence_factory': True, 'governance': True, 'intelligence_packages': True, 'knowledge_factory': True, 'no_intelligence': True, 'no_reasoning': True, 'phases_1_7': True, 'soft_wire_only': True}, 'maintenance': False, 'programme': 'AGIB v2.1 – Institutional Scheduler & Morning Operations', 'state': 'INITIALISING', 'system_ready': False, 'version': 'institutional-scheduler-v1.0.0'}, 'soft_wire_present': True}`
- **Research Office**: OK — `{'fabricated': False, 'lidi_packs_available': ['lidi-bhavcopy-2026-08-02', 'lidi-announcements-2026-08-02', 'lidi-corp-actions-2026-08-02', 'lidi-rbi-macro-2026-08-02', 'lidi-company-ir-2026-08-02'], 'note': 'Research Office soft-consumes LIDI packs; knowledge-only', 'office_health': 'ok', 'ok': True, 'ready_for_users': False}`
- **Ask Pipeline**: OK — `{'ask_health': 'ok', 'fabricated': False, 'live_objects_present': True, 'note': 'Ask soft-reads knowledge/evidence surfaces; raw LIDI payloads never reach reasoning', 'object_counts': {'ALTERNATIVE_DATA': 0, 'COMPANY': 5, 'CORPORATE_EVENT': 6, 'EXPECTATION': 2, 'HISTORICAL': 1, 'MACRO': 7, 'TIMELINE': 1}, 'ok': True}`
- **Mission Control**: OK — `{'activation_board_present': True, 'board_present': True, 'fabricated': False, 'live_collector_activation': {'all_certified': False, 'certification_summary': {'all_certified': False, 'certified_count': 0, 'collectors': 5, 'consecutive_required': 7, 'fabricated': False, 'levels': {'CERTIFIED': 0, 'DEVELOPMENT': 5, 'NOT_IMPLEMENTED': 0, 'PRODUCTION_READY': 0, 'STAGING': 0, 'TESTING': 0}, 'production_ready_or_above': 0}, 'dashboard_rows': 5, 'last_verification_run_id': None, 'north_star': 'production_certified_live_collectors', 'readiness_score': None, 'version': 'live-collector-activation-v1.0.0'}, 'live_institutional_data': {'collectors_operational': 5, 'collectors_total': 5, 'fallback_usage': 0, 'fixture_collectors_disabled': True, 'health': 'ok', 'missing_data': [], 'north_star': 'validated_live_data_not_fixtures', 'state': 'READY', 'validation_failures': 0}, 'ok': True}`
- **Reasoning untouched**: OK — `{'fabricated': False, 'ok': True, 'reasoning_frozen': True}`

## Morning Verification

- OK: **True**
- Dry run: `True`
- State: `None`
- System ready: `None`

## Quality Gates

- Passed: **True**
- Failures: `[]`

## Outstanding Failures

- `not_live:bse_corporate_actions:INJECTED`
- `not_live:company_ir:INJECTED`
- `not_live:nse_announcements:INJECTED`
- `not_live:nse_bhavcopy:INJECTED`
- `not_live:rbi_dbie:INJECTED`
- `uncertified:bse_corporate_actions:TESTING`
- `uncertified:company_ir:TESTING`
- `uncertified:nse_announcements:TESTING`
- `uncertified:nse_bhavcopy:TESTING`
- `uncertified:rbi_dbie:TESTING`

## Recommended Fixes

1. **NSE session/cookies** — Bhavcopy archives and announcement APIs frequently return 403 without a browser-like cookie jar; add an official NSE session bootstrap (still no raw→reasoning).
2. **BSE structured export** — Homepage reachability ≠ corporate-actions CSV; implement the official tabular download adapter.
3. **RBI DBIE series API** — Prefer documented DBIE SDMX/CSV endpoints over HTML home; handle TLS hostname carefully with pinned certs.
4. **Company IR adapters** — Per-issuer HTML→filing extractors (results, presentations, guidance) with checksummed PDF capture.
5. **Certification clock** — Run production morning ingestion for **7 consecutive LIVE days** with zero fixture/snapshot fallback to reach CERTIFIED.
6. **Disable KF fixture collectors in production** when LIDI mode=LIVE for the same source family (already soft-flagged).

## Snapshot Policy (enforced)

If live collection fails → latest **validated LIDI snapshot** → mark **STALE** → transparent insufficiency. **Never fixture. Never silent substitute.**

## Exit Gate Assessment

- Every collector production certified: **False**
- No fixture collector active in this verification: **True**
- Evidence packs present: **True**
- Morning scheduler verification: **True**
- Replay deterministic: **True**
- Reasoning unchanged: **True**

> Track 2 exit gate is **not** claimed complete until every collector is CERTIFIED via consecutive LIVE production days.

---
_Generated by LIDI Track 2 verifier `live-collector-activation-v1.0.0`_
