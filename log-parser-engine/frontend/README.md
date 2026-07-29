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

- `/analysis`: text and file parse workflows
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
- Analysis and comparison API clients exist, while their dedicated result
  screens remain a later UI milestone.
