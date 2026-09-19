"""PUB-01 renderers — presentation artifacts independent from planning/building."""

from __future__ import annotations

import json
from typing import Any

from institutional_publishing.models import InstitutionalPublication
from institutional_publishing.schema import RENDERERS


def supported_renderers() -> tuple[str, ...]:
    return RENDERERS


def render(publication: InstitutionalPublication, renderer: str = "markdown") -> dict[str, Any]:
    r = str(renderer or "markdown").lower().strip()
    if r not in RENDERERS:
        return {
            "ok": False,
            "error": f"unsupported renderer: {r}",
            "supported": list(RENDERERS),
        }

    manifest = publication.manifest.to_dict() if publication.manifest else {}
    if r == "markdown":
        artifact = publication.body_markdown
        content_type = "text/markdown"
    elif r == "json":
        artifact = json.dumps(publication.to_dict(), indent=2, default=str)
        content_type = "application/json"
    elif r == "html":
        artifact = _to_html(publication)
        content_type = "text/html"
    elif r == "pdf":
        # Institutional stub: PDF bytes represented as structured payload with text layer
        # Real PDF libraries can consume `text` later without changing the publication object.
        artifact = {
            "format": "pdf-stub",
            "title": publication.title,
            "text": publication.body_markdown,
            "note": "PDF presentation artifact; manifest remains audit record",
            "manifest_lineage_hash": manifest.get("lineage_hash"),
        }
        content_type = "application/pdf+json"
    else:
        return {"ok": False, "error": f"unsupported renderer: {r}"}

    return {
        "ok": True,
        "renderer": r,
        "content_type": content_type,
        "publication_id": publication.publication_id,
        "artifact": artifact,
        "manifest": manifest,
        "presentation_only": True,
        "authoritative_audit_record": "manifest",
    }


def _to_html(publication: InstitutionalPublication) -> str:
    blocks = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{_esc(publication.title)}</title>",
        "<style>body{font-family:Georgia,serif;max-width:720px;margin:2rem auto;line-height:1.5}"
        "h1,h2{font-family:system-ui,sans-serif} .meta{color:#555;font-size:.9rem}</style>",
        "</head><body>",
        f"<h1>{_esc(publication.title)}</h1>",
        "<p class='meta'>PUB-01 compose-only · lineage preserved · "
        f"id={_esc(publication.publication_id)}</p>",
    ]
    for sec in publication.sections:
        blocks.append(f"<h2>{_esc(sec.get('title') or sec.get('key'))}</h2>")
        body = str(sec.get("body") or "").replace("\n", "<br/>")
        blocks.append(f"<p>{body}</p>")
    if publication.manifest:
        blocks.append("<h2>Manifest (audit)</h2>")
        blocks.append(
            f"<pre>{_esc(json.dumps(publication.manifest.to_dict(), indent=2))}</pre>"
        )
    blocks.append("</body></html>")
    return "\n".join(blocks)


def _esc(value: Any) -> str:
    s = str(value or "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
