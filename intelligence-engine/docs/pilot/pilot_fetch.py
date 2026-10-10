"""Bounded read-only NSE pilot. Fetches filings, resolves units, writes nothing.

Conservative by construction: serial requests, a fixed floor between them, a
cache that makes a re-run cost nothing, backoff on failure, and a hard stop the
moment NSE signals throttling or blocking.
"""
import hashlib, json, os, random, sys, time, urllib.error
from datetime import datetime, timezone

SP = "/private/tmp/claude-501/-Users-shivamagarwal-Downloads-spaceanalytix/c24f664e-aa91-48a6-af6a-a3b7519affc6/scratchpad/"
CACHE = SP + "pilot_cache/"
os.makedirs(CACHE, exist_ok=True)

MIN_INTERVAL = 1.6          # seconds between requests, one at a time
MAX_RETRIES = 3
BACKOFF_BASE = 4.0
THROTTLE_CODES = {401, 403, 407, 429, 503}

_last = [0.0]
state = {"requests": 0, "cache_hits": 0, "retries": 0, "stopped": None}


def _pace():
    wait = MIN_INTERVAL - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0, 0.4))
    _last[0] = time.time()


class Throttled(Exception):
    pass


def fetch(url, opener, *, binary=False):
    """One request, cached by URL. Raises Throttled so the caller can stop."""
    key = hashlib.sha256(url.encode()).hexdigest()[:32]
    path = CACHE + key + (".bin" if binary else ".json")
    if os.path.exists(path):
        state["cache_hits"] += 1
        return open(path, "rb").read()

    from urllib.request import Request
    for attempt in range(MAX_RETRIES):
        _pace()
        try:
            req = Request(url, headers={
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
                "Accept": "application/xml,text/xml,application/json,*/*",
                "Referer": "https://www.nseindia.com/",
                "Accept-Language": "en-US,en;q=0.9",
            })
            state["requests"] += 1
            with opener.open(req, timeout=45) as resp:
                body = resp.read()
            open(path, "wb").write(body)
            return body
        except urllib.error.HTTPError as exc:
            if exc.code in THROTTLE_CODES:
                raise Throttled(f"HTTP {exc.code} on {url[:80]}")
            if attempt == MAX_RETRIES - 1:
                raise
            state["retries"] += 1
            time.sleep(BACKOFF_BASE * (2 ** attempt))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            state["retries"] += 1
            time.sleep(BACKOFF_BASE * (2 ** attempt))
    raise RuntimeError("unreachable")
