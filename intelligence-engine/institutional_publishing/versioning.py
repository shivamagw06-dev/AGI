"""PUB-01 versioning — reproducible publications via lineage hash + manifest."""

from __future__ import annotations

import hashlib
from typing import Any, Sequence

from institutional_publishing.models import PublicationManifest, SourceObjectRef
from institutional_publishing.schema import (
    DEFAULT_TEMPLATE_VERSION,
    PUBLICATION_ENGINE_VERSION,
    PUB_VERSION,
)


def lineage_hash(
    *,
    publication_type: str,
    template_version: str,
    source_refs: Sequence[str],
    generated_at: str = "",
) -> str:
    payload = "|".join(
        [
            publication_type,
            template_version,
            ",".join(sorted(source_refs)),
            # Exclude wall-clock from hash stability for identical sources;
            # include engine version for reproducibility class.
            PUBLICATION_ENGINE_VERSION,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def publication_id(publication_type: str, lineage: str, version: str = "1") -> str:
    raw = f"{publication_type}|{lineage}|{version}|{PUB_VERSION}"
    return f"pub-{hashlib.sha256(raw.encode()).hexdigest()[:14]}"


def build_manifest(
    *,
    publication_id: str,
    publication_type: str,
    template: str,
    template_version: str,
    generated_at: str,
    sources: Sequence[SourceObjectRef],
    renderer: str = "markdown",
) -> PublicationManifest:
    refs = tuple(s.ref_key() for s in sources)
    return PublicationManifest(
        publication_type=publication_type,
        template_version=template_version or DEFAULT_TEMPLATE_VERSION,
        generated_at=generated_at,
        source_objects=refs,
        renderer=renderer,
        lineage_hash=lineage_hash(
            publication_type=publication_type,
            template_version=template_version or DEFAULT_TEMPLATE_VERSION,
            source_refs=refs,
        ),
        publication_id=publication_id,
        template=template,
        engine_version=PUBLICATION_ENGINE_VERSION,
    )


def version_record(pub: dict[str, Any]) -> dict[str, Any]:
    manifest = pub.get("manifest") or {}
    return {
        "publication_id": pub.get("publication_id"),
        "publication_type": pub.get("publication_type"),
        "version": pub.get("version"),
        "template_version": manifest.get("template_version"),
        "generated_at": pub.get("generated_at"),
        "source_objects": list(manifest.get("source_objects") or []),
        "lineage_hash": manifest.get("lineage_hash"),
        "status": pub.get("status"),
        "reproducible": bool(manifest.get("lineage_hash")),
    }
