# Parsel Engine Geliştirme Durumu

Son kalite kontrolü: 25 Temmuz 2026  
Branch: `main`  
Referans commit: `64d604c`  
Remote durumu: keşif başlangıcında `main`, `origin/main` ile aynıydı.

Bu dosya doğrulanmış repository durumunu kaydeder. “Production-oriented”
tasarım hedefini production-readiness onayı olarak kullanmaz.

## Son tamamlanan iş

Son tamamlanan ürün dilimi Statistical Analysis Engine ile application/API
entegrasyonudur. Sonraki hardening commit'i analysis request gövdesi limitini
`Content-Length` olmayan chunked body'lerde de tutarlı `413` davranışına
getirmiştir.

Odak analiz kapsamı:

- summary ve dağılımlar,
- timeline,
- percentile ve latency,
- HTTP breakdown,
- baseline/comparison,
- deterministik insight,
- bounded request/response,
- güvenli public group alanları,
- eşzamanlı analysis slot limiti.

Odak test sonucu: **139 passed**.

## Repository snapshotı

| Alan | Değer |
|---|---|
| Backend paket | `log-parser-engine` `0.1.0` |
| Python | `3.11.15` |
| Poetry | `2.4.1` |
| Backend kaynak dosyası | 214 Python dosyası |
| Backend test modülü | 84 |
| Frontend paket | `log-parser-engine-ui` `0.1.0` |
| Node.js | `24.18.0` |
| npm | `11.16.0` |
| Frontend stack | React 18, TypeScript, Vite, TanStack Query/Table, Recharts |
| Storage | Yalnız `InMemoryEventStore` |
| SQL/harici DB | Yok |
| Ayrı CI/deployment | Yok |

Keşif başlangıcında çalışma ağacı temizdi. Bu keşif turu yalnız
`PROJECT_ROADMAP.md`, `ARCHITECTURE.md` ve bu dosyayı ekler; commit veya push
yapmaz.

## Tamamlanmış veya odak kapsamında doğrulanmış bileşenler

- BaseParser, ParserContext, metadata, registry, manager ve detection scoring.
- IIS W3C, JSON/JSON Lines, Apache/Nginx access/error, Windows Event XML,
  RFC3164 ve RFC5424 parser implementasyonları.
- Text/byte/path ingestion, encoding, BOM, binary, line ending, gzip/zip ve
  archive güvenliği.
- Canonical normalization.
- Batch record reader, parser session, stateful IIS header ve error policy
  akışları.
- FastAPI application factory ve temel parse/store/query endpointleri.
- Statistical Analysis Engine ve `/api/v1/analysis*` endpointleri.
- React/Vite uygulama iskeleti ve parse, event, dashboard, parser, store,
  system sayfaları.

“Tamamlanmış” burada yalnız ilgili subsystem implementasyonunun mevcut olduğunu
ifade eder. Repository genel kalite kapısı kırmızı olduğu için bütün ürün için
production-ready anlamına gelmez.

## Kısmi veya sorunlu bileşenler

| Alan | Durum | Kanıt |
|---|---|---|
| Domain model contractı | 🔧 | `LogSourceType` JSON'da uppercase; eski test ve UI lowercase bekliyor |
| Parse/Pipeline contractı | 🔧 | `ParseError`, `ParseResult` ve empty-input test beklentileri kaymış |
| Plugin discovery | 🔧 | Loader/discovery testleri başarısız; container yalnız built-in parserları doğrudan yükler |
| Redis parser | 🔧 | Server, Sentinel ve systemd wrapper testleri başarısız |
| Batch orchestration | 🟡 | Ana akış var; orchestrator üç mypy call-arg hatası taşıyor |
| InMemoryEventStore | 🔧 | Duplicate/collision/replace/clear/reject ve thread testleri kırık |
| Atomic batch write | 🔧 | `storage/memory.py` içinde `atomic=True` dalı gerçek implementasyon yerine `pass` içeriyor |
| Query engine | 🔧 | Test fixture `LogEvent` importu eksik; query engine 4 mypy hatası taşıyor |
| Aggregation | 🔧 | Fixture/model validator/type sorunları var |
| Application service | 🟡 | Ana orchestration var; plugin lifecycle/config/response mapping tam değil |
| REST API | 🟡 | Çoğu endpoint versiyonsuz; file upload tüm body'yi tek seferde okuyor |
| Frontend contractı | 🔧 | `raw_log/raw_message`, `has_next/has_more`, lowercase/uppercase farkları var |
| Frontend testing | 🟡 | Yalnız bir smoke testi var |
| Dashboard | 🟡 | Tek severity bar chart ve parser facet listesi var |
| Analysis UI | ⏳ | Yeni Statistical Analysis ve Comparison API'leri tüketilmiyor |
| Auth/audit/report/deployment | ⏳ | Uygulama yok |

## Test ve kalite sonuçları

### Backend

| Komut | Sonuç | Ayrıntı |
|---|---|---|
| `poetry run pytest -q` | Başarısız | 399 passed, 21 failed, 11 errors, 11 warnings |
| `poetry run pytest -q --cov=log_parser_engine --cov-report=term` | Başarısız | Test sonucu aynı; toplam coverage %84 |
| `poetry run pytest -q tests/test_analysis_*.py tests/test_statistical_analysis_engine.py tests/test_latency_analysis.py tests/test_http_analysis.py` | Başarılı | 139 passed |
| `poetry run ruff check . --statistics` | Başarısız | 229 bulgu |
| `poetry run mypy src` | Başarısız | 5 dosyada 20 hata; 214 dosya kontrol edildi |
| `poetry build` | Başarılı | sdist ve wheel üretildi |

Ruff dağılımı:

| Kural | Adet |
|---|---:|
| `E501` line too long | 171 |
| `F401` unused import | 20 |
| `I001` import order | 19 |
| `F821` undefined name | 15 |
| `E701` multiple statements | 2 |
| `F541` useless f-string | 1 |
| `F841` unused variable | 1 |

Mypy hata dosyaları:

- `exceptions/storage.py`
- `models/event_aggregation.py`
- `storage/query_engine.py`
- `storage/memory.py`
- `batch/orchestrator.py`

Başarısız test kümeleri:

- entry-point/package plugin loading ve discovery/validation,
- `LogEvent` enum serialization,
- ParseError/ParseResult/Pipeline eski sözleşmeleri,
- Redis parser,
- InMemoryEventStore duplicate/collision/replace/clear/reject politikaları,
- thread-safety fixture'larında boş `raw_message`,
- aggregation fixture'larında eksik `raw_message`,
- query engine test fixture'ında eksik `LogEvent` importu.

### Frontend

| Komut | Sonuç | Ayrıntı |
|---|---|---|
| `npm test` | Başarılı | 1 test dosyası, 1 smoke test |
| `npm run lint` | Başarısız | ESLint 9, `eslint.config.*` bulamıyor; yalnız legacy `.eslintrc.cjs` var |
| `npm exec -- prettier --check "src/**/*.{ts,tsx,css}" "*.{json,md,ts,js,cjs}"` | Başarısız | 22 dosyada format farkı |
| `npm run build` | Başarılı | `tsc -b` ve Vite build tamamlandı |

Frontend build:

- JavaScript: 779,35 kB; gzip 226,34 kB.
- CSS: 17,49 kB; gzip 4,49 kB.
- Vite, 500 kB üzerindeki ana chunk için code-splitting uyarısı verdi.
- Ayrı `typecheck` scripti yok; TypeScript kontrolü build içindeki `tsc -b`
  adımıyla yapılıyor.

## Stub ve kalıntı taraması

`TODO`, `FIXME`, `HACK` veya `XXX` etiketi bulunmadı. Üç `pass` sonucu bulundu:

- `storage/memory.py`: atomic batch dalı — gerçek eksik implementasyon.
- `models/pipeline_result.py`: validator içindeki etkisiz `pass` — sözleşme
  incelemesi gerektiriyor.
- `batch/parser_session.py`: boş `DocumentAdapter` alt sınıfı — kasıtlı marker
  sınıfı olabilir.

Etiket bulunmaması teknik borç bulunmadığı anlamına gelmez.

## Repository hijyeni

- Proje altında 10.335 tracked dosyanın 9.928'i
  `frontend/node_modules/**` altındadır.
- `node_modules` dizini yaklaşık 194 MB'tır.
- Toplam 9.932 generated/dependency/cache dosyası izlenmektedir; bunlara
  `node_modules`, TypeScript build cache ve generated Vite config çıktıları
  dahildir.
- `.gitignore`, `node_modules/` ve `*.tsbuildinfo` kurallarını içermiyor.
- Repository kökünde `.DS_Store` tracked.
- `pyproject.toml` author alanı placeholder durumunda.
- `CHANGELOG`, `LICENSE`, `SECURITY`, `CONTRIBUTING`, `CODEOWNERS`, CI workflow,
  container manifesti ve runbook yok.

Bu dosyaları Git takibinden çıkarmak çalışma ağacında büyük ama mekanik bir
değişiklik yaratacaktır; ayrı ve gözden geçirilebilir bir çalışma olarak
yapılmalıdır.

## README ile kod arasındaki farklar

- README “production-oriented” ifadesini kullanıyor; tam kalite kapıları
  başarısız olduğu için ürün henüz production-ready değildir.
- Frontend README analysis/comparison API'lerini listelemiyor.
- README upload akışının boundsuz `UploadFile.read()` kullandığını söylemiyor.
- Plugin discovery notları vardır; runtime container discovery'yi çağırmaz.
- Frontend README API contractı ile elle yazılmış TypeScript modellerinin bazı
  alanları gerçek backendden sapmıştır.
- Repository kök README'si yalnız başlık seviyesindedir; gerçek dokümantasyon
  alt proje README'sindedir.

## Güvenlik ve performans notları

- Analysis endpointi request-size ve non-blocking concurrency sınırı uygular.
- File upload endpointi ingestiondan önce tüm uploadu belleğe alır.
- CORS local originlerle sınırlı başlar ancak methods/headers wildcard'dır.
- Authn/authz ve audit yoktur.
- Structured logging, Prometheus ve OpenTelemetry yoktur.
- UI fetch timeout'u `Promise.race` ile sonuçlandırır ancak underlying fetch'i
  kendi başına abort etmez.
- React Query Devtools production buildinde koşulsuz mount edilir.
- UI'da runtime response doğrulaması ve generated API client yoktur.
- Query/store kapasite ve concurrency davranışı kırık testler nedeniyle henüz
  production kanıtına sahip değildir.

## Sıradaki önerilen iş

### Foundation Quality Recovery — Dilim 1

Bir sonraki çalışma:

1. Public enum serialization kararını sabitler.
2. `LogEvent`, `ParseError`, `ParseResult` ve `PipelineResult` sözleşmelerini
   kod, test ve mevcut API/UI tüketimiyle karşılaştırır.
3. Geriye uyumlu en küçük düzeltmeleri uygular.
4. Domain/pipeline/plugin odak testlerini çalıştırır.
5. Tam backend test paketini yeniden çalıştırır.
6. Yeni kalan hata kümelerini kaydeder.
7. `PROJECT_ROADMAP.md` ve bu dosyayı günceller.

Bu dilim tamamlanmadan Report Engine veya yeni ürün özelliği başlatılmamalıdır.

### Dilim 1 kabul kriterleri

- Enum JSON sözleşmesi tek ve belgeli.
- Domain/parse/pipeline odak testleri başarılı.
- Bu sözleşmeye bağlı plugin testlerinin kırık nedeni ayrıştırılmış.
- Yeni Ruff/mypy ihlali yok.
- Tam test başarısızlık sayısı artmamış ve mümkün olan ilgili kümeler kapanmış.
- Public API/UI etkisi açıkça kaydedilmiş.

## Tekrarlanabilir kalite komutları

Backend:

```bash
poetry run pytest -q
poetry run pytest -q --cov=log_parser_engine --cov-report=term
poetry run ruff check . --statistics
poetry run mypy src
poetry build
```

Statistical Analysis odak kontrolü:

```bash
poetry run pytest -q \
  tests/test_analysis_*.py \
  tests/test_statistical_analysis_engine.py \
  tests/test_latency_analysis.py \
  tests/test_http_analysis.py
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npm exec -- prettier --check "src/**/*.{ts,tsx,css}" "*.{json,md,ts,js,cjs}"
npm run build
```

## Güncelleme kuralı

Her subsystem çalışmasından sonra:

1. Referans commit ve tarih güncellenir.
2. Gerçek komut sonuçları yazılır.
3. Kırmızı kontroller gizlenmez.
4. Roadmap durumu yalnız kabul kriterleri karşılandıysa yükseltilir.
5. In-memory ve multi-pod sınırlamaları korunur.
