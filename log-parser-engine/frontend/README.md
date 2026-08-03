# SmartLog Web UI

Production-oriented Log Analysis UI for `log-parser-engine`.

## Stack

- React + TypeScript + Vite
- TanStack Query + TanStack Table
- React Router
- React Hook Form + Zod
- Recharts
- Tailwind CSS
- Vitest + Testing Library

## Setup

```bash
npm ci
cp .env.example .env
npm run dev
```

Default API target is `http://localhost:8000` via `VITE_API_BASE_URL`.

## Routes

- `/analysis`: text/file ingest, parse and optional store workflows
- `/analytics`: statistical summary, bounded timeline and diagnostic distributions
- `/analytics/compare`: adjacent-period metric and group comparison workspace
- `/events`: server-side query and event list
- `/events/:eventId`: event detail
- `/dashboard`: aggregation/facet charts
- `/parsers`: parser registry view
- `/store`: store statistics and retention counters
- `/system`: health and runtime telemetry

## API Contract

UI is designed around these backend endpoints:

- `GET /health`
- `GET /runtime/statistics`
- `GET /store/statistics`
- `GET /parsers`
- `POST /parse`
- `POST /parse/{parser_name}`
- `POST /parse/file`
- `POST /parse/store`
- `POST /batch/parse`
- `POST /batch/parse/store`
- `POST /query`
- `POST /aggregate`
- `POST /api/v1/analysis`
- `POST /api/v1/analysis/compare`
- `GET /events/{event_id}`
- `DELETE /events/{event_id}`

## Quality gates

```bash
npm run check
npm run build
```

`npm run check`; TypeScript, ESLint 9, Vitest ve Prettier kontrollerini
birlikte çalıştırır. Dependency klasörü ve Vite/TypeScript cache çıktıları
Git'e eklenmez; tekrarlanabilir kurulum için `package-lock.json` korunur.

## Notes

- Backend parser/store logic stays in Python layers. UI does not duplicate parser algorithms.
- Current store is memory-backed; data resets on API restart.
- Event pagination, parser metadata and canonical event fields are derived from
  the backend wire contract; UI does not invent response fields.
- Statistical analysis and comparison requests use backend-aligned literal
  unions and concrete response contracts. Unknown `JsonObject` casts are not
  required for summary, timeline, distribution, latency, HTTP or comparison
  results.
- `/analytics` automatically analyzes the current process-local snapshot, then
  supports timezone-aware range selection, backend-bounded automatic bucket
  sizing, optional explicit UTC buckets, bounded Top-N dimensions and retry-safe
  refresh.
- `/analytics/compare` compares two required, timezone-aware, half-open periods
  (`start <= timestamp < end`) from the same process-local
  `InMemoryEventStore` snapshot. It does not compare separate stores, pods or
  persisted datasets.
- The comparison form offers equal, adjacent `1 hour`, `24 hour` and `7 day`
  presets. Manual input still requires all four period boundaries; an empty
  filter is not submitted as an implicit whole-store comparison.
- Supported metrics are event count, error/critical/HTTP 4xx/HTTP 5xx rates,
  average/P50/P95/P99 duration and throughput. A request accepts at most four
  group dimensions, and group result tables render at most 20 rows per
  dimension.
- Ratio values are rendered as percentages, the difference between two ratios
  as percentage points, and `percent_change` as the backend-provided relative
  percentage. These three quantities are not interchangeable.
- A `significant` flag means only that the configured relative-change threshold
  was reached; it is not a statistical significance test. Low-sample warnings
  are shown explicitly and suppress overconfident interpretation.
- The comparison route does not run automatically on first render. It provides
  explicit initial, loading, partial/empty, structured error and same-request
  retry states; new and disappeared groups remain visible when only one period
  is empty.
- Timeline rendering is bounded to 120 visual points. Larger responses are
  merged deterministically without combining percentile values. Distribution
  rendering is bounded to 20 rows per dimension.
- Recharts visualizations have equivalent semantic tables, and loading, empty,
  warning and structured API error states remain usable without the charts.
- Comparison request state, form and result presentation are typed against the
  backend contract. As with every analysis view, results are temporary and
  pod-local: restarting the API loses events, and replicas do not share them.
