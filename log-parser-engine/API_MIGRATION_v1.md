# API v1 Migration Notes

Sprint 5 introduces a consistent versioned API surface under /api/v1 and keeps
legacy unversioned routes available as deprecated aliases.

## Strategy

- Versioned routes under /api/v1 are the primary contract.
- Legacy unversioned routes are still operational and marked deprecated in OpenAPI.
- No legacy route was silently removed.

## Route Mapping

- GET /health -> GET /api/v1/health
- GET /runtime/statistics -> GET /api/v1/runtime/statistics
- GET /store/statistics -> GET /api/v1/store/statistics
- GET /parsers -> GET /api/v1/parsers
- POST /ingest/text -> POST /api/v1/ingest/text
- POST /parse -> POST /api/v1/parse
- POST /parse/file -> POST /api/v1/parse/file
- POST /parse/store -> POST /api/v1/parse/store
- POST /parse/{parser_name} -> POST /api/v1/parse/{parser_name}
- POST /batch/parse -> POST /api/v1/batch/parse
- POST /batch/parse/store -> POST /api/v1/batch/parse/store
- POST /events -> POST /api/v1/events
- POST /events/batch -> POST /api/v1/events/batch
- GET /events/{event_id} -> GET /api/v1/events/{event_id}
- DELETE /events/{event_id} -> DELETE /api/v1/events/{event_id}
- POST /query -> POST /api/v1/query
- POST /aggregate -> POST /api/v1/aggregate
- POST /analysis -> POST /api/v1/analysis
- POST /analysis/compare -> POST /api/v1/analysis/compare

## Response Model Policy

The API no longer returns domain models directly for key endpoints. Explicit API
response models are used for parser list, parse outputs, event query/list, event
detail, aggregation and store statistics.

## Safety Rules

- Event list responses are compact and do not include raw_message.
- Event detail responses include raw_message.
- Internal storage fields such as content_hash, estimated_size_bytes, metadata
  are not exposed in compact/detail API event wrappers.
