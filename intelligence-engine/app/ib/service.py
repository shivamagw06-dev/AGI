"""IB service facade — publish, subscribe, route, replay, observe. Never business logic."""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.ib.config import EVENT_TYPES, FUTURE_SUBSCRIBERS, PUBLISHERS, SCHEMA_VERSION
from app.ib.delivery import DeliveryEngine
from app.ib.flags import IbFlags
from app.ib.handlers import build_default_handlers, default_subscriptions
from app.ib.models import BusEvent, Subscription, TraceNode, new_id
from app.ib.replay import replay_events
from app.ib.router import explain_routing
from app.ib.schema import SchemaRegistry
from app.ib.store import IbStore


class IbService:
    """AGI Intelligence Bus — event-driven communication backbone."""

    def __init__(
        self,
        *,
        flags: IbFlags | None = None,
        store: IbStore | None = None,
        aoi: Any | None = None,
        eve: Any | None = None,
        iie: Any | None = None,
        fle: Any | None = None,
        mee: Any | None = None,
        cae: Any | None = None,
    ) -> None:
        self.flags = flags or IbFlags.from_settings(get_settings())
        self.store = store or IbStore()
        self.engines: dict[str, Any] = {
            "aoi": aoi,
            "eve": eve,
            "iie": iie,
            "fle": fle,
            "mee": mee,
            "cae": cae,
        }
        self.schema = SchemaRegistry(self.store)
        self.delivery = DeliveryEngine(
            self.store,
            retry_enabled=self.flags.ib_retry,
            dlq_enabled=self.flags.ib_dlq,
        )
        self._bootstrapped = False
        if self.flags.ib:
            self.bootstrap()

    def bind(self, **engines: Any) -> None:
        for name, eng in engines.items():
            self.engines[name] = eng
        if self.flags.ib_soft_handlers:
            for sub, fn in build_default_handlers(
                self.store,
                engines=self.engines,
                cache_invalidate=self.flags.ib_cache_invalidate,
            ).items():
                self.delivery.register_handler(sub, fn)

    def bootstrap(self) -> dict[str, Any]:
        schemas = self.schema.bootstrap()
        created = 0
        if not self.store.subscriptions:
            for spec in default_subscriptions():
                self.subscribe(spec)
                created += 1
        if self.flags.ib_soft_handlers:
            self.bind(**self.engines)
        self._bootstrapped = True
        return {"schemas_registered": schemas, "subscriptions_created": created}

    def _require(self) -> None:
        if not self.flags.ib:
            raise RuntimeError("IB is disabled (IB=false)")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.ib else "disabled",
            "layer": "AGI Intelligence Bus",
            "programme": "IB",
            "version": "ib-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "event_driven_backbone",
            "never_stores_business_knowledge": True,
            "never_business_logic": True,
            "no_redesign": [
                "kf1",
                "kcv1",
                "aoi",
                "eve",
                "iie",
                "fle",
                "mee",
                "cae",
                "kip",
                "irp",
                "rsp",
                "ask_agi",
            ],
            "publishers": list(PUBLISHERS),
            "future_subscribers": list(FUTURE_SUBSCRIBERS),
            "principles": [
                "event_driven",
                "stateless",
                "asynchronous",
                "idempotent",
                "observable",
                "replayable",
                "versioned",
                "extensible",
                "fault_tolerant",
            ],
            "flags": self.flags.as_dict(),
            "snapshot": self.store.snapshot() if self.flags.ib else {},
            "metrics": self.store.metrics.model_dump(),
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        live = [e.to_dict() for e in self.store.list_events(limit=25)]
        return {
            "programme": "IB",
            "live_events": live,
            "publishers": list(PUBLISHERS),
            "subscribers": sorted({s.subscriber for s in self.store.subscriptions.values()}),
            "subscriptions": [s.to_dict() for s in self.store.subscriptions.values()],
            "dead_letters": [d.to_dict() for d in list(self.store.dead_letters.values())[-20:]],
            "cache_invalidations": list(reversed(self.store.cache_invalidation_log[-20:])),
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
            "modules": [
                "Live Event Stream",
                "Publishers",
                "Subscribers",
                "Routing",
                "Replay",
                "Dead Letter Queue",
                "Schema Registry",
                "Delivery Metrics",
                "Latency",
                "Retries",
                "Correlation Explorer",
                "Execution Timeline",
                "Cache Invalidations",
                "Consumer Health",
            ],
        }

    def publish(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        self._require()
        t0 = time.perf_counter()
        data = dict(payload or {})
        data.update({k: v for k, v in kwargs.items() if v is not None})
        event_type = str(data.get("event_type") or "").strip()
        if not event_type:
            raise RuntimeError("event_type is required")
        category = str(data.get("category") or EVENT_TYPES.get(event_type) or "system")
        schema_version = str(data.get("schema_version") or SCHEMA_VERSION)
        errors = self.schema.validate(event_type, dict(data.get("payload") or {}), schema_version)
        # Unknown types allowed but flagged in metadata
        correlation_id = str(data.get("correlation_id") or new_id("cor"))
        causation_id = str(data.get("causation_id") or "")
        aggregate_type = str(data.get("aggregate_type") or "system")
        aggregate_id = str(data.get("aggregate_id") or "platform")
        event = BusEvent(
            event_id=str(data.get("event_id") or new_id("evt")),
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            version=int(data.get("version") or 1),
            producer=str(data.get("producer") or "system"),
            correlation_id=correlation_id,
            causation_id=causation_id,
            priority=str(data.get("priority") or "normal"),
            status="published",
            payload=dict(data.get("payload") or {}),
            metadata={
                **dict(data.get("metadata") or {}),
                "validation_errors": errors,
            },
            schema_version=schema_version,
            category=category,
            routing=str(data.get("routing") or "broadcast"),
            targets=list(data.get("targets") or []),
            topics=list(data.get("topics") or []),
            delay_ms=int(data.get("delay_ms") or 0),
        )
        if self.flags.ib_persist:
            self.store.put_event(event)
        else:
            self.store.events[event.event_id] = event  # ephemeral hold for delivery
            self.store.event_order.append(event.event_id)

        event.status = "delivering"
        deliveries = self.delivery.deliver(event)
        latency = (time.perf_counter() - t0) * 1000
        self.store.metrics.observe_publish(latency)
        return {
            "event": event.to_dict(),
            "deliveries": [d.to_dict() for d in deliveries],
            "routing": explain_routing(event, self.store.subscriptions),
            "publish_latency_ms": round(latency, 2),
            "validation_errors": errors,
        }

    def emit(
        self,
        event_type: str,
        *,
        producer: str,
        aggregate_type: str = "company",
        aggregate_id: str = "",
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        priority: str = "normal",
        routing: str = "broadcast",
        targets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Soft helper for publishers — safe no-op wrapper when used externally."""
        return self.publish(
            {
                "event_type": event_type,
                "producer": producer,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id or "unknown",
                "payload": payload or {},
                "correlation_id": correlation_id,
                "causation_id": causation_id,
                "priority": priority,
                "routing": routing,
                "targets": targets or [],
            }
        )

    def subscribe(self, spec: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        self._require()
        data = dict(spec or {})
        data.update({k: v for k, v in kwargs.items() if v is not None})
        subscriber = str(data.get("subscriber") or "").strip()
        if not subscriber:
            raise RuntimeError("subscriber is required")
        sub = Subscription(
            subscription_id=str(data.get("subscription_id") or new_id("sub")),
            subscriber=subscriber,
            event_types=list(data.get("event_types") or []),
            categories=list(data.get("categories") or []),
            priority=str(data.get("priority") or "normal"),
            retry_max=int(data.get("retry_max") or 3),
            timeout_ms=int(data.get("timeout_ms") or 2000),
            max_concurrency=int(data.get("max_concurrency") or 4),
            failure_strategy=str(data.get("failure_strategy") or "dlq"),
            version_compat=str(data.get("version_compat") or SCHEMA_VERSION),
            enabled=bool(data.get("enabled", True)),
            filter=dict(data.get("filter") or {}),
        )
        self.store.put_subscription(sub)
        return sub.to_dict()

    def list_subscriptions(self) -> dict[str, Any]:
        self._require()
        return {
            "subscriptions": [s.to_dict() for s in self.store.subscriptions.values()],
            "count": len(self.store.subscriptions),
        }

    def list_events(
        self,
        *,
        event_type: str | None = None,
        producer: str | None = None,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require()
        rows = self.store.list_events(
            event_type=event_type,
            producer=producer,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            limit=limit,
        )
        return {"events": [e.to_dict() for e in rows], "count": len(rows)}

    def history(
        self,
        *,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require()
        return self.list_events(aggregate_id=aggregate_id, correlation_id=correlation_id, limit=limit)

    def replay(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        self._require()
        if not self.flags.ib_replay:
            raise RuntimeError("IB replay is disabled (IB_REPLAY=false)")
        data = dict(payload or {})
        data.update({k: v for k, v in kwargs.items() if v is not None})
        return replay_events(
            self.store,
            self.delivery,
            consumer=data.get("consumer"),
            event_type=data.get("event_type"),
            producer=data.get("producer"),
            aggregate_id=data.get("aggregate_id"),
            aggregate_type=data.get("aggregate_type"),
            correlation_id=data.get("correlation_id"),
            company_symbol=data.get("company_symbol"),
            sector=data.get("sector"),
            since=data.get("since"),
            until=data.get("until"),
            limit=int(data.get("limit") or 100),
        )

    def metrics(self) -> dict[str, Any]:
        self._require()
        return {"metrics": self.store.metrics.model_dump(), "snapshot": self.store.snapshot()}

    def dead_letter(self, *, resolve_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        if resolve_id:
            item = self.store.dead_letters.get(resolve_id)
            if not item:
                raise KeyError(f"dead letter not found: {resolve_id}")
            item.resolved = True
            return {"resolved": item.to_dict()}
        rows = list(self.store.dead_letters.values())[-max(1, min(limit, 200)) :]
        return {"dead_letters": [d.to_dict() for d in reversed(rows)], "count": len(self.store.dead_letters)}

    def schemas(self, event_type: str | None = None) -> dict[str, Any]:
        self._require()
        rows = self.schema.list_schemas(event_type=event_type)
        return {"schemas": rows, "count": len(rows), "schema_version": SCHEMA_VERSION}

    def traces(self, correlation_id: str | None = None, event_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        if event_id and event_id in self.store.events:
            correlation_id = self.store.events[event_id].correlation_id or correlation_id
        if not correlation_id:
            # Return recent correlation groups
            recent = self.store.list_events(limit=limit)
            groups: dict[str, list[dict[str, Any]]] = {}
            for e in recent:
                groups.setdefault(e.correlation_id or e.event_id, []).append(e.to_dict())
            return {"traces": groups, "count": len(groups)}
        chain = self.store.list_events(correlation_id=correlation_id, limit=limit)
        # Order by causation chain when possible
        by_id = {e.event_id: e for e in chain}
        nodes = []
        for e in sorted(chain, key=lambda x: x.timestamp):
            subs = [
                d.subscriber
                for d in self.store.deliveries
                if d.event_id == e.event_id and d.status == "delivered"
            ]
            nodes.append(
                TraceNode(
                    event_id=e.event_id,
                    event_type=e.event_type,
                    producer=e.producer,
                    timestamp=e.timestamp,
                    causation_id=e.causation_id,
                    correlation_id=e.correlation_id,
                    subscribers=subs,
                ).to_dict()
            )
        return {
            "correlation_id": correlation_id,
            "chain": nodes,
            "length": len(nodes),
            "event_ids": [n["event_id"] for n in nodes],
            "known_causation": [e.event_id for e in chain if e.causation_id in by_id],
        }

    def publish_chain_demo(self, company_symbol: str = "INFY") -> dict[str, Any]:
        """Demonstrate acquisition → evidence → thesis → forecast → market event chain."""
        self._require()
        sym = company_symbol.upper()
        cor = new_id("cor")
        steps = [
            ("aoi", "DocumentDiscovered", {"url": f"https://example.com/{sym.lower()}/results", "company_symbol": sym}),
            ("aoi", "DocumentDownloaded", {"url": f"https://example.com/{sym.lower()}/results", "company_symbol": sym}),
            ("eve", "EvidenceVerified", {"evidence_id": f"ev_{sym.lower()}", "company_symbol": sym}),
            ("iie", "InvestmentThesisUpdated", {"company_symbol": sym, "thesis": "quality compounder"}),
            ("fle", "ForecastUpdated", {"company_symbol": sym, "metric": "revenue_growth"}),
            ("mee", "CorporateEventDetected", {"company_symbol": sym, "event_title": f"{sym} quarterly results"}),
            ("cae", "CacheInvalidated", {"scopes": ["cae", "company", "forecast", "events"], "company_symbol": sym}),
        ]
        results = []
        prev = ""
        for producer, etype, payload in steps:
            out = self.publish(
                {
                    "event_type": etype,
                    "producer": producer,
                    "aggregate_type": "company",
                    "aggregate_id": sym,
                    "payload": payload,
                    "correlation_id": cor,
                    "causation_id": prev,
                    "priority": "high",
                }
            )
            prev = out["event"]["event_id"]
            results.append(out)
        return {
            "correlation_id": cor,
            "company_symbol": sym,
            "steps": len(results),
            "events": [r["event"] for r in results],
            "trace": self.traces(correlation_id=cor),
        }

    def emit_ask_agi_activity(
        self,
        *,
        query: str,
        ticker: str | None = None,
        used_cae: bool = False,
    ) -> dict[str, Any] | None:
        """Soft emit from Ask AGI — no-op when flag off or IB disabled."""
        if not self.flags.ib or not self.flags.ib_ask_agi_emit:
            return None
        try:
            payload = {"query": query, "company_symbol": (ticker or "").upper(), "used_cae": used_cae}
            if ticker:
                return self.emit(
                    "CompanyUpdated",
                    producer="ask_agi",
                    aggregate_type="company",
                    aggregate_id=ticker.upper(),
                    payload=payload,
                    priority="low",
                )
            return self.emit(
                "HealthChanged",
                producer="ask_agi",
                aggregate_type="system",
                aggregate_id="ask_agi",
                payload=payload,
                priority="low",
            )
        except Exception:
            return None
