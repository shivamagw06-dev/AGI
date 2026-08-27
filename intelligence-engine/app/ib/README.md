# AGI Intelligence Bus (IB) v1.0

Event-driven communication backbone for the AGI platform.

IB is **not** an intelligence engine. It transports canonical internal events so subsystems can react without direct coupling.

## Position

```text
AOI / EVE / IIE / FLE / MEE / CAE
              │
              ▼
     AGI Intelligence Bus (IB)
              │
     soft subscribers + future PMO/IME/RME/AMS
```

Architecture **v1.0.1 LOCKED**. Fully additive — engines keep working when `IB=false`.

## Responsibilities

Publish · route · subscribe · deliver · retry · DLQ · replay · persist · metrics · traces · cache invalidation

IB never stores business knowledge and never performs business logic.

## APIs

`/v1/ib/health` · `/dashboard` · `/events` · `/publish` · `/subscriptions` · `/replay` · `/history` · `/metrics` · `/traces` · `/dead-letter` · `/schema`

Admin: `/admin/intelligence-bus`

## Out of scope (v2/v3)

Distributed streaming, cross-region replication, AI-generated subscriptions, predictive routing — not implemented in v1.
