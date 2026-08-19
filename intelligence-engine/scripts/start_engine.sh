#!/usr/bin/env bash
# Start HTTP (uvicorn) + gather sidecar as separate processes on one instance.
#
# Why: FSE/CGL/FAA in the uvicorn process starve Ask / Mission Control.
# Separate OS processes share the Render disk but not the asyncio event loop.
#
# Set AGI_GATHER_SIDECAR=false to run HTTP only (use dedicated worker instead).
set -euo pipefail

cd "$(dirname "$0")/.."

GATHER_PID=""
DOSSIER_PID=""

cleanup() {
  if [[ -n "${GATHER_PID}" ]] && kill -0 "${GATHER_PID}" 2>/dev/null; then
    kill -TERM "${GATHER_PID}" 2>/dev/null || true
    wait "${GATHER_PID}" 2>/dev/null || true
  fi
  if [[ -n "${DOSSIER_PID}" ]] && kill -0 "${DOSSIER_PID}" 2>/dev/null; then
    kill -TERM "${DOSSIER_PID}" 2>/dev/null || true
    wait "${DOSSIER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# HTTP process: never run in-process gather loops (set before uvicorn import).
export AGI_ROLE=web
export CONTINUOUS_GATHER_LEARN=false
export FAA_BACKGROUND_COLLECTOR=false
export CONTINUOUS_HISTORICAL_BACKFILL=false
# Keep KF live collectors off in HTTP; sidecar/worker owns backfill.
export KF_HD_LIVE_COLLECTORS=false
# Live fetch for on-demand FAA + correct health reporting (collector stays off).
# Respect explicit false from the dashboard; default true when unset.
export FAA_LIVE_FETCH="${FAA_LIVE_FETCH:-true}"

# Default OFF. render.yaml sets both to "false" for this service and a
# dedicated agib-intelligence-worker exists to run them, but these defaults
# were "true", so whenever the env did not reach the process the shell default
# won and a heavy worker started inside the HTTP service anyway.
#
# That is what happened on 2026-08-19: agi.forecast_worker was logging from the
# web service while the blueprint said FIE_SIDECAR=false. Memory sat at 2.5/8 GB
# and CPU at 1-2/4, so nothing was starved - HTTP was blocked behind SQLite
# locks held by the in-process worker (see institutional_warehouse/db.py, which
# already carries lock-retry backoff). The engine served ~12s timeouts for
# hours while background work carried on.
#
# A web service is now HTTP-only unless a sidecar is explicitly switched on.
FULL_SIDECAR="${AGI_GATHER_SIDECAR:-false}"
FORECAST_SIDECAR="${FIE_SIDECAR:-false}"
if [[ ( "${FULL_SIDECAR}" != "false" && "${FULL_SIDECAR}" != "0" ) || ( "${FORECAST_SIDECAR}" != "false" && "${FORECAST_SIDECAR}" != "0" ) ]]; then
  # Delay + nice: let uvicorn finish boot and stay responsive before gather
  # saturates the shared Pro CPUs (was starving /v1/health + Mission Control).
  DELAY_SEC="${AGI_GATHER_SIDECAR_DELAY_SEC:-90}"
  echo "[start_engine] MODE=http+sidecar gather=${FULL_SIDECAR} forecast=${FORECAST_SIDECAR} delay=${DELAY_SEC}s"
  echo "[start_engine] WARNING: a heavy worker is starting inside the HTTP service; it competes for SQLite locks with request handlers"
  (
    sleep "${DELAY_SEC}"
    export AGI_ROLE=gather_worker
    SIDECAR_PROFILE="${AGI_GATHER_SIDECAR_PROFILE:-full}"
    if [[ "${FULL_SIDECAR}" == "false" || "${FULL_SIDECAR}" == "0" ]]; then
      SIDECAR_PROFILE="forecast_only"
    fi
    if [[ "${SIDECAR_PROFILE}" == "forecast_only" ]]; then
      export FIE_RUNTIME=true
      export FIE_BATCH="${FIE_BATCH:-1}"
      export FIE_INTERVAL_SECONDS="${FIE_INTERVAL_SECONDS:-180}"
      echo "[start_engine] launching forecast-only sidecar now"
      exec nice -n 10 python scripts/forecast_worker.py
    fi
    export AGI_GATHER_FORCE=true
    export CONTINUOUS_GATHER_LEARN=true
    export FAA_BACKGROUND_COLLECTOR=true
    export FAA_LIVE_FETCH=true
    export CONTINUOUS_HISTORICAL_BACKFILL=true
    export CONTINUOUS_BACKFILL_UNTIL_COMPLETE=true
    export KF_HD_LIVE_COLLECTORS=true
    export CONTINUOUS_FAA_REFRESH=true
    export CONTINUOUS_LIDI=true
    export CONTINUOUS_KF_HD=true
    export CONTINUOUS_LEARNING_LOOP=true
    export CONTINUOUS_MORNING_DAG=true
    # Milder defaults on shared box so HTTP keeps CPU share.
    export KF_HD_BACKFILL_WORKERS="${KF_HD_BACKFILL_WORKERS_SIDECAR:-1}"
    export KF_HD_BACKFILL_BATCH="${KF_HD_BACKFILL_BATCH_SIDECAR:-6}"
    export FAA_COLLECTOR_LIMIT="${FAA_COLLECTOR_LIMIT_SIDECAR:-2}"
    export FAA_MAX_WORKERS="${FAA_MAX_WORKERS_SIDECAR:-2}"
    echo "[start_engine] launching full gather sidecar now"
    exec nice -n 10 python scripts/gather_worker.py
  ) &
  GATHER_PID=$!
  echo "[start_engine] gather sidecar pid=${GATHER_PID}"
else
  echo "[start_engine] MODE=http-only (gather=${FULL_SIDECAR} forecast=${FORECAST_SIDECAR}) — workers run in agib-intelligence-worker"
fi

if [[ "${CID_DOSSIER_PAUSED:-true}" == "true" || "${CID_DOSSIER_PAUSED:-true}" == "1" ]]; then
  echo "[start_engine] company dossier worker paused"
elif [[ "${CID_DOSSIER_WORKER_ENABLED:-true}" != "false" && "${CID_DOSSIER_WORKER_ENABLED:-true}" != "0" ]]; then
  # Give uvicorn time to become healthy before warehouse reads and OpenAI work
  # begin. The dossier process is deliberately lower priority and defaults to
  # four threads on the live four-CPU Render web service.
  DOSSIER_DELAY_SEC="${CID_DOSSIER_START_DELAY_SECONDS:-120}"
  echo "[start_engine] company dossier worker scheduled in ${DOSSIER_DELAY_SEC}s (${CID_DOSSIER_WORKERS:-4} threads)"
  (
    sleep "${DOSSIER_DELAY_SEC}"
    export AGI_ROLE=dossier_worker
    echo "[start_engine] launching continuous company dossier worker now"
    exec nice -n 5 python scripts/company_dossier_worker.py
  ) &
  DOSSIER_PID=$!
  echo "[start_engine] company dossier worker pid=${DOSSIER_PID}"
else
  echo "[start_engine] company dossier worker disabled"
fi

echo "[start_engine] launching uvicorn on port ${PORT:-8100} (FAA_LIVE_FETCH=${FAA_LIVE_FETCH})"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8100}"
