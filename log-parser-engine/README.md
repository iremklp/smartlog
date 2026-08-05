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
- Request ID header is returned as `X-Request-ID`. Incoming client request IDs
  are ignored by default; trusted mode accepts only bounded, safe identifiers.
- Dev CORS defaults to `http://localhost:5173` and `http://127.0.0.1:5173`
- Override CORS with:
  `LOG_PARSER_CORS_ORIGINS=https://my-ui.example.com,http://localhost:4173`.
  Origins must be explicit HTTP(S) origins; wildcard, credential-bearing and
  path-bearing values are rejected.
- `POST /parse/file` reads uploads in 64 KiB chunks, enforces a configurable
  byte limit before ingestion and always closes the upload stream. The default
  limit is 50 MiB (`ApplicationOptions.max_upload_bytes`).
- Oversized uploads return `413`; empty or invalid ingestion input returns a
  safe `400` response without reflecting the uploaded content.
- API responses include `Cache-Control: no-store`,
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and
  `Referrer-Policy: no-referrer`.
- Enum values in JSON responses use lowercase/snake_case. Legacy uppercase and
  case-insensitive enum inputs remain accepted.

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
- `POST /api/v1/analysis`
- `POST /api/v1/analysis/compare`
- `GET /events/{event_id}`
- `DELETE /events/{event_id}`

## Running tests

```bash
poetry run pytest
```

Coverage:

```bash
poetry run pytest --cov
```

## Web UI (frontend)

UI source lives in [frontend](frontend).

```bash
cd frontend
npm ci
npm run dev
```

Environment:

- Copy `.env.example` to `.env`
- Set `VITE_API_BASE_URL=http://localhost:8000`

Frontend quality gates:

```bash
npm run typecheck
npm run lint
npm run test
npm run check
npm run build
```

## Linting

```bash
poetry run ruff check .
```

## Type checking

```bash
poetry run mypy
```

## Backend Quality Gate

```bash
poetry install
poetry run pytest
poetry run pytest --cov
poetry run ruff check
poetry run mypy
poetry build
```

## Plugin startup and discovery

External parser discovery is disabled by default. The application always
registers the eight built-in parsers first and runs the optional plugin startup
lifecycle once, before `ParserManager`, the pipeline and the batch orchestrator
are created.

Trusted package plugins must be explicitly allowlisted and should expose a
non-empty `__plugin_modules__` manifest:

```python
from log_parser_engine.application import ApplicationOptions
from log_parser_engine.plugins import PluginStartupOptions

options = ApplicationOptions(
    plugin_startup_options=PluginStartupOptions(
        package_names=("company_log_parsers",),
        failure_policy="fail",
        duplicate_policy="reject",
    )
)
```

Entry-point discovery is also opt-in and requires an explicit name allowlist.
Package candidates are confined to the configured package namespace, and
fallback class discovery accepts only concrete `BaseParser` subclasses.
Unrelated classes are never instantiated as parser candidates.

Startup policies:

- `failure_policy="fail"` validates and stages all plugins before changing the
  real registry; any failure aborts startup without partial registration.
- `failure_policy="warn"` registers healthy plugins, reports bounded and
  sanitized startup warnings, and exposes degraded application health.
- `duplicate_policy="reject"` preserves the existing parser.
- `duplicate_policy="replace"` preserves registration order, but replacing a
  built-in parser additionally requires `allow_builtin_replacement=True`.
- Candidate and warning counts are bounded.

Application package loading requires the manifest by default. Direct loader
APIs retain their backward-compatible behavior for library users. Injected
loaders are intended for controlled composition and tests and require
`allow_injected_loaders=True`.

Plugins are trusted Python code and are not sandboxed. Do not derive package or
entry-point configuration from uploads, request metadata or other
user-controlled input. There is no runtime hot reload, remote plugin download,
filesystem-directory scanning or plugin unload lifecycle.

Parser implementation modules remain separate from plugin entry modules.
Webserver plugins are exposed only through `*_plugin.py` entry modules, and
helper modules must not export `Parser` or `create_parser`.

## Canonical LogEvent updates

Parser enrichment after normalization must use
`LogEvent.with_validated_updates(...)`. This method reconstructs the event
through Pydantic validation, preserves `event_id` and `ingested_at`, and
recursively freezes `attributes` and `tags` again.

Do not use `model_copy(update=...)` to enrich canonical events. Pydantic
intentionally skips validation for those updates, which can leak mutable
collections into an otherwise frozen `LogEvent`. All eight built-in parsers
are covered by fixture-based root, nested and tag immutability regression
tests.

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

- Single write işlemleri typed duplicate, collision, capacity ve oversized
  event hatalarını korur.
- `add_many(..., atomic=True)` gerçek all-or-nothing rollback uygular;
  başarısız batch event, index, sayaç veya sequence değişikliği bırakmaz.
- Duplicate kararı capacity eviction'dan önce verilir; ignore edilen duplicate
  dolu store'dan geçerli event çıkarmaz.
- Replace işlemi mevcut store ID'sini ve monoton sequence değerini korur.
- Query işlemleri lock altında alınan event ve index snapshotı üzerinde çalışır.
- Uygulama veya pod yeniden başladığında veriler kaybolur.
- Birden fazla replica çalıştığında her pod kendi bağımsız event store'una
  sahiptir.
- Bu yapı kalıcı audit storage veya merkezi log arşivi değildir.
- Bellek kullanımı `max_events`, retention ve eviction seçenekleriyle
  sınırlandırılmalıdır.

### Güncel Geliştirme Durumu

> Durum notu: 3 Ağustos 2026 tarihinde yapılan yerel kalite kontrolünün
> özetidir. Sonraki değişikliklerden sonra komutlar yeniden çalıştırılmalıdır.

Frontend:

- TypeScript, ESLint 9, Prettier ve Vite production build kontrolleri
  başarılıdır.
- On iki test dosyasında **52 Vitest testi** geçmektedir; API URL/body ve
  structured error sözleşmeleri, analiz/comparison tipleri, request-state,
  bounded presentation, erişilebilir analiz görünümü, pagination ve backend
  biçimli event tablosu fixture'ı kapsanır.
- `node_modules`, Vite cache ve TypeScript build info dosyaları Git tarafından
  izlenmez; kurulum `package-lock.json` üzerinden `npm ci` ile tekrarlanır.
- Üretilen ana JavaScript bundle'ı yaklaşık 840 kB olduğundan route bazlı code
  splitting halen önerilir.

Backend:

- Tam backend paketi başarılıdır: **549 test geçti**.
- Tam paket coverage sonucu **%86**'dır. Yalnız istatistiksel analiz modülünün
  odak testleri 139/139 geçmiş ve modül coverage değeri %92 olmuştur.
- Domain/pipeline/plugin/API contract odak seçkisi 39/39 geçmiştir.
- Redis parser testleri 7/7, deep-immutability dahil built-in
  parser/pipeline/orchestration seçkisi 126/126 geçmiştir.
- In-memory query, aggregation ve storage contract testleri başarılıdır.
- Query/aggregation source kapsamı Ruff ve mypy kontrollerinden geçmektedir.
- `mypy src` kontrolü 217 source dosyasının tamamında başarılıdır.
- `ruff check .` kontrolü repository genelinde başarılıdır.

Bu nedenle proje kapsamlı ve modüler bir MVP/prototip seviyesindedir; mevcut
durumuyla bütün production kalite kapılarını henüz geçmemektedir.

### Statistical Analysis Engine Durumu

İstatistiksel analiz katmanı tamamlanmış ve application service ile REST API'ye
bağlanmıştır. Motor yalnız kendisine verilen `StoredEvent` snapshotı üzerinde
çalışır; event store'u değiştirmez, SQL veya harici bir veri tabanı kullanmaz ve
AI/LLM çağrısı yapmaz. Üretilen insight'lar eşiklere ve açık metriklere dayanan
deterministik gözlemlerdir; kök neden iddiası değildir.

Desteklenen analizler:

- toplam event, severity, hata ve kritik oranı özetleri
- event type, parser, servis, host, tag ve HTTP boyutlarında bounded dağılımlar
- UTC ve Unix epoch hizalı zaman serileri
- exact veya açıkça işaretlenmiş deterministik örneklemeli percentile analizi
- latency min/max/ortalama/median/population standard deviation ve histogram
- HTTP status sınıfı, method, endpoint, 4xx/5xx ve endpoint latency analizi
- baseline/comparison dönem karşılaştırmaları
- minimum örnek ve anlamlı değişim eşiklerine bağlı temkinli insight'lar
- raw log içermeyen, sınırlı ve sanitize edilmiş event örnekleri

Canonical API uçları:

```text
POST /api/v1/analysis
POST /api/v1/analysis/compare
```

Analiz isteği filtre, zaman aralığı, bucket boyutu, top-N, grup alanları,
percentile'lar ve dahil edilecek modülleri seçebilir. Başlangıç zamanı inclusive,
bitiş zamanı exclusive'dir. HTTP hata oranı yalnız 4xx ve 5xx sonuçlarını hata
olarak değerlendirir; genel `error_rate` ise severity `ERROR` ve `CRITICAL`
kayıtlarını kullanır. Percentile metodu varsayılan olarak `nearest_rank`tır.
Örnekleme etkinleştirilirse median dahil order-statistic/percentile sonuçları
yaklaşık olur; count, min/max, mean ve population standard deviation tam veri
kümesinden hesaplanır. Sonuç bu durumu `percentiles_approximated` ve
`percentile_sample_count` alanlarıyla açıkça bildirir.

Python kullanımı:

```python
from log_parser_engine.analysis import StatisticalAnalysisEngine
from log_parser_engine.models import AnalysisRequest

snapshot = store.snapshot_events()
result = StatisticalAnalysisEngine().analyze(
    snapshot,
    AnalysisRequest(
        time_bucket_seconds=300,
        group_fields=("severity", "service", "event_type"),
        percentiles=(50, 95, 99),
        top_n=10,
    ),
)
```

API örneği:

```bash
curl -X POST http://localhost:8000/api/v1/analysis \
  -H 'Content-Type: application/json' \
  -d '{
    "time_bucket_seconds": 300,
    "group_fields": ["severity", "service"],
    "percentiles": [50, 95, 99],
    "include_samples": false
  }'
```

Güvenlik ve kaynak sınırları:

- event, grup, timeline bucket, percentile sample, top-N ve response alanları
  yapılandırılabilir limitlere tabidir
- timeline bucket süresi ve uç datetime aritmetiği taşma üretmeyecek biçimde
  sınırlandırılmıştır
- API istek gövdesi byte limiti ve non-blocking eşzamanlı analiz slotu sınırı
  uygular; kapasite dolduğunda izlenebilir `413` veya `429` cevabı döner
- `message`, `raw_message`, kimlik, credential, token ve authorization alanları
  gruplama veya HTTP alan override'ı olarak kullanılamaz
- public API yalnız bilinen analiz boyutlarını kabul eder; özel attribute
  grupları ancak server tarafında güvenilir iç kullanımda değerlendirilebilir
- attribute yollarında object attribute erişimi, dunder segmentleri, regex,
  `eval` ve çalıştırılabilir expression desteklenmez
- sonuç modellerindeki metadata/evidence/attributes koleksiyonları iç içe
  yapılarda da immutable'dır
- API cevapları request metadata'sını, full filter metinlerini veya raw logu
  geri yansıtmaz

Analiz sonuçları kalıcı değildir. `InMemoryEventStore` process/pod belleğinde
yaşar; uygulama veya pod yeniden başladığında silinir ve OpenShift'te farklı
replica'lar arasında paylaşılmaz. Analiz endpointleri yalnız istek anında ilgili
podda bulunan snapshotı görür.

Frontend'deki `/analytics` çalışma alanı `/api/v1/analysis` sözleşmesini
doğrudan tüketir. Özet metrikler, en fazla 120 görsel noktaya indirgenen timeline
ve boyut başına en fazla 20 satırlık dağılımlar sunulur. Grafiklerin eşdeğer
semantik tabloları vardır; empty, warning, `413` ve `429` durumları güvenli ve
izlenebilir şekilde gösterilir. Timeline aralığı varsayılan olarak backend'in
bounded otomatik seçimine bırakılır; elle seçilen bucketlar UTC hizalıdır.

`/analytics/compare` çalışma alanı aynı process-local `InMemoryEventStore`
snapshotından iki zorunlu zaman aralığını karşılaştırır. Her aralık yarı-açıktır:
başlangıç dahildir, bitiş dahil değildir (`start <= timestamp < end`). Bu ekran
ayrı veri tabanlarını, podları veya kalıcı datasetleri karşılaştırmaz. `Son 1
saat / önceki 1 saat`, `son 24 saat / önceki 24 saat` ve `son 7 gün / önceki 7
gün` presetleri eşit uzunluklu ve bitişik dönemler üretir; manuel kullanımda da
dört dönem sınırının tamamı zorunludur.

Karşılaştırma metrikleri event sayısı, hata ve kritik oranları, HTTP 4xx/5xx
oranları, ortalama/P50/P95/P99 süreleri ve throughput'tur. En fazla dört grup
boyutu istenebilir ve her boyutun sonucu en fazla 20 satırla gösterilir. Ratio
değerleri yüzde, iki ratio arasındaki mutlak fark yüzde puan, `percent_change`
ise backend'in ürettiği göreli yüzde değişim olarak sunulur; bu ölçüler birbirine
dönüştürülmez. `significant` işareti yalnız yapılandırılmış göreli değişim
eşiğinin aşıldığını bildirir, istatistiksel anlamlılık testi değildir. Düşük
örnek sayısı ayrıca uyarılır ve kesin iyileşme/kötüleşme iddiası kurulmaz.

Karşılaştırma ilk sayfa açılışında otomatik istek göndermez. Kullanıcı
gönderdikten sonra loading, partial/empty, structured error ve aynı istekle
retry durumları görünürdür. İki dönem de boşsa açık empty state gösterilir;
yalnız bir dönem boşsa yeni veya kaybolan gruplar yine listelenir. Sonuçlar
geçicidir: ilgili podun belleğindeki snapshota aittir, restartta kaybolur ve
OpenShift replica'ları arasında paylaşılmaz.

### Production Öncesi Öncelikler

1. Latency, HTTP ve deterministic insight analiz modüllerini görünür kılmak
2. Dashboard filtrelerini analysis/comparison drill-down akışına bağlamak
3. Frontend bundle'ı route-level code splitting ile küçültmek
4. Merkezi doğrulanmış configuration ve redacted structured logging
   sözleşmesini tamamlamak

Production adayı bir sürüm oluşturulmadan önce aşağıdaki kontrollerin tamamı
başarılı olmalıdır:

```bash
poetry run pytest
poetry run pytest --cov=log_parser_engine
poetry run ruff check .
poetry run mypy src

cd frontend
npm run check
npm run build
```
