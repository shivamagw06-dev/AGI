"""FLE engines — forecast creation, resolution, accuracy, calibration, learning."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.fle.config import (
    CALIBRATION_BANDS,
    DEFAULT_HORIZON_DAYS,
    METRIC_CATEGORY,
    MIN_EVIDENCE_FOR_FORECAST,
)
from app.fle.models import (
    AccuracySummary,
    CalibrationBucket,
    CalibrationSnapshot,
    Explainability,
    ForecastHealth,
    ForecastRecord,
    LearningRecord,
    OutcomeRecord,
    RelationshipEdge,
    ScenarioCase,
    new_id,
    now_iso,
)
from app.fle.store import FleStore

_NUM_RE = re.compile(r"[-+]?\d*\.?\d+")


def _parse_num(text: str | None) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = _NUM_RE.search(str(text).replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _avg(vals: list[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _horizon_label(days: int) -> str:
    if days <= 30:
        return "short"
    if days <= 90:
        return "medium"
    return "long"


def _band_for_confidence(conf: float) -> tuple[float, float, str]:
    for lo, hi, name in CALIBRATION_BANDS:
        if lo <= conf < hi:
            return lo, hi, name
    return CALIBRATION_BANDS[-1]


def _review_date(horizon_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=max(1, horizon_days))).date().isoformat()


class FleEngines:
    def __init__(self, store: FleStore, *, iie: Any | None = None, eve: Any | None = None) -> None:
        self.store = store
        self.iie = iie
        self.eve = eve

    # --- Forecast generation -------------------------------------------------

    def create_forecast(
        self,
        *,
        metric: str,
        predicted_value: str,
        company_id: str = "",
        company_symbol: str = "",
        sector_id: str = "",
        theme_ids: list[str] | None = None,
        forecast_type: str | None = None,
        direction: str = "",
        confidence: float = 0.55,
        probability: float = 0.5,
        origin: str = "user_request",
        assumptions: list[str] | None = None,
        evidence_ids: list[str] | None = None,
        evidence_links: list[dict[str, Any]] | None = None,
        horizon_days: int = DEFAULT_HORIZON_DAYS,
        tags: list[str] | None = None,
        why: str = "",
        risks: list[str] | None = None,
        thesis_id: str = "",
        risk_ids: list[str] | None = None,
        catalyst_ids: list[str] | None = None,
        owner_engine: str = "fle",
        unit: str = "",
        predicted_numeric: float | None = None,
        priority: str = "normal",
        parent_forecast_id: str = "",
        version: int = 1,
    ) -> ForecastRecord:
        assumptions = list(assumptions or [])
        evidence_ids = list(evidence_ids or [])
        evidence_links = list(evidence_links or [])
        if not assumptions:
            raise ValueError("Forecasts require explicit assumptions")
        if len(evidence_ids) + len(evidence_links) < MIN_EVIDENCE_FOR_FORECAST:
            raise ValueError("No forecast without supporting evidence")

        metric_l = (metric or "").strip().lower()
        ftype = forecast_type or METRIC_CATEGORY.get(metric_l, "company")
        num = predicted_numeric if predicted_numeric is not None else _parse_num(predicted_value)
        dir_ = direction or self._infer_direction(predicted_value, metric_l)

        # Soft enrich from IIE if available
        thesis_id = thesis_id
        dna_refs: list[str] = []
        if self.iie and company_id:
            try:
                pack = self.iie.company(company_id, analyse_if_missing=False)
                if isinstance(pack, dict):
                    thesis_id = thesis_id or (pack.get("thesis") or {}).get("thesis_id") or ""
                    sector_id = sector_id or ((pack.get("profile") or {}).get("sections") and "") or sector_id
                    if pack.get("dna"):
                        dna_refs = list((pack["dna"].get("dimensions") or {}).keys())[:8]
                    if not theme_ids:
                        theme_ids = [t.get("theme_id") for t in (pack.get("themes") or []) if t.get("theme_id")]
            except Exception:
                pass

        bull = ScenarioCase(
            case_type="bull",
            probability=0.25,
            expected_outcome=f"Upside on {metric_l}: stronger than {predicted_value}",
            drivers=["Opportunity catalysts materialise"],
            risks=list(risks or [])[:2],
            confidence=min(1.0, confidence + 0.05),
            supporting_evidence=evidence_links[:3],
        )
        base = ScenarioCase(
            case_type="base",
            probability=0.5,
            expected_outcome=predicted_value,
            drivers=["Continuation of evidenced trends"],
            risks=list(risks or [])[:3],
            confidence=confidence,
            supporting_evidence=evidence_links[:3],
        )
        bear = ScenarioCase(
            case_type="bear",
            probability=0.25,
            expected_outcome=f"Downside on {metric_l} vs {predicted_value}",
            drivers=["Risks crystallise"],
            risks=list(risks or []) or ["Assumption failure"],
            confidence=max(0.0, confidence - 0.05),
            supporting_evidence=evidence_links[:3],
        )

        explain = Explainability(
            why=why
            or f"Forecast for {metric_l} derived from {len(evidence_ids) or len(evidence_links)} evidence links and explicit assumptions.",
            supporting_evidence=evidence_links[:12],
            assumptions=assumptions,
            risks=list(risks or []),
            alternative_scenarios=["bull", "base", "bear"],
            historical_similar_cases=self._similar_cases(company_id, metric_l),
            expected_timeline=f"{horizon_days} days",
            confidence=confidence,
            responsible_engine="fle.forecast",
            version=version,
        )

        fid = new_id("fc")
        review = _review_date(horizon_days)
        forecast = ForecastRecord(
            forecast_id=fid,
            company_id=company_id,
            company_symbol=company_symbol,
            sector_id=sector_id,
            theme_ids=list(theme_ids or []),
            forecast_type=ftype,
            metric=metric_l,
            predicted_value=str(predicted_value),
            predicted_numeric=num,
            direction=dir_,
            unit=unit,
            horizon_days=horizon_days,
            review_date=review,
            expected_resolution=review,
            status="active",
            version=version,
            owner_engine=owner_engine,
            origin=origin,
            evidence_ids=evidence_ids,
            evidence_links=evidence_links,
            thesis_id=thesis_id,
            dna_refs=dna_refs,
            risk_ids=list(risk_ids or []),
            catalyst_ids=list(catalyst_ids or []),
            confidence=float(confidence),
            probability=float(probability),
            priority=priority,
            tags=list(tags or []),
            assumptions=assumptions,
            bull=bull,
            base=base,
            bear=bear,
            explainability=explain,
            parent_forecast_id=parent_forecast_id,
            relationships=[
                {"type": "evidence", "ids": evidence_ids},
                {"type": "company", "id": company_id},
                {"type": "sector", "id": sector_id},
            ],
        )
        self.store.add_forecast(forecast)
        self._link(forecast)
        self._update_health(company_id)
        return forecast

    def create_from_iie(self, company_key: str) -> list[ForecastRecord]:
        """Generate forecasts from IIE thesis/scenarios/catalysts (origin=iie)."""
        if not self.iie:
            return []
        try:
            pack = self.iie.company(company_key, analyse_if_missing=True)
        except Exception:
            return []
        if not isinstance(pack, dict):
            return []
        company_id = pack.get("company_id") or company_key
        symbol = pack.get("symbol") or ""
        profile = pack.get("profile") or {}
        thesis = pack.get("thesis") or {}
        scenarios = pack.get("scenarios") or {}
        evidence_links = list((profile.get("explainability") or {}).get("supporting_evidence") or [])
        evidence_ids = [e.get("evidence_id") for e in evidence_links if e.get("evidence_id")]
        evidence_ids = evidence_ids or list(profile.get("evidence_ids") or [])[:8]
        if not evidence_ids and not evidence_links:
            # synthesize minimal evidence link from thesis text to satisfy invariant when IIE has content
            if thesis.get("investment_thesis"):
                evidence_links = [
                    {
                        "evidence_id": "",
                        "claim_text": thesis.get("investment_thesis", "")[:200],
                        "confidence": float(thesis.get("confidence") or profile.get("confidence") or 0.5),
                        "status": "iie_thesis",
                    }
                ]
            else:
                return []

        assumptions = [
            "Verified EVE/IIE evidence remains representative",
            "No material unresolved conflict dominates the thesis",
            "Base-case scenario assumptions hold over the forecast horizon",
        ]
        conf = float(thesis.get("confidence") or profile.get("confidence") or 0.5)
        growth = str((profile.get("sections") or {}).get("growth_outlook") or thesis.get("investment_thesis") or "")
        created: list[ForecastRecord] = []
        # Growth / guidance style forecast
        created.append(
            self.create_forecast(
                metric="guidance",
                predicted_value=growth[:160] or "Base case operating continuity",
                company_id=company_id,
                company_symbol=symbol,
                direction="flat",
                confidence=conf,
                origin="iie",
                assumptions=assumptions,
                evidence_ids=[e for e in evidence_ids if e],
                evidence_links=evidence_links,
                risks=[r.get("title") for r in (pack.get("risks") or [])[:4] if isinstance(r, dict)],
                thesis_id=thesis.get("thesis_id") or "",
                catalyst_ids=[c.get("catalyst_id") for c in (pack.get("catalysts") or [])[:4] if isinstance(c, dict)],
                risk_ids=[r.get("risk_id") for r in (pack.get("risks") or [])[:4] if isinstance(r, dict)],
                why="Generated from IIE investment thesis and verified evidence.",
                tags=["iie", "auto"],
            )
        )
        # Margin forecast if profitability section present
        margins = str((profile.get("sections") or {}).get("profitability") or "")
        if margins:
            created.append(
                self.create_forecast(
                    metric="margins",
                    predicted_value=margins[:160],
                    company_id=company_id,
                    company_symbol=symbol,
                    direction="flat",
                    confidence=conf * 0.95,
                    origin="iie",
                    assumptions=assumptions + ["Margin structure stable absent commodity shock"],
                    evidence_ids=[e for e in evidence_ids if e],
                    evidence_links=evidence_links,
                    why="Generated from IIE profitability assessment.",
                    tags=["iie", "margins"],
                )
            )
        # Scenario-linked directional forecast
        base = scenarios.get("base") or {}
        if base:
            created.append(
                self.create_forecast(
                    metric="revenue",
                    predicted_value=str((base.get("assumptions") or ["Base case revenue trajectory"])[0])[:160],
                    company_id=company_id,
                    company_symbol=symbol,
                    direction="up",
                    confidence=float(base.get("confidence") or conf),
                    probability=float(base.get("probability") or 0.5),
                    origin="iie",
                    assumptions=list(base.get("assumptions") or assumptions),
                    evidence_ids=[e for e in evidence_ids if e],
                    evidence_links=evidence_links or list(base.get("supporting_evidence") or []),
                    risks=list(base.get("risks") or []),
                    why="Generated from IIE base-case scenario.",
                    tags=["iie", "scenario", "base"],
                )
            )
        return created

    def version_forecast(self, forecast_id: str, **updates: Any) -> ForecastRecord:
        """Create a new version; mark prior as superseded — never overwrite."""
        prior = self.store.forecasts.get(forecast_id)
        if not prior:
            raise KeyError(f"Forecast '{forecast_id}' not found")
        self.store.mark_superseded(forecast_id)
        return self.create_forecast(
            metric=updates.get("metric", prior.metric),
            predicted_value=updates.get("predicted_value", prior.predicted_value),
            company_id=prior.company_id,
            company_symbol=prior.company_symbol,
            sector_id=prior.sector_id,
            theme_ids=prior.theme_ids,
            forecast_type=prior.forecast_type,
            direction=updates.get("direction", prior.direction),
            confidence=float(updates.get("confidence", prior.confidence)),
            probability=float(updates.get("probability", prior.probability)),
            origin=updates.get("origin", prior.origin),
            assumptions=list(updates.get("assumptions", prior.assumptions)),
            evidence_ids=list(updates.get("evidence_ids", prior.evidence_ids)),
            evidence_links=list(updates.get("evidence_links", prior.evidence_links)),
            horizon_days=int(updates.get("horizon_days", prior.horizon_days)),
            tags=list(prior.tags) + ["versioned"],
            why=updates.get("why", f"Version {prior.version + 1} of {prior.forecast_id}"),
            risks=list(prior.explainability.risks),
            thesis_id=prior.thesis_id,
            risk_ids=prior.risk_ids,
            catalyst_ids=prior.catalyst_ids,
            owner_engine=prior.owner_engine,
            unit=prior.unit,
            predicted_numeric=updates.get("predicted_numeric", prior.predicted_numeric),
            parent_forecast_id=prior.forecast_id,
            version=prior.version + 1,
        )

    # --- Resolution ----------------------------------------------------------

    def resolve(
        self,
        forecast_id: str,
        *,
        actual_value: str,
        actual_numeric: float | None = None,
        notes: str = "",
        evidence_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        fc = self.store.forecasts.get(forecast_id)
        if not fc or fc.soft_deleted:
            raise KeyError(f"Forecast '{forecast_id}' not found")
        if forecast_id in self.store.outcomes:
            return {
                "outcome": self.store.outcomes[forecast_id].to_dict(),
                "learning": self.store.learnings.get(
                    next((lid for lid, l in self.store.learnings.items() if l.forecast_id == forecast_id), ""),
                    LearningRecord(learning_id="", forecast_id=forecast_id),
                ).to_dict()
                if any(l.forecast_id == forecast_id for l in self.store.learnings.values())
                else {},
                "already_resolved": True,
            }

        pred_n = fc.predicted_numeric if fc.predicted_numeric is not None else _parse_num(fc.predicted_value)
        act_n = actual_numeric if actual_numeric is not None else _parse_num(actual_value)
        difference = None
        pct_err = None
        abs_err = None
        direction_correct = None
        magnitude_ok = None
        if pred_n is not None and act_n is not None:
            difference = round(act_n - pred_n, 6)
            abs_err = abs(difference)
            if pred_n != 0:
                pct_err = round(abs(difference / pred_n) * 100.0, 4)
            direction_correct = self._direction_match(fc.direction, pred_n, act_n)
            magnitude_ok = pct_err is not None and pct_err <= 15.0

        accuracy = self._accuracy_score(direction_correct, pct_err, fc.confidence)
        timing_ok = True  # resolved at/after review in v1
        reason = notes or self._error_reason(direction_correct, pct_err, fc.assumptions)

        outcome = OutcomeRecord(
            outcome_id=new_id("out"),
            forecast_id=forecast_id,
            predicted_value=fc.predicted_value,
            predicted_numeric=pred_n,
            actual_value=str(actual_value),
            actual_numeric=act_n,
            difference=difference,
            percentage_error=pct_err,
            absolute_error=abs_err,
            direction_correct=direction_correct,
            magnitude_ok=magnitude_ok,
            timing_ok=timing_ok,
            accuracy_score=accuracy,
            error_reason=reason,
            evidence_ids=list(evidence_ids or []),
            notes=notes,
        )
        self.store.add_outcome(outcome)
        learning = self._learn(fc, outcome)
        self.recompute_accuracy()
        self.recompute_calibration()
        self._update_health(fc.company_id)
        return {
            "outcome": outcome.to_dict(),
            "learning": learning.to_dict() if learning else {},
            "already_resolved": False,
        }

    def mark_review_due(self, *, as_of: str | None = None) -> int:
        today = as_of or datetime.now(timezone.utc).date().isoformat()
        n = 0
        for fc in self.store.active_forecasts():
            if fc.status in {"active", "pending"} and fc.review_date and fc.review_date <= today:
                fc.status = "review_due"
                n += 1
        self.store._refresh_pending()
        return n

    def auto_resolve_from_evidence(self, *, limit: int = 20) -> dict[str, Any]:
        """When review is due, attempt resolution from latest EVE evidence numeric values."""
        self.mark_review_due()
        due = [f for f in self.store.active_forecasts(status="review_due")][:limit]
        resolved = []
        for fc in due:
            actual = self._actual_from_eve(fc)
            if actual is None:
                continue
            try:
                out = self.resolve(fc.forecast_id, actual_value=str(actual), notes="Auto-resolved from EVE evidence")
                resolved.append(out["outcome"]["outcome_id"])
            except Exception:
                self.store.metrics.forecast_failures += 1
        return {"reviewed": len(due), "resolved": len(resolved), "outcome_ids": resolved}

    # --- Accuracy / Calibration / Learning -----------------------------------

    def recompute_accuracy(self) -> AccuracySummary:
        outcomes = list(self.store.outcomes.values())
        global_sum = self._accuracy_for(outcomes, scope="global", scope_id="all")
        self.store.put_accuracy(global_sum)

        # by company / sector / metric
        by_company: dict[str, list[OutcomeRecord]] = {}
        by_sector: dict[str, list[OutcomeRecord]] = {}
        by_metric: dict[str, list[OutcomeRecord]] = {}
        for o in outcomes:
            fc = self.store.forecasts.get(o.forecast_id)
            if not fc:
                continue
            by_company.setdefault(fc.company_id or "unknown", []).append(o)
            by_sector.setdefault(fc.sector_id or "unknown", []).append(o)
            by_metric.setdefault(fc.metric or "unknown", []).append(o)
        for cid, rows in by_company.items():
            self.store.put_accuracy(self._accuracy_for(rows, scope="company", scope_id=cid))
        for sid, rows in by_sector.items():
            self.store.put_accuracy(self._accuracy_for(rows, scope="sector", scope_id=sid))
        for mid, rows in by_metric.items():
            self.store.put_accuracy(self._accuracy_for(rows, scope="metric", scope_id=mid))
        return global_sum

    def recompute_calibration(self) -> CalibrationSnapshot:
        buckets: list[CalibrationBucket] = []
        for lo, hi, name in CALIBRATION_BANDS:
            matched = []
            for o in self.store.outcomes.values():
                fc = self.store.forecasts.get(o.forecast_id)
                if not fc:
                    continue
                if lo <= fc.confidence < hi:
                    matched.append((fc, o))
            success = sum(1 for _, o in matched if (o.accuracy_score or 0) >= 0.55 or o.direction_correct)
            rate = (success / len(matched)) if matched else 0.0
            mid_conf = (lo + hi) / 2
            if not matched:
                label = "unknown"
            elif rate + 0.1 < mid_conf:
                label = "overconfident"
            elif rate > mid_conf + 0.1:
                label = "underconfident"
            else:
                label = "well_calibrated"
            buckets.append(
                CalibrationBucket(
                    band=name,
                    predicted_confidence_low=lo,
                    predicted_confidence_high=hi,
                    forecast_count=len(matched),
                    success_count=success,
                    historical_success_rate=round(rate, 4),
                    calibration_label=label,
                )
            )
        avg_conf = _avg([self.store.forecasts[o.forecast_id].confidence for o in self.store.outcomes.values() if o.forecast_id in self.store.forecasts])
        avg_success = _avg([o.accuracy_score for o in self.store.outcomes.values()])
        drift = round(avg_conf - avg_success, 4)
        snap = CalibrationSnapshot(
            snapshot_id=new_id("cal"),
            scope="global",
            scope_id="all",
            buckets=buckets,
            average_confidence=avg_conf,
            average_success=avg_success,
            calibration_drift=drift,
        )
        self.store.add_calibration(snap)
        return snap

    def _learn(self, fc: ForecastRecord, outcome: OutcomeRecord) -> LearningRecord | None:
        lessons: list[str] = []
        successful: list[str] = []
        failed: list[str] = []
        unexpected: list[str] = []
        improvements: list[str] = []
        adj: dict[str, Any] = {}

        if outcome.direction_correct:
            lessons.append("Directional call was correct.")
            successful.extend(fc.base.drivers[:3] or ["Base-case drivers held"])
        else:
            lessons.append("Directional call missed.")
            failed.extend(fc.assumptions[:3])
            improvements.append("Revisit directional assumptions and conflicting evidence.")

        if outcome.percentage_error is not None and outcome.percentage_error > 15:
            lessons.append(f"Large percentage error ({outcome.percentage_error}%).")
            unexpected.append(outcome.error_reason or "Magnitude missed")
            improvements.append("Tighten numeric ranges; require more confirming evidence.")

        # Calibration hint
        lo, hi, band = _band_for_confidence(fc.confidence)
        hist = None
        if self.store.calibration_history:
            for b in self.store.calibration_history[-1].buckets:
                if b.band == band:
                    hist = b.historical_success_rate
        if hist is not None and fc.confidence - hist > 0.1:
            adj = {
                "band": band,
                "predicted_confidence": fc.confidence,
                "historical_success": hist,
                "label": "overconfident",
                "suggested_confidence": round(max(0.2, hist), 4),
            }
            lessons.append("Confidence was overstated relative to historical success in this band.")
            improvements.append("Reduce future confidence in similar forecasts.")
        elif hist is not None and hist - fc.confidence > 0.1:
            adj = {
                "band": band,
                "predicted_confidence": fc.confidence,
                "historical_success": hist,
                "label": "underconfident",
                "suggested_confidence": round(min(0.95, hist), 4),
            }

        knowledge_updates = [
            f"Record outcome for {fc.metric} on {fc.company_id or fc.company_symbol}",
            "Feed learning into future IIE scenario/risk monitoring (soft, non-destructive)",
        ]
        text = " ".join(lessons + successful + failed + improvements)
        learning = LearningRecord(
            learning_id=new_id("learn"),
            forecast_id=fc.forecast_id,
            outcome_id=outcome.outcome_id,
            company_id=fc.company_id,
            sector_id=fc.sector_id,
            metric=fc.metric,
            lessons_learned=lessons,
            successful_drivers=successful,
            failed_assumptions=failed,
            unexpected_events=unexpected,
            confidence_adjustments=adj,
            knowledge_updates=knowledge_updates,
            future_improvements=improvements,
            searchable_text=text,
        )
        self.store.add_learning(learning)
        # Soft feed hint — do not mutate IIE history
        self.store.add_relationship(
            RelationshipEdge(
                edge_id=new_id("rel"),
                from_id=learning.learning_id,
                to_id=fc.forecast_id,
                relation_type="learned_from",
            )
        )
        return learning

    # --- Health / helpers ----------------------------------------------------

    def _update_health(self, company_id: str) -> None:
        if not company_id:
            return
        fcs = self.store.history_for_company(company_id)
        active = [f for f in fcs if not f.soft_deleted and f.status in {"active", "pending", "review_due"}]
        resolved = [f for f in fcs if f.forecast_id in self.store.outcomes]
        scores = [self.store.outcomes[f.forecast_id].accuracy_score for f in resolved]
        pending = len([f for f in active if f.status == "review_due"])
        expired = len([f for f in fcs if f.status == "expired" or f.soft_deleted])
        learnings = [l for l in self.store.learnings.values() if l.company_id == company_id]
        cal_label = "unknown"
        if self.store.calibration_history:
            # pick dominant non-unknown bucket label
            labels = [b.calibration_label for b in self.store.calibration_history[-1].buckets if b.forecast_count]
            if labels:
                cal_label = labels[0]
        freshness = active[0].created_at if active else (fcs[0].created_at if fcs else "")
        self.store.put_health(
            ForecastHealth(
                company_id=company_id,
                forecast_coverage=len({f.metric for f in fcs if not f.soft_deleted}),
                forecast_accuracy=_avg(scores),
                pending_reviews=pending,
                expired_forecasts=expired,
                average_confidence=_avg([f.confidence for f in fcs if not f.soft_deleted]),
                calibration_label=cal_label,
                learning_score=min(1.0, len(learnings) / 10.0),
                forecast_freshness=freshness,
            )
        )

    def _accuracy_for(self, outcomes: list[OutcomeRecord], *, scope: str, scope_id: str) -> AccuracySummary:
        if not outcomes:
            return AccuracySummary(scope=scope, scope_id=scope_id)
        dir_ok = [o for o in outcomes if o.direction_correct is True]
        pct = [o.percentage_error for o in outcomes if o.percentage_error is not None]
        abs_e = [o.absolute_error for o in outcomes if o.absolute_error is not None]
        scores = [o.accuracy_score for o in outcomes]
        # confidence accuracy: fraction where high confidence (>=0.7) succeeded
        conf_ok = 0
        conf_n = 0
        by_horizon: dict[str, list[float]] = {}
        for o in outcomes:
            fc = self.store.forecasts.get(o.forecast_id)
            if not fc:
                continue
            if fc.confidence >= 0.7:
                conf_n += 1
                if o.accuracy_score >= 0.55:
                    conf_ok += 1
            by_horizon.setdefault(_horizon_label(fc.horizon_days), []).append(o.accuracy_score)
        return AccuracySummary(
            scope=scope,
            scope_id=scope_id,
            forecast_count=len({o.forecast_id for o in outcomes}),
            resolved_count=len(outcomes),
            directional_accuracy=round(len(dir_ok) / len(outcomes), 4) if outcomes else 0.0,
            mean_percentage_error=round(_avg([float(x) for x in pct]), 4),
            mean_absolute_error=round(_avg([float(x) for x in abs_e]), 4),
            mean_accuracy_score=round(_avg(scores), 4),
            confidence_accuracy=round(conf_ok / conf_n, 4) if conf_n else 0.0,
            by_horizon={k: round(_avg(v), 4) for k, v in by_horizon.items()},
        )

    def _link(self, fc: ForecastRecord) -> None:
        for eid in fc.evidence_ids:
            self.store.add_relationship(
                RelationshipEdge(edge_id=new_id("rel"), from_id=fc.forecast_id, to_id=eid, relation_type="supported_by")
            )
        if fc.company_id:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"), from_id=fc.forecast_id, to_id=fc.company_id, relation_type="about_company"
                )
            )
        if fc.sector_id:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"), from_id=fc.forecast_id, to_id=fc.sector_id, relation_type="about_sector"
                )
            )

    def _similar_cases(self, company_id: str, metric: str) -> list[str]:
        out = []
        for f in self.store.active_forecasts(metric=metric)[:5]:
            if f.company_id != company_id:
                out.append(f"{f.forecast_id}:{f.company_id}:{f.predicted_value[:40]}")
        return out[:5]

    def _infer_direction(self, predicted_value: str, metric: str) -> str:
        text = (predicted_value or "").lower()
        if any(w in text for w in ("increase", "grow", "up", "expansion", "higher", "accelerate")):
            return "up"
        if any(w in text for w in ("decline", "down", "lower", "contract", "slow")):
            return "down"
        if metric in {"debt", "attrition"}:
            return "flat"
        return "range"

    def _direction_match(self, direction: str, pred: float, actual: float) -> bool:
        if direction in {"", "range", "flat"}:
            # flat/range: within 10% counts as correct directionally
            if pred == 0:
                return abs(actual) < 1e-9
            return abs(actual - pred) / abs(pred) <= 0.1
        if direction == "up":
            return actual >= pred * 0.98
        if direction == "down":
            return actual <= pred * 1.02
        return False

    def _accuracy_score(self, direction_correct: bool | None, pct_err: float | None, confidence: float) -> float:
        score = 0.0
        if direction_correct is True:
            score += 0.55
        elif direction_correct is False:
            score += 0.1
        else:
            score += 0.3
        if pct_err is not None:
            # 0% error → +0.45; 50%+ → 0
            score += max(0.0, 0.45 * (1.0 - min(pct_err, 50.0) / 50.0))
        else:
            score += 0.15
        return round(min(1.0, score), 4)

    def _error_reason(self, direction_correct: bool | None, pct_err: float | None, assumptions: list[str]) -> str:
        if direction_correct is False:
            return f"Direction missed; review assumptions: {', '.join(assumptions[:2])}"
        if pct_err is not None and pct_err > 15:
            return f"Magnitude error {pct_err}%; assumptions may have been incomplete"
        return "Within tolerance"

    def _actual_from_eve(self, fc: ForecastRecord) -> float | None:
        if not self.eve or not fc.company_id:
            return None
        try:
            listed = self.eve.list_evidence(company_id=fc.company_id, fact_key=fc.metric, limit=5)
            rows = listed.get("evidence") if isinstance(listed, dict) else []
        except Exception:
            rows = []
        for row in rows or []:
            n = _parse_num(row.get("value_text") if isinstance(row, dict) else None)
            if n is not None:
                return n
        return None
