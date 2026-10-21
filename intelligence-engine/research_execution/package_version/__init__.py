"""Package versioning — every execution stores version + execution id."""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any

from research_execution.schema import (
    ARCHITECTURE_VERSION,
    IREP_VERSION,
    RESEARCH_VERSION,
)


def new_package_ids(question: str) -> dict[str, Any]:
    ts = time.time()
    request_id = str(uuid.uuid4())
    execution_id = str(uuid.uuid4())
    fingerprint = hashlib.sha256(f"{question}|{ts}|{request_id}".encode()).hexdigest()[:16]
    return {
        "request_id": request_id,
        "execution_id": execution_id,
        "package_id": f"IREP-{fingerprint}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "unix_ts": ts,
        "version": IREP_VERSION,
        "architecture_version": ARCHITECTURE_VERSION,
        "research_version": RESEARCH_VERSION,
    }
