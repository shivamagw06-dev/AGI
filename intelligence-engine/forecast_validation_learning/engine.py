"""Forecast Validation & Learning engine — close the forecasting loop."""

from __future__ import annotations

import time
from typing import Any

from forecast_validation_learning import traces
from forecast_validation_learning.bias import bias_dashboard, detect_biases
from forecast_validation_learning.calibration import calibration_report
from forecast_validation_learning.expected import extract_expected
from forecast_validation_learning.learning import generate_learning
from forecast_validation_learning.outcomes import available_entities, resolve_actual
from forecast_validation_learning.schema import (
    FVL_VERSION,
    NO_FVL_ACTIONS,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    ForecastValidation,
    RegisteredForecast,
)
from forecast_validation_learning.scoring import aggregate_scores, score_validation
from forecast_validation_learning.store import LEARNINGS, METRICS, REGISTRY, VALIDATIONS
from forecast_validation_learning.validation import (
    compare_outcomes,
    decide_status,
    validation_confidence,
)


class ForecastValidationLearningEngine:
    """Register → monitor → validate → score → learn (never rewrite history)."""

    def register_assessment(
        self,
        assessment: dict[str, Any],
        *,
        version: int | None = None,
        parent_forecast_id: str | None = None,
    ) -> dict[str, Any]:
        """Publish-gate: every forecast is registered and versioned before validation."""
        entity = str(assessment.get("entity") or "").upper()
        scope = str(assessment.get("scope") or "company")
        if not entity:
            raise ValueError("assessment.entity required")

        expected = extract_expected(assessment)
        prior = REGISTRY.list_for_entity(entity, scope=scope, limit=1)
        ver = version or ((prior[0].version + 1) if prior else 1)
        parent = parent_forecast_id or (prior[0].forecast_id if prior else None)

        forecast = RegisteredForecast(
            version=ver,
            parent_forecast_id=parent,
            entity=entity,
            entity_label=assessment.get("entity_label"),
            scope=scope,
            assessment_id=assessment.get("assessment_id"),
            scenario_report_id=assessment.get("scenario_report_id"),
            forecast_bundle_id=assessment.get("forecast_bundle_id"),
            assessment_snapshot=dict(assessment),
            expected_outcome=expected,
            status="Pending",
            published=True,
            providers_queried=list(assessment.get("providers_queried") or []),
            provenance={
                "gateway": "FVL",
                "version": FVL_VERSION,
                "source": "IPCI_assessment",
                "assessment_id": assessment.get("assessment_id"),
            },
        )
        frozen = REGISTRY.register(forecast)
        REGISTRY.record_status(frozen.forecast_id, "Monitoring", event="monitoring")
        METRICS.record(
            {
                "event": "register",
                "forecast_id": frozen.forecast_id,
                "entity": entity,
                "scope": scope,
                "version": ver,
            }
        )
        return REGISTRY.public_view(frozen)

    def register_entity(
        self,
        entity: str,
        *,
        scope: str = "company",
        question: str | None = None,
        assessment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if assessment is None:
            from institutional_probability_confidence.production import assessment as ipci_assessment

            assessment = ipci_assessment(
                ticker=entity if scope == "company" else None,
                scope=scope,
                entity=entity,
                question=question,
            )
        return self.register_assessment(assessment)

    def validate(
        self,
        forecast_id: str,
        *,
        actual_override: dict[str, Any] | None = None,
        generate_learning_record: bool = True,
    ) -> dict[str, Any]:
        span = traces.begin("forecast_validation", meta={"forecast_id": forecast_id})
        fc = REGISTRY.get(forecast_id)
        if not fc:
            traces.end(span, ok=False, output={"error": "not_found"})
            raise KeyError(f"forecast not found: {forecast_id}")

        # Immutability check — snapshot must remain identical
        snapshot_before = fc.assessment_snapshot

        actual = resolve_actual(entity=fc.entity, scope=fc.scope, override=actual_override)
        if actual is None:
            REGISTRY.record_status(forecast_id, "Indeterminate", event="no_actual")
            out = {
                "forecast_id": forecast_id,
                "entity": fc.entity,
                "validation_status": "Indeterminate",
                "reason": "no_seeded_or_provided_actual_outcome",
                "available_entities": available_entities(),
                "history_rewritten": False,
                "forecast_snapshot_unchanged": True,
            }
            traces.end(span, output=out)
            return out

        diff = compare_outcomes(fc.expected_outcome, actual)
        status = decide_status(diff, actual=actual)
        conf = validation_confidence(diff, actual)

        validation = ForecastValidation(
            forecast_id=forecast_id,
            entity=fc.entity,
            scope=fc.scope,
            forecast_date=fc.forecast_date,
            expected_outcome=fc.expected_outcome,
            actual_outcome=actual,
            difference=diff,
            validation_status=status,
            evidence=list(actual.evidence),
            confidence=conf,
            provenance={
                "gateway": "FVL",
                "version": FVL_VERSION,
                "actual_source": actual.source,
                "deterministic_rules": True,
            },
            history_rewritten=False,
        )

        sspan = traces.begin("forecast_scoring", meta={"forecast_id": forecast_id})
        score = score_validation(validation)
        validation.score = score.model_dump(mode="json")
        traces.end(sspan, output=score.model_dump(mode="json"))

        frozen = VALIDATIONS.append(validation)
        REGISTRY.record_status(forecast_id, status, event="validated")

        # Guarantee snapshot unchanged
        assert REGISTRY.get(forecast_id).assessment_snapshot == snapshot_before

        learning_out = None
        if generate_learning_record and status != "Pending":
            lspan = traces.begin("forecast_learning", meta={"forecast_id": forecast_id})
            learning = generate_learning(frozen)
            LEARNINGS.append(learning)
            learning_out = learning.to_public_dict()
            self._soft_wire_ilo(learning_out, frozen)
            traces.end(
                lspan,
                output={
                    "learning_id": learning.learning_id,
                    "category": learning.category,
                    "history_rewritten": False,
                },
            )

        cspan = traces.begin("forecast_calibration", meta={"entity": fc.entity})
        cal = calibration_report(VALIDATIONS.list_all(limit=500))
        traces.end(
            cspan,
            output={
                "n": cal["probability"]["n"],
                "alerts": cal["probability"].get("alerts") or [],
            },
        )

        METRICS.record(
            {
                "event": "validate",
                "forecast_id": forecast_id,
                "entity": fc.entity,
                "status": status,
                "overall_score": score.overall,
            }
        )

        out = frozen.to_public_dict()
        out["learning"] = learning_out
        out["forecast_snapshot_unchanged"] = True
        out["registry"] = REGISTRY.public_view(fc)
        traces.end(span, output={"status": status, "overall": score.overall})
        return out

    def validate_entity(
        self,
        entity: str,
        *,
        scope: str = "company",
        question: str | None = None,
        actual_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convenience: register latest IPCI assessment then validate against actuals."""
        registered = self.register_entity(entity, scope=scope, question=question)
        return self.validate(
            registered["forecast_id"],
            actual_override=actual_override,
            generate_learning_record=True,
        )

    def get_validation(self, forecast_id: str) -> dict[str, Any]:
        fc = REGISTRY.get(forecast_id)
        if not fc:
            raise KeyError(forecast_id)
        rows = VALIDATIONS.for_forecast(forecast_id)
        return {
            "forecast": REGISTRY.public_view(fc),
            "validations": [v.to_public_dict() for v in rows],
            "latest": rows[-1].to_public_dict() if rows else None,
            "status": REGISTRY.current_status(forecast_id),
            "history_rewritten": False,
        }

    def learning(self, *, limit: int = 50, category: str | None = None) -> dict[str, Any]:
        rows = LEARNINGS.list_all(limit=limit, category=category)
        return {
            "n": len(rows),
            "learnings": [r.to_public_dict() for r in rows],
            "categories": list(
                {
                    "Company forecasting",
                    "Sector forecasting",
                    "Market forecasting",
                    "Macro forecasting",
                    "Catalyst effectiveness",
                    "Scenario quality",
                    "Probability calibration",
                    "Confidence calibration",
                }
            ),
            "history_rewritten": False,
            "knowledge_factory_updated": False,
            "process_memory": True,
        }

    def performance(self, *, scope: str | None = None, limit: int = 200) -> dict[str, Any]:
        rows = VALIDATIONS.list_all(limit=limit)
        if scope:
            rows = [v for v in rows if v.scope == scope]
        scores = aggregate_scores(rows)
        by_scope: dict[str, list] = {}
        for v in rows:
            by_scope.setdefault(v.scope, []).append(v)
        scope_scores = {k: aggregate_scores(vs) for k, vs in by_scope.items()}
        return {
            "programme": PROGRAMME,
            "scores": scores,
            "by_scope": scope_scores,
            "bias": bias_dashboard(rows),
            "trends": METRICS.recent(30),
            "history_rewritten": False,
        }

    def calibration(self) -> dict[str, Any]:
        span = traces.begin("forecast_calibration", meta={"source": "api"})
        report = calibration_report(VALIDATIONS.list_all(limit=500))
        traces.end(span, output={"n": report["probability"]["n"]})
        return {
            "programme": PROGRAMME,
            **report,
        }

    def history(self, *, entity: str | None = None, scope: str = "company", limit: int = 50) -> dict[str, Any]:
        if entity:
            forecasts = REGISTRY.list_for_entity(entity, scope=scope, limit=limit)
        else:
            forecasts = REGISTRY.list_all(limit=limit)
        return {
            "n": len(forecasts),
            "forecasts": [REGISTRY.public_view(f) for f in forecasts],
            "status_log": REGISTRY.status_log(limit=limit),
            "validations": [v.to_public_dict() for v in VALIDATIONS.list_all(limit=limit)],
            "immutable_registry": True,
            "history_rewritten": False,
        }

    def dashboard(self) -> dict[str, Any]:
        forecasts = REGISTRY.list_all(limit=200)
        validations = VALIDATIONS.list_all(limit=200)
        learnings = LEARNINGS.list_all(limit=50)
        status_counts = REGISTRY.counts_by_status()
        active = status_counts.get("Pending", 0) + status_counts.get("Monitoring", 0)
        validated_n = sum(
            status_counts.get(s, 0)
            for s in ("Validated", "Partially Correct", "Incorrect", "Indeterminate")
        )
        scores = aggregate_scores(validations)
        cal = calibration_report(validations)
        biases = detect_biases(validations)

        return {
            "board": "Forecast Validation & Learning",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": FVL_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "principles": {
                "history_never_rewritten": True,
                "validation_records_immutable": True,
                "learning_is_new_object": True,
                "no_live_providers": True,
                "no_trading_recommendations": True,
                "process_improvement_not_retraining": True,
            },
            "does_not": list(NO_FVL_ACTIONS),
            "active_forecasts": active,
            "validated_forecasts": validated_n,
            "status_counts": status_counts,
            "validation_accuracy": scores.get("validation_accuracy_pct"),
            "forecast_score": scores,
            "probability_calibration": cal["probability"],
            "confidence_calibration": cal["confidence"],
            "learning_generated": len(learnings),
            "recent_learnings": [l.to_public_dict() for l in learnings[:10]],
            "bias_indicators": [b.model_dump(mode="json") for b in biases],
            "forecast_performance_trends": METRICS.recent(25),
            "recent_validations": [v.to_public_dict() for v in validations[:10]],
            "retrieval_performance": {"traces": traces.recent(40)},
            "available_outcome_entities": available_entities(),
            "phase9_complete": True,
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": FVL_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "does_not": list(NO_FVL_ACTIONS),
            "providers_queried_always": [],
            "consumes": "IPCI Forecast Assessments (+ ISI/IFI upstream)",
            "emits": "ForecastValidation + InvestmentLearning (process memory)",
            "phase": "9.5",
            "phase9_layers": ["IFI", "ISI", "CTI", "IPCI", "FVL"],
        }

    def _soft_wire_ilo(self, learning: dict[str, Any], validation: ForecastValidation) -> None:
        """Optional soft-wire into ILO process memory — never mutates forecasts."""
        try:
            from institutional_learning_office.production import apply_learning_office

            apply_learning_office(
                question=f"FVL learning: {learning.get('topic')}",
                investment_thesis={
                    "thesis": {
                        "thesis_id": f"FVL-{validation.forecast_id}",
                        "investment_view": learning.get("learning"),
                        "lifecycle": "Closed",
                        "status": "Closed",
                    }
                },
                decision_office={
                    "decision": {
                        "decision_id": f"FVL-D-{validation.validation_id}",
                        "decision": "Process Observation",
                    }
                },
                monitoring_office={
                    "events": [
                        {
                            "explanation": learning.get("observation"),
                            "requires_review": validation.validation_status == "Incorrect",
                            "trigger": {"code": "forecast_validated"},
                            "recommended_action": learning.get("future_guidance"),
                        }
                    ]
                },
                confidence_calibration={
                    "expected_confidence": validation.expected_outcome.confidence_pct,
                    "outcome": validation.validation_status,
                },
                metadata={
                    "source": "FVL",
                    "forecast_id": validation.forecast_id,
                    "validation_id": validation.validation_id,
                    "category": learning.get("category"),
                    "history_rewritten": False,
                },
                persist=True,
            )
        except Exception:
            # Soft-wire only — FVL remains authoritative for its own learning store
            pass
