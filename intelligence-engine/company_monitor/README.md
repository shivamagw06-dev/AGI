# Company Monitoring System (CMS) V1

**Architecture status:** v1.0.1 LOCKED  
**Role:** Continuous living-analyst layer for tracked companies.  
**Not:** engine redesign · provider redesign · recommendation changes · CID redesign · auto house-view mutation

## Soft pipeline

LEO → CID → Financial Intelligence → Company Analysis → House View **hint** → Prediction stamp → Knowledge Timeline → Ask AGI

## Flags

`COMPANY_MONITOR`, `CMS_AUTO_PIPELINE`, `CMS_ASK_AGI`, `CMS_RESEARCH_WRITER`, `CMS_HOUSE_VIEW_HINTS`

## Admin

`/admin/company-monitor`

## APIs

- `GET /v1/company-monitor/health`
- `GET /v1/company-monitor/dashboard`
- `GET /v1/company-monitor/quality-gates`
- `POST /v1/company-monitor/run`
- `POST /v1/company-monitor/run-universe`
- `GET /v1/company-monitor/changes`
- `GET /v1/company-monitor/alerts`
