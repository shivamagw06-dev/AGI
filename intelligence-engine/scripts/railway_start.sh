#!/usr/bin/env bash
# Railway entrypoint — pick web engine vs background worker by service name.
#
# Railway sets RAILWAY_SERVICE_NAME per service. Both agib-intelligence-engine
# and agib-intelligence-worker share this Dockerfile; only the start path differs.
set -euo pipefail

cd "$(dirname "$0")/.."

service="${RAILWAY_SERVICE_NAME:-}"

case "${service}" in
  *worker*)
    echo "[railway_start] background worker (${service})"
    export AGI_ROLE=gather_worker
    export AGI_GATHER_FORCE=true
    exec python scripts/gather_worker.py
    ;;
  *improvement*)
    echo "[railway_start] improvement worker (${service})"
    exec python scripts/improvement_worker.py
    ;;
  *)
    echo "[railway_start] HTTP engine (${service:-unknown})"
    export AGI_ROLE=web
    export AGI_GATHER_SIDECAR="${AGI_GATHER_SIDECAR:-false}"
    exec bash scripts/start_engine.sh
    ;;
esac
