# Production Hardening (Post-P6)

Hardening layer for treating AGIB as a production investment platform — **not a new intelligence engine**.

## Focus areas

1. **Scale testing** — Nifty500 / sample universe throughput, latency, memory
2. **Observability** — pipeline health, queues, failures, processing time, cache proxies, freshness
3. **Gold regression** — TCS, HDFCBANK, RELIANCE, NTPC, TATAMOTORS deterministic fingerprints
4. **Data quality** — freshness SLAs, provenance, duplicates, confidence
5. **Performance** — profile graph / replay / research generation

## CLI

```bash
python -m production_hardening --regression-update   # capture gold baseline
python -m production_hardening --regression          # verify vs baseline
python -m production_hardening --suite smoke         # full hardening pass
python -m production_hardening --scale sample_100
python -m production_hardening --scale nifty500      # overnight-friendly 500-name run
python -m production_hardening --dashboard
```

## APIs

```
GET /v1/production-hardening/health
GET /v1/production-hardening/dashboard
GET /v1/production-hardening/regression
POST /v1/production-hardening/regression/baseline
GET /v1/production-hardening/scale
GET /v1/production-hardening/data-quality
GET /v1/production-hardening/performance
GET /v1/production-hardening/suite
GET /v1/production-hardening/universe
```
