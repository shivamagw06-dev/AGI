"""E05-001 Event Feature Builder — PIT event panels from FeatureSnapshot / events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.e05.features.events import PitEvent, parse_event_objects, synthesize_calendar
from app.engines.e05.mapping import REGISTRY_EVENT
from app.features.models import FeatureSnapshot
from app.features.service import FeatureRegistryService


@dataclass
class EventPanel:
    symbol: str
    as_of: str
    sector_id: str | None = None
    events: list[PitEvent] = field(default_factory=list)
    event_meta: dict[str, float] = field(default_factory=dict)
    stale: list[str] = field(default_factory=list)
    discovery: str = "pit_objects"


class EventFeatureBuilder:
    """Build event panels. Never MarketDataClient / provider payloads / raw calendars."""

    def __init__(self, registry: FeatureRegistryService) -> None:
        self.registry = registry

    def build_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
    ) -> dict[str, EventPanel]:
        merged: dict[str, dict[str, Any]] = {
            k.upper(): dict(v) for k, v in (panels or {}).items()
        }
        if snapshots:
            for sym, snap in snapshots.items():
                s = sym.upper()
                meta = merged.setdefault(s, {})
                for fv in snap.values.values():
                    sid = (fv.metadata or {}).get("sector_id")
                    if sid:
                        meta.setdefault("sector_id", str(sid))
                    evs = (fv.metadata or {}).get("events")
                    if isinstance(evs, list) and evs:
                        meta.setdefault("events", evs)

        out: dict[str, EventPanel] = {}
        for sym in sorted(merged.keys()):
            panel = merged[sym]
            raw = panel.get("events")
            stale: list[str] = []
            discovery = "pit_objects"
            if isinstance(raw, list) and raw:
                events = parse_event_objects(sym, raw, as_of=as_of)
            else:
                events = synthesize_calendar(sym, as_of, panel)
                stale.append("events_synthesized")
                discovery = "synthetic_calendar"
            event_meta = _event_meta_from_registry(self.registry, sym, as_of)
            # Overlay registry surprise / guidance when present
            if "EVENT_EPS_SURPRISE" in event_meta:
                for ev in events:
                    if ev.event_type in {"earn_q", "earn_fy", "eps_surprise", "earn_surprise"}:
                        if ev.actual is None and ev.consensus is not None:
                            # Interpret registry value as surprise ratio → reconstruct actual
                            ratio = event_meta["EVENT_EPS_SURPRISE"]
                            ev.actual = round(ev.consensus * (1.0 + ratio), 6)
            if "EVENT_GUIDANCE_DELTA" in event_meta:
                for ev in events:
                    if ev.event_type == "guidance" and ev.guidance_delta is None:
                        ev.guidance_delta = event_meta["EVENT_GUIDANCE_DELTA"]
            out[sym] = EventPanel(
                symbol=sym,
                as_of=as_of,
                sector_id=str(panel["sector_id"]) if panel.get("sector_id") else None,
                events=events,
                event_meta=event_meta,
                stale=stale,
                discovery=discovery,
            )
        return out


def _event_meta_from_registry(
    registry: FeatureRegistryService,
    symbol: str,
    as_of: str,
) -> dict[str, float]:
    out: dict[str, float] = {}
    for fid in REGISTRY_EVENT:
        fv = registry.get(fid, symbol=symbol, as_of=as_of, pit_mode=True)
        if fv is None:
            fv = registry.get(fid, symbol=None, as_of=as_of, pit_mode=True)
        if fv is not None and fv.value is not None:
            try:
                out[fid] = float(fv.value)
            except (TypeError, ValueError):
                continue
    return out
