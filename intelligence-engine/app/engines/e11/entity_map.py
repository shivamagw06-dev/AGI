"""E11-001 Entity resolution table — deterministic symbol/entity map (P0 subset)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityRecord:
    entity_id: str
    symbol: str
    name: str | None
    aliases: tuple[str, ...]
    sector_id: str | None
    confidence: float


class EntityMap:
    """In-memory PIT entity resolution. No provider APIs / MarketDataClient."""

    def __init__(self) -> None:
        self._by_symbol: dict[str, EntityRecord] = {}
        self._by_alias: dict[str, str] = {}

    def upsert(
        self,
        *,
        symbol: str,
        name: str | None = None,
        aliases: list[str] | None = None,
        sector_id: str | None = None,
        confidence: float = 1.0,
    ) -> EntityRecord:
        sym = symbol.upper().strip()
        eid = f"ENT:{sym}"
        alias_t = tuple(sorted({a.upper().strip() for a in (aliases or []) if a}))
        rec = EntityRecord(
            entity_id=eid,
            symbol=sym,
            name=name,
            aliases=alias_t,
            sector_id=sector_id,
            confidence=max(0.0, min(1.0, float(confidence))),
        )
        self._by_symbol[sym] = rec
        self._by_alias[sym] = eid
        for a in alias_t:
            self._by_alias[a] = eid
        return rec

    def resolve(self, token: str) -> EntityRecord | None:
        key = token.upper().strip()
        if key in self._by_symbol:
            return self._by_symbol[key]
        eid = self._by_alias.get(key)
        if eid is None:
            return None
        # eid format ENT:SYM
        sym = eid.split(":", 1)[-1]
        return self._by_symbol.get(sym)

    def ensure(self, symbol: str, *, sector_id: str | None = None, name: str | None = None) -> EntityRecord:
        existing = self.resolve(symbol)
        if existing is not None:
            if sector_id and not existing.sector_id:
                return self.upsert(
                    symbol=existing.symbol,
                    name=existing.name or name,
                    aliases=list(existing.aliases),
                    sector_id=sector_id,
                    confidence=existing.confidence,
                )
            return existing
        return self.upsert(symbol=symbol, name=name, sector_id=sector_id, confidence=0.9)

    def from_panel(self, symbol: str, panel: dict[str, Any]) -> EntityRecord:
        aliases = panel.get("aliases") or panel.get("entity_aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        return self.upsert(
            symbol=symbol,
            name=panel.get("name") or panel.get("company_name"),
            aliases=list(aliases) if isinstance(aliases, list) else [],
            sector_id=str(panel["sector_id"]) if panel.get("sector_id") else None,
            confidence=float(panel.get("entity_confidence") or 0.9),
        )

    def stats(self) -> dict[str, int]:
        return {"entities": len(self._by_symbol), "aliases": len(self._by_alias)}
