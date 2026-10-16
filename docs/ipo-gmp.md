# Daily mainboard GMP

Xflot public API: https://www.xflot.com/api-docs. No key. One bulk request per noon-to-noon IST cycle (refresh within one hour after noon), startup catch-up and hourly scheduler checks. Failed requests retry no sooner than 15 minutes. No new service or paid plan.

Only exact unambiguous symbol/name matches on open mainboard issues are attached to the existing IPO list. Missing values stay null; zero/negative premiums are valid. Disputed quotes and issue-price conflicts are withheld. Provider record updatedAt is not treated as the GMP observation time: UI shows our collection time separately. Attribution and the provider disclaimer travel with quotes.

Snapshots (up to 365) are written atomically to DATA_DIR/ipo-gmp-xflot.json, default ./data. Durability across deploys requires DATA_DIR on a persistent volume; without one history is only local cache. This is not a durable public GMP chart feature. On a failed refresh the last in-process/disk quote remains explicitly stale.

Test: node --test server/services/ipoGmp.test.js
