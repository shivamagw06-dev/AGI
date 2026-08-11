# AGIB intelligence engine — shared image for Railway web + worker services.
# Service root on Railway: intelligence-engine/ (WORKDIR /intelligence-engine).
FROM python:3.12-slim

WORKDIR /intelligence-engine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    FAA_PLAYWRIGHT_AUTO_INSTALL=false

# Minimal OS packages; Playwright --with-deps installs Chromium runtime libs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# python:3.12-slim may omit pip; ensure it is available before installing deps.
RUN python -m ensurepip --upgrade \
    && python -m pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

RUN chmod +x scripts/railway_start.sh scripts/start_engine.sh

CMD ["bash", "scripts/railway_start.sh"]
