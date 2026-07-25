# log-parser-engine

This project provides a production-oriented plugin-based log parser engine with:

- application service layer
- FastAPI REST API
- in-memory event store with query/facet/aggregation support
- optional React Web UI in [frontend](frontend)

## Purpose

The long-term goal is to build a flexible log analysis platform that can parse logs through extensible plugins and support future integrations such as APIs, queues, multiprocessing, and AI features.

## Installation

1. Make sure Python 3.11 is installed.
2. Install Poetry if it is not already available.
3. Run the following commands from the project root:

```bash
poetry install
```

## Run API

```bash
poetry run uvicorn log_parser_engine.api.main:app --reload --port 8000
```

### API Notes

- Default base URL: `http://localhost:8000`
- Request ID header is returned as `X-Request-ID`
- Dev CORS defaults to `http://localhost:5173` and `http://127.0.0.1:5173`
- Override CORS with: `LOG_PARSER_CORS_ORIGINS=http://my-ui.example.com,http://localhost:4173`

### Main Endpoints

- `GET /health`
- `GET /runtime/statistics`
- `GET /store/statistics`
- `GET /parsers`
- `POST /parse`
- `POST /parse/{parser_name}`
- `POST /parse/file` (multipart)
- `POST /parse/store`
- `POST /batch/parse`
- `POST /batch/parse/store`
- `POST /query`
- `POST /aggregate`
- `GET /events/{event_id}`
- `DELETE /events/{event_id}`

## Running tests

```bash
poetry run pytest
```

## Web UI (frontend)

UI source lives in [frontend](frontend).

```bash
cd frontend
npm install
npm run dev
```

Environment:

- Copy `.env.example` to `.env`
- Set `VITE_API_BASE_URL=http://localhost:8000`

## Linting

```bash
poetry run ruff check .
```

## Type checking

```bash
poetry run mypy src
```

## Plugin discovery notes

Parser implementation modules are separate from plugin entry modules. Webserver plugins are exposed only through `*_plugin.py` entry modules, and helper modules must not export `Parser` or `create_parser`.

## Batch and Streaming Parse

The batch layer adds orchestration around existing single-record parsers without changing parser contracts.

- Single-event parser interface is preserved.
- `BatchParseOrchestrator` coordinates record iteration, parser detection/selection reuse, parser session state, and centralized error policy decisions.
- `iter_parse_*` APIs are streaming and iterator-based; natural backpressure is provided by synchronous pull consumption.
- `parse_*` APIs are collector wrappers that aggregate events/failures with configurable collection limits.

### Core APIs

```python
from log_parser_engine.batch import BatchParseOptions, BatchParseOrchestrator

result = orchestrator.parse_lines(lines, options=BatchParseOptions())

stream = orchestrator.iter_parse_lines(lines, options=BatchParseOptions())
for item in stream:
	...
stats = stream.statistics
```

### Detection and Sessions

- Default mode is detect-once with bounded detection sample buffering.
- Explicit parser selection is supported via `BatchParseOptions(parser_name="...")`.
- Parser sessions reuse the selected parser path and keep per-session counters.
- Optional redetection on failure can switch parser sessions when mixed formats are allowed.

### Record Modes

- `line`: one logical record per line.
- `multiline_document`: entire source as one logical record.
- `auto`: strategy-based fallback; unknown multiline parsers require explicit mode.

Windows Event XML is intended for document mode. JSON Lines is line mode. Pretty JSON documents should use explicit `multiline_document`.

### Stateful IIS Header Handling

- IIS directives (`#Fields`, `#Software`, `#Version`, `#Date`) are handled as header/comment records.
- Header lines update parser session state.
- Data records receive effective IIS state through context attributes.

### Error Policies and Safety

Supported stop policies include:

- stop on first error
- total error limit
- consecutive error limit
- error rate threshold (after minimum attempted records)

Safety controls include:

- max characters per record
- oversized record failure without exposing full raw payload
- sanitized previews for oversized lines
- no raw payload in progress callbacks

### Progress and Statistics

- Optional progress callback receives `BatchProgress` snapshots at configurable record intervals.
- Batch statistics report records seen/attempted/succeeded/failed/skipped, detection counts, parser switches, error counts, status counts, durations, and min/max event timestamps.
- Session history is available as immutable `ParserSessionInfo` entries.

### Path Streaming Scope

- `iter_parse_path` supports plain text files only.
- `.gz` and `.zip` are rejected for streaming path mode.
- For archives and encoding-aware ingestion workflows, use ingestion first, then parse the produced text.

### Out of Scope

The batch layer intentionally does not implement:

- async I/O
- multiprocessing/thread pools
- tailing/log rotation watchers
- directory recursion and parallel multi-file orchestration
- multiline stack-trace grouping
- XML `<Events>` container batch parsing
- JSON array batch parsing
