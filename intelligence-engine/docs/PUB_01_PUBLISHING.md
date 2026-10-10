# PUB-01 — engine notes

Package: `institutional_publishing`.

## Compose-only retrieval

`sources.py` soft-reads domain engines (decision, risk, policy, portfolio decision, committee). Missing sources are referenced as unavailable — never invented as recommendations.

## Manifest vs artifact

| Object | Role |
|--------|------|
| `PublicationManifest` | Authoritative audit / reproducibility record |
| Rendered HTML/PDF/MD/JSON | Presentation artifact |

## Façades

- `generate` / `get_publication` / `list_publications` / `export_publication`
- `list_types` / `soft_slice_mission_control`

## Tests

`tests/test_pub_01_publishing.py`
