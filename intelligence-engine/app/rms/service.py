"""RMS service facade — institutional research workflow from idea to publication."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from app.core.config import get_settings
from app.rms.dashboard import build_dashboard
from app.rms.flags import RmsFlags
from app.rms.models import (
    ApprovalRecord,
    ApproveRequest,
    ComplianceRecord,
    DraftRequest,
    PublishRequest,
    PublishingHistoryEntry,
    ResearchObject,
    ResearchRequestCreate,
    ResearchStatus,
    ReviewComment,
    ReviewDecision,
    ReviewRequest,
    ReviewType,
    RmsDashboard,
)
from app.rms.publish import build_publication_artifacts, kip_ingest_payload
from app.rms.store import RmsStore
from app.rms.workflow import WorkflowError, bump_version, transition


class RmsService:
    def __init__(
        self,
        store: RmsStore | None = None,
        flags: RmsFlags | None = None,
        *,
        kip: Any | None = None,
        rsp: Any | None = None,
    ) -> None:
        self.flags = flags or RmsFlags.from_settings(get_settings())
        self.store = store or RmsStore()
        self.kip = kip
        self.rsp = rsp

    # ── Request / Idea ──────────────────────────────────────────────
    def create_request(self, req: ResearchRequestCreate) -> ResearchObject:
        self._require(self.flags.rms, "RMS")
        obj = ResearchObject(
            title=req.title,
            status=ResearchStatus.IDEA,
            owner=req.owner,
            reviewer=req.reviewer,
            tickers=[t.upper() for t in req.tickers],
            sectors=list(req.sectors),
            themes=list(req.themes),
            idea_summary=req.idea_summary or req.request_brief,
            request_brief=req.request_brief or req.idea_summary,
            prediction_horizon=req.prediction_horizon,
            engine_snapshot=dict(req.engine_snapshot or {}),
            assignments={"owner": req.owner, **({"reviewer": req.reviewer} if req.reviewer else {})},
            metadata=dict(req.metadata or {}),
            compliance=ComplianceRecord(
                document_versions=["v1"],
                engine_versions={k: "snapshot" for k in (req.engine_snapshot or {})},
            ),
        )
        transition(obj, ResearchStatus.RESEARCH_REQUEST, actor=req.owner, details={"title": req.title})

        if req.collect_knowledge:
            transition(obj, ResearchStatus.KNOWLEDGE_COLLECTION, actor="system")
            self._collect_knowledge(obj)

        if req.run_rsp:
            transition(obj, ResearchStatus.RSP_REASONING, actor="system")
            self._run_rsp(obj)

        # Land in draft after automated collection/reasoning
        if obj.status in {ResearchStatus.KNOWLEDGE_COLLECTION, ResearchStatus.RSP_REASONING}:
            transition(obj, ResearchStatus.DRAFT, actor="system", details={"auto": True})

        self.store.put(obj)
        return obj

    # ── Draft ───────────────────────────────────────────────────────
    def create_or_update_draft(self, req: DraftRequest) -> ResearchObject:
        self._require(self.flags.rms, "RMS")
        if req.research_id:
            obj = self._get(req.research_id)
            if obj.status == ResearchStatus.REVISION_REQUESTED:
                bump_version(obj, actor=req.owner or obj.owner, reason="revision_draft")
                transition(obj, ResearchStatus.DRAFT, actor=req.owner or obj.owner)
            elif obj.status not in {
                ResearchStatus.DRAFT,
                ResearchStatus.RSP_REASONING,
                ResearchStatus.KNOWLEDGE_COLLECTION,
                ResearchStatus.RESEARCH_REQUEST,
            }:
                # allow updating draft body while in draft; otherwise require revision path
                if obj.status != ResearchStatus.DRAFT:
                    raise WorkflowError(f"Cannot draft from status {obj.status.value}")
            if req.title:
                obj.title = req.title
            if req.draft_body:
                obj.draft_body = req.draft_body
            if req.tickers:
                obj.tickers = [t.upper() for t in req.tickers]
            if req.engine_snapshot:
                obj.engine_snapshot = dict(req.engine_snapshot)
            if req.run_rsp:
                if obj.status != ResearchStatus.RSP_REASONING:
                    # move through reasoning if coming from earlier states
                    if obj.status in {
                        ResearchStatus.RESEARCH_REQUEST,
                        ResearchStatus.KNOWLEDGE_COLLECTION,
                    }:
                        if obj.status == ResearchStatus.RESEARCH_REQUEST:
                            transition(obj, ResearchStatus.KNOWLEDGE_COLLECTION, actor=obj.owner)
                            self._collect_knowledge(obj)
                        transition(obj, ResearchStatus.RSP_REASONING, actor="system")
                    elif obj.status == ResearchStatus.DRAFT:
                        # refresh reasoning without leaving draft permanently
                        self._run_rsp(obj)
                if obj.status == ResearchStatus.RSP_REASONING:
                    self._run_rsp(obj)
                    transition(obj, ResearchStatus.DRAFT, actor=obj.owner)
            if obj.status != ResearchStatus.DRAFT and obj.status in {
                ResearchStatus.KNOWLEDGE_COLLECTION,
                ResearchStatus.RSP_REASONING,
            }:
                transition(obj, ResearchStatus.DRAFT, actor=obj.owner)
        else:
            obj = ResearchObject(
                title=req.title or "Untitled draft",
                status=ResearchStatus.IDEA,
                owner=req.owner,
                tickers=[t.upper() for t in req.tickers],
                draft_body=req.draft_body,
                engine_snapshot=dict(req.engine_snapshot or {}),
                assignments={"owner": req.owner},
            )
            transition(obj, ResearchStatus.RESEARCH_REQUEST, actor=req.owner)
            transition(obj, ResearchStatus.KNOWLEDGE_COLLECTION, actor="system")
            self._collect_knowledge(obj)
            if req.run_rsp:
                transition(obj, ResearchStatus.RSP_REASONING, actor="system")
                self._run_rsp(obj)
            transition(obj, ResearchStatus.DRAFT, actor=req.owner)

        obj.updated_at = _dt.datetime.now(_dt.timezone.utc)
        if req.submit_for_review:
            self._require(self.flags.rms_review, "RMS_REVIEW")
            transition(obj, ResearchStatus.INTERNAL_REVIEW, actor=req.owner or obj.owner)
        self.store.put(obj)
        return obj

    # ── Review ──────────────────────────────────────────────────────
    def review(self, req: ReviewRequest) -> ResearchObject:
        self._require(self.flags.rms, "RMS")
        self._require(self.flags.rms_review, "RMS_REVIEW")
        obj = self._get(req.research_id)
        comment = ReviewComment(
            author=req.author,
            body=req.body,
            decision=req.decision,
            review_type=req.review_type,
        )
        obj.compliance.review_history.append(comment)
        obj.reviewer = req.author
        obj.assignments["reviewer"] = req.author

        if req.decision == ReviewDecision.COMMENT:
            # ensure in a review queue
            if obj.status == ResearchStatus.DRAFT:
                if req.review_type == ReviewType.COMPLIANCE:
                    transition(obj, ResearchStatus.INTERNAL_REVIEW, actor=req.author)
                    transition(obj, ResearchStatus.COMPLIANCE_REVIEW, actor=req.author)
                else:
                    transition(obj, ResearchStatus.INTERNAL_REVIEW, actor=req.author)
            elif obj.status == ResearchStatus.INTERNAL_REVIEW and req.review_type == ReviewType.COMPLIANCE:
                transition(obj, ResearchStatus.COMPLIANCE_REVIEW, actor=req.author)
        elif req.decision == ReviewDecision.REQUEST_REVISION:
            transition(obj, ResearchStatus.REVISION_REQUESTED, actor=req.author, details={"body": req.body})
        elif req.decision == ReviewDecision.REJECT:
            transition(obj, ResearchStatus.REJECTED, actor=req.author, details={"body": req.body})
            obj.compliance.approvals.append(
                ApprovalRecord(
                    approver=req.author,
                    role=req.review_type.value,
                    decision="rejected",
                    notes=req.body,
                )
            )
        elif req.decision == ReviewDecision.APPROVE:
            if req.review_type == ReviewType.COMPLIANCE or obj.status == ResearchStatus.COMPLIANCE_REVIEW:
                if obj.status == ResearchStatus.DRAFT:
                    transition(obj, ResearchStatus.INTERNAL_REVIEW, actor=req.author)
                if obj.status == ResearchStatus.INTERNAL_REVIEW:
                    transition(obj, ResearchStatus.COMPLIANCE_REVIEW, actor=req.author)
                # compliance approve → approved requires RMS_APPROVAL path; treat as advance
                if self.flags.rms_approval:
                    transition(obj, ResearchStatus.APPROVED, actor=req.author)
                    obj.compliance.approvals.append(
                        ApprovalRecord(
                            approver=req.author,
                            role="compliance",
                            decision="approved",
                            notes=req.body,
                        )
                    )
            else:
                # internal approve advances to compliance review
                if obj.status == ResearchStatus.DRAFT:
                    transition(obj, ResearchStatus.INTERNAL_REVIEW, actor=req.author)
                if obj.status == ResearchStatus.INTERNAL_REVIEW:
                    transition(obj, ResearchStatus.COMPLIANCE_REVIEW, actor=req.author)
                obj.compliance.approvals.append(
                    ApprovalRecord(
                        approver=req.author,
                        role="internal",
                        decision="approved",
                        notes=req.body,
                    )
                )

        obj.updated_at = _dt.datetime.now(_dt.timezone.utc)
        self.store.put(obj)
        return obj

    # ── Approve ─────────────────────────────────────────────────────
    def approve(self, req: ApproveRequest) -> ResearchObject:
        self._require(self.flags.rms, "RMS")
        self._require(self.flags.rms_approval, "RMS_APPROVAL")
        obj = self._get(req.research_id)
        # Normalize into compliance review then approve
        if obj.status == ResearchStatus.DRAFT:
            transition(obj, ResearchStatus.INTERNAL_REVIEW, actor=req.approver)
        if obj.status == ResearchStatus.INTERNAL_REVIEW:
            transition(obj, ResearchStatus.COMPLIANCE_REVIEW, actor=req.approver)
        if obj.status == ResearchStatus.REVISION_REQUESTED:
            raise WorkflowError("Resolve revision before approval")
        if obj.status not in {ResearchStatus.COMPLIANCE_REVIEW, ResearchStatus.APPROVED}:
            raise WorkflowError(f"Cannot approve from status {obj.status.value}")
        if obj.status == ResearchStatus.COMPLIANCE_REVIEW:
            transition(obj, ResearchStatus.APPROVED, actor=req.approver, details={"notes": req.notes})
        obj.compliance.approvals.append(
            ApprovalRecord(
                approver=req.approver,
                role=req.role,
                decision="approved",
                notes=req.notes,
            )
        )
        obj.updated_at = _dt.datetime.now(_dt.timezone.utc)
        self.store.put(obj)
        return obj

    # ── Publish ─────────────────────────────────────────────────────
    def publish(self, req: PublishRequest) -> ResearchObject:
        self._require(self.flags.rms, "RMS")
        self._require(self.flags.rms_publish, "RMS_PUBLISH")
        obj = self._get(req.research_id)
        if obj.status != ResearchStatus.APPROVED:
            raise WorkflowError(f"Publish requires approved status, got {obj.status.value}")

        artifacts = build_publication_artifacts(obj, channels=list(req.channels))
        obj.publication_artifacts.extend(artifacts)

        # Automatic KIP ingestion
        if req.ingest_kip and self.kip is not None:
            try:
                from app.kip.models import DocumentType, IngestRequest

                payload = kip_ingest_payload(obj)
                doc = self.kip.ingest_agi(
                    IngestRequest(
                        title=payload["title"],
                        content=payload["content"],
                        author=payload["author"],
                        source="agi",
                        document_type=DocumentType.AGI_RESEARCH,
                        tickers=payload["tickers"],
                        themes=payload["themes"],
                        sectors=payload["sectors"],
                        article_id=payload["article_id"],
                        research_type="agi_research",
                        time_horizon=payload["time_horizon"],
                        date=_dt.date.today(),
                        metadata=payload["metadata"],
                    )
                )
                obj.kip_document_ids.append(doc.document_id)
                obj.publishing_history.append(
                    PublishingHistoryEntry(
                        action="kip_ingest",
                        actor=req.actor,
                        details={"document_id": doc.document_id},
                    )
                )
                # Prediction tracking via KIP post-ingest
                if req.track_predictions and getattr(self.kip, "flags", None) and self.kip.flags.kip_prediction_tracking:
                    for t in obj.tickers:
                        preds = self.kip.predictions(t)
                        for p in preds:
                            if p.document_id == doc.document_id and p.prediction_id not in obj.prediction_ids:
                                obj.prediction_ids.append(p.prediction_id)
            except Exception as exc:
                obj.publishing_history.append(
                    PublishingHistoryEntry(
                        action="kip_ingest_failed",
                        actor=req.actor,
                        details={"error": str(exc)},
                    )
                )

        transition(obj, ResearchStatus.PUBLISHED, actor=req.actor, details={"channels": list(req.channels)})
        now = _dt.datetime.now(_dt.timezone.utc)
        obj.published_at = now
        obj.compliance.publication_timestamp = now
        obj.compliance.reasoning_version = str(
            (obj.reasoning_package or {}).get("reasoning_version") or obj.reasoning_id or ""
        )
        obj.compliance.evidence_version = str(
            ((obj.evidence_package or {}).get("knowledge_version"))
            or ((obj.reasoning_package or {}).get("validation") or {}).get("reasoning_version")
            or ""
        )
        obj.updated_at = now
        self.store.put(obj)
        return obj

    def get_research(self, research_id: str) -> ResearchObject | None:
        self._require(self.flags.rms, "RMS")
        return self.store.get(research_id)

    def dashboard(self) -> RmsDashboard:
        self._require(self.flags.rms, "RMS")
        return build_dashboard(self.store.list_all())

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.rms else "disabled",
            "platform": "RMS",
            "rms_version": "rms-v1.0.1",
            "flags": self.flags.as_dict(),
            "stats": self.store.stats(),
            "lifecycle": [
                "idea",
                "research_request",
                "knowledge_collection",
                "rsp_reasoning",
                "draft",
                "internal_review",
                "compliance_review",
                "approval",
                "publication",
                "kip_ingestion",
                "prediction_tracking",
            ],
            "integrations": ["KIP", "RSP", "L4", "E10", "PredictionTracker"],
            "out_of_scope": [
                "cms_redesign",
                "website_redesign",
                "trading",
                "engine_redesign",
            ],
        }

    # ── Integrations ────────────────────────────────────────────────
    def _collect_knowledge(self, obj: ResearchObject) -> None:
        kip = self.kip
        if kip is None or not obj.tickers:
            obj.evidence_package = {"status": "skipped", "reason": "no_kip_or_tickers"}
            return
        try:
            ticker = obj.tickers[0]
            q = obj.request_brief or obj.title
            ctx = kip.research_context(q, ticker=ticker) if getattr(kip.flags, "kip_rag", False) else {}
            hv = None
            if getattr(kip.flags, "kip_house_view", False):
                hv = kip.house_view(ticker).model_dump(mode="json")
            obj.evidence_package = {
                "knowledge_version": ctx.get("knowledge_version") or "kip-v1.0.1-p1",
                "documents_retrieved": ctx.get("documents_retrieved") or [],
                "agi_research_used": ctx.get("agi_research_used") or [],
                "broker_reports_used": ctx.get("broker_reports_used") or [],
                "freshness_score": ctx.get("freshness_score"),
                "confidence_score": ctx.get("confidence_score"),
                "source_list": ctx.get("source_list") or [],
            }
            obj.house_view = hv
            # L4 / E10 from engine snapshot if provided
            if obj.engine_snapshot.get("l4"):
                obj.evidence_package["l4"] = obj.engine_snapshot["l4"]
            if obj.engine_snapshot.get("e10"):
                obj.evidence_package["e10"] = obj.engine_snapshot["e10"]
        except Exception as exc:
            obj.evidence_package = {"status": "error", "error": str(exc)}

    def _run_rsp(self, obj: ResearchObject) -> None:
        rsp = self.rsp
        if rsp is None:
            obj.reasoning_package = {"status": "skipped", "reason": "no_rsp"}
            return
        try:
            from app.rsp.models import EngineBundle, ReasonRequest

            engines = EngineBundle(
                e01=obj.engine_snapshot.get("e01"),
                e02=obj.engine_snapshot.get("e02"),
                e03=obj.engine_snapshot.get("e03"),
                e04=obj.engine_snapshot.get("e04"),
                e05=obj.engine_snapshot.get("e05"),
                e08=obj.engine_snapshot.get("e08"),
                e09=obj.engine_snapshot.get("e09"),
                e11=obj.engine_snapshot.get("e11"),
                e13=obj.engine_snapshot.get("e13"),
                e14=obj.engine_snapshot.get("e14"),
                l4=obj.engine_snapshot.get("l4"),
                e10=obj.engine_snapshot.get("e10"),
            )
            pkg = rsp.reason(
                ReasonRequest(
                    question=obj.request_brief or obj.title,
                    ticker=obj.tickers[0] if obj.tickers else None,
                    kip_context=obj.evidence_package if obj.evidence_package.get("documents_retrieved") is not None else None,
                    house_view=obj.house_view,
                    engines=engines,
                )
            )
            obj.reasoning_id = pkg.reasoning_id
            obj.reasoning_package = pkg.model_dump(mode="json")
            obj.compliance.reasoning_version = pkg.reasoning_version
            # Seed draft from synthesis if empty
            if not obj.draft_body and pkg.synthesis.research_brief:
                obj.draft_body = (
                    f"{pkg.synthesis.research_brief}\n\n"
                    f"Investment Thesis\n{pkg.synthesis.investment_thesis}\n\n"
                    f"Counter Thesis\n{pkg.synthesis.counter_thesis}\n\n"
                    f"Risks\n" + "\n".join(f"- {r}" for r in pkg.synthesis.risks) + "\n\n"
                    f"Catalysts\n" + "\n".join(f"- {c}" for c in pkg.synthesis.catalysts)
                )
        except Exception as exc:
            obj.reasoning_package = {"status": "error", "error": str(exc)}

    def _get(self, research_id: str) -> ResearchObject:
        obj = self.store.get(research_id)
        if obj is None:
            raise KeyError(f"research not found: {research_id}")
        return obj

    def _require(self, enabled: bool, name: str) -> None:
        if not enabled:
            raise RuntimeError(f"{name} is disabled")
