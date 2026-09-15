# RQ1 Research Ontology (Sprint 1)

Constitution-first research typing for AGIB.

**Not** a top-level intelligence layer. Soft-wire supporting ontology only.

## Law

> What type of research is this?

Classify **before** any analyst or intelligence layer executes.

## Sprint 1 surfaces

| Surface | Path |
|---|---|
| Health | `GET /v1/research-ontology/health` |
| Constitution | `GET /v1/research-ontology/constitution` |
| Classify | `POST /v1/research-ontology/classify` |
| Dashboard | `GET /v1/research-ontology/dashboard` |
| Quality gates | `GET /v1/research-ontology/quality-gates` |
| Admin | `/admin/intent-intelligence` |

## Outputs

Primary intent · secondary intents · entity · entity type · objective · confidence · clarification · next stage  
`executed_layers` and `executed_analysts` are always `[]` in Sprint 1.
