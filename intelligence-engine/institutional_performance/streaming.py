"""Streaming response helpers — chunked JSON / NDJSON for Ask AGI (PRP-01)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Generator, Iterable, Optional

from institutional_performance.schema import PRP_01_ID


def ndjson_chunks(
    events: Iterable[Dict[str, Any]],
) -> Generator[str, None, None]:
    """Yield newline-delimited JSON lines for progressive delivery."""
    for event in events:
        yield json.dumps(event, default=str) + "\n"


def stream_ask_envelope(
    *,
    query: str,
    stages: Optional[Iterable[Dict[str, Any]]] = None,
    final: Optional[Dict[str, Any]] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    Yield progressive Ask events:
      meta → stage* → final → done
    Soft improvement over single-shot JSON when clients support NDJSON.
    """
    yield {
        "type": "meta",
        "id": PRP_01_ID,
        "query": query,
        "ts": time.time(),
        "streaming": True,
    }
    for stage in stages or []:
        yield {"type": "stage", **stage, "ts": time.time()}
    if final is not None:
        yield {"type": "final", "payload": final, "ts": time.time()}
    yield {"type": "done", "ts": time.time()}


def streaming_capabilities() -> Dict[str, Any]:
    return {
        "id": PRP_01_ID,
        "formats": ["ndjson", "json"],
        "ask_events": ["meta", "stage", "final", "done"],
        "note": "Clients may request Accept: application/x-ndjson for progressive Ask.",
    }
