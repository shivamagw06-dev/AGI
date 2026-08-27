"""Document processing — format detection + text/table/metadata extraction."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

from app.aoi.models import DocumentArtifact, DocumentFormat


_FORMAT_HINTS: list[tuple[str, DocumentFormat]] = [
    (r"\.pdf($|\?)", "pdf"),
    (r"\.html?($|\?)", "html"),
    (r"\.xml($|\?)", "xml"),
    (r"\.json($|\?)", "json"),
    (r"\.csv($|\?)", "csv"),
    (r"\.xlsx?($|\?)", "xlsx"),
    (r"\.txt($|\?)", "txt"),
    (r"\.zip($|\?)", "zip"),
]


def detect_format(artifact: DocumentArtifact) -> DocumentFormat:
    if artifact.format and artifact.format != "unknown":
        return artifact.format  # type: ignore[return-value]
    url = (artifact.url or "").lower()
    for pattern, fmt in _FORMAT_HINTS:
        if re.search(pattern, url):
            return fmt
    text = (artifact.content_text or "").lstrip()
    if text.startswith("{") or text.startswith("["):
        return "json"
    if text.startswith("<"):
        return "html" if "<html" in text.lower() or "<div" in text.lower() else "xml"
    if "," in text and "\n" in text:
        return "csv"
    return "txt"


def parse_artifact(artifact: DocumentArtifact) -> DocumentArtifact:
    art = artifact.model_copy(deep=True)
    fmt = detect_format(art)
    art.format = fmt
    text = art.content_text or ""
    tables: list[dict[str, Any]] = []
    meta: dict[str, Any] = dict(art.metadata or {})
    meta["detected_format"] = fmt

    if fmt == "json":
        try:
            data = json.loads(text) if text else {}
            meta["json_keys"] = list(data.keys()) if isinstance(data, dict) else ["list"]
            art.content_text = json.dumps(data, indent=2) if not isinstance(data, str) else data
        except json.JSONDecodeError:
            meta["parse_warning"] = "invalid_json"
    elif fmt == "csv":
        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)[:50]
            tables.append({"name": "csv_table", "rows": rows})
            meta["csv_rows"] = len(rows)
        except Exception:
            meta["parse_warning"] = "invalid_csv"
    elif fmt in {"html", "xml"}:
        # Lightweight tag strip for offline pipeline
        cleaned = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
        cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.I)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            art.content_text = cleaned
        meta["html_stripped"] = True
    elif fmt == "pdf":
        meta["pdf_text_layer"] = "synthetic_or_extracted"
    elif fmt == "zip":
        meta["archive"] = True

    # Simple key:value table extraction
    kv_rows = []
    for line in (art.content_text or "").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            if 1 <= len(k.strip()) <= 40:
                kv_rows.append({"key": k.strip(), "value": v.strip()})
    if kv_rows:
        tables.append({"name": "key_values", "rows": kv_rows[:100]})

    art.tables = tables
    art.metadata = meta
    art.status = "parsed"
    return art
