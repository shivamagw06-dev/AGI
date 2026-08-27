"""Explicit per-provider kill switches — independent of API key presence.

A provider may have a key configured (e.g. in the Render dashboard) but be
intentionally turned off — for example, when billing has lapsed and every
call returns 402 Payment Required, wasting a full background cycle on dead
providers. Set FAA_<PROVIDER>_ENABLED=false (env) to hard-disable a
provider everywhere, regardless of whether its API key still exists.
"""

from __future__ import annotations

import os


def provider_enabled(name: str) -> bool:
    raw = (os.environ.get(f"FAA_{name.strip().upper()}_ENABLED") or "").strip().lower()
    return raw not in {"0", "false", "no", "off"}
