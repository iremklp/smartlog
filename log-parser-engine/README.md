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

- Tam test paketi toplanıp çalışmaktadır; son kontrolde 389 test geçmiş,
  analiz katmanı dışındaki eski test/fixture uyumsuzlukları nedeniyle 21 test
  başarısız olmuş ve 11 test setup hatası vermiştir.
- Tam paket coverage sonucu %84'tür. Yalnız istatistiksel analiz modülünün
  odak testleri 129/129 geçmiş ve modül coverage değeri %93 olmuştur.
- `mypy src` kontrolünde 5 eski dosyada toplam 20 tip hatası bulunmaktadır.
- `ruff check .` kontrolünde satır uzunluğu, import sırası, kullanılmayan import
  ve tanımsız isimler dahil 231 bulgu bulunmaktadır.

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
- `message`, `raw_message`, kimlik, credential, token ve authorization alanları
  gruplama veya HTTP alan override'ı olarak kullanılamaz
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

### Production Öncesi Öncelikler

1. Analiz dışındaki eski backend test uyumsuzluklarını gidermek
2. Proje genelindeki kalan `mypy` tip hatalarını gidermek
3. Proje genelindeki Ruff kalite bulgularını temizlemek
4. Dosya upload akışını tek seferde belleğe almak yerine bounded/chunked
   okumaya geçirmek
5. Frontend'i `/api/v1/analysis` sözleşmesine bağlamak
6. Frontend bundle'ı route-level code splitting ile küçültmek

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
