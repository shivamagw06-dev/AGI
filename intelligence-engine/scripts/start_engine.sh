#!/usr/bin/env bash
# Start HTTP (uvicorn) + gather sidecar as separate processes on one instance.
#
# Why: FSE/CGL/FAA in the uvicorn process starve Ask / Mission Control.
# Separate OS processes share the Render disk but not the asyncio event loop.
#
# Set AGI_GATHER_SIDECAR=false to run HTTP only (use dedicated worker instead).
set -euo pipefail

cd "$(dirname "$0")/.."

# Render stores env values in multi-line textareas, so a trailing newline or
# space is invisible in the dashboard but fatal to a string comparison:
# "true\n" == "true" is false in bash. On 2026-08-19 the dashboard showed
# CID_DOSSIER_PAUSED=true and CID_DOSSIER_WORKER_ENABLED=false while the boot
# log still read "launching continuous company dossier worker now".
#
# ${VAR:-default} does not save you either - it only fires when the variable is
# unset, not when it is set to "false ". Every boolean flag is normalised here
# before it is compared.
flag() {  # flag VALUE DEFAULT -> "true"/"false"
  local raw="${1-}" fallback="${2:-false}"
  raw="$(printf '%s' "${raw}" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')"
  [[ -z "${raw}" ]] && raw="${fallback}"
  case "${raw}" in
    true|1|yes|on) printf 'true' ;;
    *)             printf 'false' ;;
  esac
}

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
FULL_SIDECAR="$(flag "${AGI_GATHER_SIDECAR-}" false)"
FORECAST_SIDECAR="$(flag "${FIE_SIDECAR-}" false)"
if [[ "${FULL_SIDECAR}" == "true" || "${FORECAST_SIDECAR}" == "true" ]]; then
  # Delay + nice: let uvicorn finish boot and stay responsive before gather
  # saturates the shared Pro CPUs (was starving /v1/health + Mission Control).
  DELAY_SEC="${AGI_GATHER_SIDECAR_DELAY_SEC:-90}"
  echo "[start_engine] MODE=http+sidecar gather=${FULL_SIDECAR} forecast=${FORECAST_SIDECAR} delay=${DELAY_SEC}s"
  echo "[start_engine] WARNING: a heavy worker is starting inside the HTTP service; it competes for SQLite locks with request handlers"
  (
    sleep "${DELAY_SEC}"
    export AGI_ROLE=gather_worker
    SIDECAR_PROFILE="${AGI_GATHER_SIDECAR_PROFILE:-full}"
    if [[ "${FULL_SIDECAR}" != "true" ]]; then
      SIDECAR_PROFILE="forecast_only"
    fi
    # warehouse_only: the narrowest sidecar that can still collect history.
    #
    # The warehouse backfill has to run somewhere with the disk, and the disk is
    # attached here. The full profile would bring it, but it also switches on
    # gather-learn, the FAA collectors, KF_HD, LIDI and the morning DAG - and the
    # 19 August incident above was exactly that: background work inside the HTTP
    # process holding SQLite locks while the engine served 12-second timeouts.
    #
    # Every loop in gather_worker.py reads its own flag, so leaving the rest
    # unset leaves them off. This turns on the warehouse refresh and the archive
    # backfill and nothing else, with a small slice so the writer releases its
    # lock often rather than holding it through a long batch.
    if [[ "${SIDECAR_PROFILE}" == "warehouse_only" ]]; then
      export WAREHOUSE_BACKFILL=true
      export WAREHOUSE_BACKFILL_COMPANIES="${WAREHOUSE_BACKFILL_COMPANIES:-8}"
      export WAREHOUSE_BACKFILL_DAYS="${WAREHOUSE_BACKFILL_DAYS:-20}"
      export WAREHOUSE_BACKFILL_INTERVAL_MIN="${WAREHOUSE_BACKFILL_INTERVAL_MIN:-30}"
      echo "[start_engine] launching warehouse-only sidecar now"
      exec nice -n 10 python scripts/gather_worker.py
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

DOSSIER_PAUSED="$(flag "${CID_DOSSIER_PAUSED-}" true)"
DOSSIER_ENABLED="$(flag "${CID_DOSSIER_WORKER_ENABLED-}" false)"
if [[ "${DOSSIER_PAUSED}" == "true" ]]; then
  echo "[start_engine] company dossier worker paused"
# Default OFF, matching render.yaml (CID_DOSSIER_WORKER_ENABLED=false). This
# defaulted to true, so when the env did not reach the process the worker
# started anyway - on 2026-08-19 the boot logs read "launching continuous
# company dossier worker now" while the blueprint said it was disabled and
# paused. It runs CID_DOSSIER_WORKERS threads (15 in the blueprint) doing
# warehouse reads and OpenAI calls inside the HTTP process, 120s after boot,
# which matches the observed ~3-4 minute ramp from a healthy service to one
# answering nothing.
elif [[ "${DOSSIER_ENABLED}" == "true" ]]; then
  # Give uvicorn time to become healthy before warehouse reads and OpenAI work
  # begin. The dossier process is deliberately lower priority and defaults to
  # four threads on the live four-CPU Render web service.
  DOSSIER_DELAY_SEC="${CID_DOSSIER_START_DELAY_SECONDS:-120}"
  echo "[start_engine] MODE=http+dossier threads=${CID_DOSSIER_WORKERS:-4} delay=${DOSSIER_DELAY_SEC}s"
  echo "[start_engine] WARNING: dossier worker runs inside the HTTP process and competes for SQLite locks"
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
