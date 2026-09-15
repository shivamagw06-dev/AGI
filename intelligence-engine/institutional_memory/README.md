# Institutional Learning & Memory Engine (ILM) V1

Active institutional learning — not passive storage. Soft intelligence layer.

## Primary question

**What has AGIB learned over time?**

## Includes

Mistake Intelligence Engine (MIE) — classify why AGIB was wrong.

## Flag

`INSTITUTIONAL_MEMORY=true`

## Rules

- No thesis overwritten
- Every forecast versioned
- Every committee decision preserved
- Accuracy continuously updated
- Lessons generated after outcomes
- Historical evidence retained
- Confidence evolution recorded

## API

- `GET /v1/ilm/company/{ticker}`
- `GET /v1/ilm/thesis/{ticker}`
- `GET /v1/ilm/committee/{ticker}`
- `GET /v1/ilm/forecast/{ticker}`
- `GET /v1/ilm/portfolio/{portfolio}`
- `POST /v1/ilm/learning/update`
- `GET /admin/institutional-memory`
