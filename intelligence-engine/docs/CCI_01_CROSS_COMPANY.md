# CCI-01 — engine notes

Package: `institutional_cross_company`.

## Soft dependencies

- **KG-01** (`institutional_graph.production.get_company_graph`) — read-only bridge
- Peer Intelligence — optional competitor enrichment
- PKG-01 — portfolio co-holding relationships

CCI never writes to KG-01 caches or mutates graph nodes/edges.

## Façades

- `get_company_relationships` / `get_sector_relationships` / `get_macro_relationships`
- `query_relationships` / `get_similarity` / `get_clusters` / `get_propagation`
- `soft_slice_mission_control` → Relationship Center

## Extending relationship types

```python
from institutional_cross_company import register_relationship_provider

register_relationship_provider(
    "esg_link",
    provider="esg_dependency_engine",
    category="business",
    discover=my_discover_fn,
)
```

## Tests

`tests/test_cci_01_cross_company.py`
