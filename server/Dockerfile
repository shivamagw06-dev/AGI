# AGIB Node API gateway (agib-api on Railway).
# Root Directory on Railway: server
FROM node:20-slim

WORKDIR /app

ENV NODE_ENV=production

# Groww Python scripts (server/scripts/groww_*.py) need pip deps.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf python3 /usr/bin/python

COPY package.json package-lock.json ./
RUN npm install --no-audit --no-fund

COPY requirements.txt ./
RUN python3 -m venv /opt/groww-venv \
    && /opt/groww-venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH="/opt/groww-venv/bin:${PATH}"

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
