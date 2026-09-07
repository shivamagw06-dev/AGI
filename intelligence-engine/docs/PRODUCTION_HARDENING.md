# Production Hardening (Post-P6)

P6 is where foundational capability expansion pauses. This workstream hardens AGIB as a **production investment platform**.

## Priorities

1. **Scale testing** — Nifty500 / sample universes; measure throughput, latency, RSS
2. **Observability** — pipeline health, failures, processing time, cache proxies, freshness
3. **Gold regression** — TCS, HDFCBANK, RELIANCE, NTPC, TATAMOTORS fingerprints
4. **Data quality** — freshness SLAs, provenance, duplicates, confidence
5. **Performance** — profile graph traversal, decision replay, research generation

## Overnight scale (recommended)

```bash
# Warm path: cache hits only (after CompanyMemory compiled)
python -m production_hardening --scale nifty500
# mode defaults to opportunity (uses cached memory when present)

# Full hardening suite (CI / daily)
python -m production_hardening --suite smoke
python -m production_hardening --regression
```

## APIs

`/v1/production-hardening/*`

Package: `intelligence-engine/production_hardening/`
