"""PUB-01 core objects — InstitutionalPublication + PublicationManifest."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class SourceObjectRef:
    object_type: str
    object_id: str
    label: str = ""
    provider: str = ""

    def ref_key(self) -> str:
        return f"{self.object_type}:{self.object_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "label": self.label,
            "provider": self.provider,
            "ref": self.ref_key(),
        }


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    label: str
    object_ref: str = ""
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "label": self.label,
            "object_ref": self.object_ref,
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class PublicationManifest:
    """Authoritative audit record — separate from presentation artifacts."""

    publication_type: str
    template_version: str
    generated_at: str
    source_objects: tuple[str, ...]
    renderer: str
    lineage_hash: str
    publication_id: str = ""
    template: str = ""
    engine_version: str = ""
    analyzes: bool = False
    generates_recommendations: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "publication_type": self.publication_type,
            "template_version": self.template_version,
            "generated_at": self.generated_at,
            "source_objects": list(self.source_objects),
            "renderer": self.renderer,
            "lineage_hash": self.lineage_hash,
            "publication_id": self.publication_id,
            "template": self.template,
            "engine_version": self.engine_version,
            "analyzes": False,
            "generates_recommendations": False,
            "reinterprets_evidence": False,
            "authoritative_audit_record": True,
        }


@dataclass(frozen=True)
class InstitutionalPublication:
    """Immutable composed publication — presentation view over source objects."""

    publication_id: str
    publication_type: str
    title: str
    generated_at: str
    template: str
    source_objects: tuple[SourceObjectRef, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    lineage: tuple[str, ...] = ()
    diagnostics: Optional[dict[str, Any]] = None
    sections: tuple[dict[str, Any], ...] = ()
    manifest: Optional[PublicationManifest] = None
    body_markdown: str = ""
    status: str = "generated"  # draft | generated | exported | failed
    version: str = "1"
    category: str = ""
    renderer_outputs: tuple[str, ...] = ()
    analyzes: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "publication_id": self.publication_id,
            "publication_type": self.publication_type,
            "title": self.title,
            "generated_at": self.generated_at,
            "template": self.template,
            "source_objects": [s.to_dict() for s in self.source_objects],
            "evidence": [e.to_dict() for e in self.evidence],
            "lineage": list(self.lineage),
            "diagnostics": dict(self.diagnostics or {}),
            "sections": list(self.sections),
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "body_markdown": self.body_markdown,
            "status": self.status,
            "version": self.version,
            "category": self.category,
            "renderer_outputs": list(self.renderer_outputs),
            "analyzes": False,
            "generates_recommendations": False,
            "reinterprets_evidence": False,
            "compose_only": True,
            "immutable": True,
        }


@dataclass
class PublicationPlan:
    publication_type: str
    template: str
    required_sources: tuple[str, ...]
    context: dict[str, Any] = field(default_factory=dict)
    steps: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "publication_type": self.publication_type,
            "template": self.template,
            "required_sources": list(self.required_sources),
            "context": dict(self.context),
            "steps": list(self.steps),
            "analyzes": False,
        }
