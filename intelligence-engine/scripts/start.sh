#!/usr/bin/env bash
# Optional Render start helper. Default Blueprint startCommand uses uvicorn
# directly so /v1/health stays fast. Use this when you want a best-effort
# Chromium bake before the API listens.
set -euo pipefail

if [[ "${FAA_PLAYWRIGHT:-true}" != "false" && "${FAA_PLAYWRIGHT:-true}" != "0" ]]; then
  if ! python - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    b.close()
PY
  then
    python -m playwright install chromium >/tmp/playwright-install.log 2>&1 || true
  fi
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8100}"
