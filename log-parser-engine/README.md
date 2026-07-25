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

## Proje Özeti ve Mevcut Durum

Bu proje, farklı kaynaklardan gelen logları ortak bir veri modeline dönüştüren,
plugin tabanlı ve genişletilebilir bir log analiz platformudur.

### Mimari Akış

```text
Log girdisi
  → Encoding, binary ve arşiv kontrolleri
  → Parser tespiti
  → Parse ve normalizasyon
  → Canonical LogEvent
  → Batch/streaming orchestration
  → InMemoryEventStore
  → Query ve aggregation API
  → React Web UI
```

Ana katmanlar:

- `ingestion`: encoding, BOM, binary içerik, satır sonu ve arşiv kontrolleri
- `core`, `plugins` ve `parsers`: parser sözleşmesi, otomatik format tespiti,
  parser yönetimi ve plugin keşfi
- `normalization` ve `pipeline`: farklı log tiplerini ortak `LogEvent`
  modeline dönüştürme
- `batch`: streaming işleme, parser session reuse, state yönetimi ve merkezi
  hata politikaları
- `storage`: SQL kullanmadan çalışan in-memory event store, filtreleme,
  pagination, facet, aggregation, retention ve eviction
- `application` ve `api`: uygulama servisi ve FastAPI REST katmanı
- `frontend`: React, TypeScript ve Vite tabanlı analiz ve yönetim arayüzü

### Desteklenen Log Formatları

Mevcut built-in parserlar:

- IIS W3C
- JSON logları
- Redis logları
- Syslog RFC 3164
- Syslog RFC 5424
- Apache/Nginx access logları
- Apache/Nginx error logları
- Windows Event XML

### In-Memory Store Kısıtları

Eventler yalnızca çalışan process belleğinde tutulur:

- Uygulama veya pod yeniden başladığında veriler kaybolur.
- Birden fazla replica çalıştığında her pod kendi bağımsız event store'una
  sahiptir.
- Bu yapı kalıcı audit storage veya merkezi log arşivi değildir.
- Bellek kullanımı `max_events`, retention ve eviction seçenekleriyle
  sınırlandırılmalıdır.

### Güncel Geliştirme Durumu

> Durum notu: 25 Temmuz 2026 tarihinde yapılan yerel kalite kontrolünün
> özetidir. Sonraki değişikliklerden sonra komutlar yeniden çalıştırılmalıdır.

Frontend:

- Vitest smoke testi başarılıdır.
- TypeScript ve Vite production build başarılıdır.
- Üretilen ana JavaScript bundle'ı yaklaşık 779 kB olduğundan ileride route
  bazlı code splitting uygulanması önerilir.

Backend:

- `pytest` test toplama aşaması, bazı plugin modellerinin public model
  paketinden dışa aktarılmaması nedeniyle başarısızdır.
- İlk hata `PluginCandidate` modelinin `log_parser_engine.models` üzerinden
  import edilememesidir.
- `mypy src` kontrolünde 13 dosyada 43 tip hatası bulunmaktadır.
- `ruff check .` kontrolünde format, import, satır uzunluğu ve kullanılmayan
  importlar dahil 281 bulgu bulunmaktadır.

Bu nedenle proje kapsamlı ve modüler bir MVP/prototip seviyesindedir; mevcut
durumuyla bütün production kalite kapılarını henüz geçmemektedir.

### Statistical Analysis Engine Durumu

İstatistiksel analiz katmanı için `AnalysisOptions`, `AnalysisRequest`,
`ComparisonRequest` ve ilgili exception temelleri oluşturulmuştur. Analiz
motoru, accumulatorlar, sonuç modelleri, REST API entegrasyonu ve kapsamlı
testler henüz tamamlanmamıştır.

Planlanan analiz yetenekleri:

- event ve severity özetleri
- hata oranları
- dağılımlar ve zaman serileri
- latency percentile hesapları
- HTTP status, method ve endpoint analizleri
- dönem karşılaştırmaları
- AI kullanmayan deterministik insight üretimi

### Production Öncesi Öncelikler

1. Public plugin model exportlarını düzeltmek ve test koleksiyonunu çalışır
   hale getirmek
2. Bütün backend testlerini başarıyla tamamlamak
3. `mypy` tip hatalarını gidermek
4. Ruff kalite bulgularını temizlemek
5. Dosya upload akışını tek seferde belleğe almak yerine bounded/chunked
   okumaya geçirmek
6. Statistical Analysis Engine'i tamamlayıp API ve UI katmanlarına entegre
   etmek
7. Frontend bundle'ı route-level code splitting ile küçültmek

Production adayı bir sürüm oluşturulmadan önce aşağıdaki kontrollerin tamamı
başarılı olmalıdır:

```bash
poetry run pytest
poetry run pytest --cov=log_parser_engine
poetry run ruff check .
poetry run mypy src

cd frontend
npm test
npm run lint
npm run build
```
