# Parsel Engine Geliştirme Durumu

Son kalite kontrolü: 25 Temmuz 2026  
Branch: `main`  
Referans taban commit: `e5523f8`
Remote durumu: çalışma başlangıcında `main`, `origin/main` ile aynıydı.

Bu dosya doğrulanmış repository durumunu kaydeder. “Production-oriented”
tasarım hedefini production-readiness onayı olarak kullanmaz.

## Son tamamlanan iş

Son tamamlanan teknik dilim **Foundation Quality Recovery — Redis Parser
Stabilizasyonu**dur.

Bu dilimde:

- shallow `dict()` ve runtime etkisi olmayan `cast()` nedeniyle nested
  `FrozenDict.update()` üzerinde oluşan üç Redis regresyonu kapatıldı,
- mapping katmanındaki `category`, `matched_rule`, `parser_attributes` ve
  wrapper metadata alanları kaybedilmeden canonical evente taşındı,
- context metadata korunurken parser-authoritative Redis ve parser kimlik
  alanlarının spoof edilmesi engellendi,
- `model_copy(update=...)` doğrulama bypassı kaldırıldı; event
  `LogEvent.model_validate()` ile yeniden doğrulanıp deep-freeze edildi,
- root/nested attributes, `redis_event` ve tags immutability regresyon testleri
  eklendi,
- Redis, built-in parser, pipeline ve orchestration odak seçkileri doğrulandı.

Odak sonuçları: **7 Redis testi** ve **113 parser/pipeline/orchestration testi**
geçti. Önceki domain contract seçkisi **39 passed**, Statistical Analysis
seçkisi ise regresyonsuz **139 passed** durumundadır.

## Repository snapshotı

| Alan | Değer |
|---|---|
| Backend paket | `log-parser-engine` `0.1.0` |
| Python | `3.11.15` |
| Poetry | `2.4.1` |
| Backend kaynak dosyası | 214 Python dosyası |
| Backend test modülü | 85 |
| Frontend paket | `log-parser-engine-ui` `0.1.0` |
| Node.js | `24.18.0` |
| npm | `11.16.0` |
| Frontend stack | React 18, TypeScript, Vite, TanStack Query/Table, Recharts |
| Storage | Yalnız `InMemoryEventStore` |
| SQL/harici DB | Yok |
| Ayrı CI/deployment | Yok |

Çalışma başlangıcında kaynak repository temizdi. Foundation Quality Recovery
dilimleri ayrı bir yazılabilir çalışma kopyasında uygulanmış ve `main` branch
için doğrulanmıştır.

## Tamamlanmış veya odak kapsamında doğrulanmış bileşenler

- BaseParser, ParserContext, metadata, registry, manager ve detection scoring.
- IIS W3C, JSON/JSON Lines, Apache/Nginx access/error, Windows Event XML,
  RFC3164 ve RFC5424 parser implementasyonları.
- Text/byte/path ingestion, encoding, BOM, binary, line ending, gzip/zip ve
  archive güvenliği.
- Canonical normalization.
- Lowercase enum wire contractı ve legacy uppercase input uyumluluğu.
- Pipeline non-string ve errorsız non-success sonuçlarının güvenli failure
  davranışı.
- Redis server, Sentinel ve systemd wrapper canonical parse akışları.
- Redis enrichment/context precedence ve revalidated deep immutability.
- Package/entry-point plugin loader ve discovery/validation odak sözleşmeleri.
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
| Domain model contractı | ✅ | Enum çıktıları lowercase; uppercase/case-insensitive legacy input kabul ediliyor |
| Parse/Pipeline contractı | ✅ | Domain/pipeline odak testleri ve güvenli failure regresyonları başarılı |
| Plugin discovery | 🟡 | Loader/discovery odak testleri başarılı; container hâlâ yalnız built-in parserları doğrudan yükler |
| Redis parser | ✅ | 7/7 test; server, Sentinel, systemd, enrichment ve immutability başarılı |
| Built-in parser immutability | 🔧 | Redis düzeltildi; IIS/JSON/Syslog/Windows `model_copy` yolları audit edilmeli |
| Batch orchestration | 🟡 | Ana akış var; orchestrator üç mypy call-arg hatası taşıyor |
| InMemoryEventStore | 🔧 | Duplicate/collision/replace/clear/reject ve thread testleri kırık |
| Atomic batch write | 🔧 | `storage/memory.py` içinde `atomic=True` dalı gerçek implementasyon yerine `pass` içeriyor |
| Query engine | 🔧 | Test fixture `LogEvent` importu eksik; query engine 4 mypy hatası taşıyor |
| Aggregation | 🔧 | Fixture/model validator/type sorunları var |
| Application service | 🟡 | Ana orchestration var; plugin lifecycle/config/response mapping tam değil |
| REST API | 🟡 | Çoğu endpoint versiyonsuz; file upload tüm body'yi tek seferde okuyor |
| Frontend contractı | 🔧 | `raw_log/raw_message`, `has_next/has_more` ve elle tutulan tip farkları var |
| Frontend testing | 🟡 | Yalnız bir smoke testi var |
| Dashboard | 🟡 | Tek severity bar chart ve parser facet listesi var |
| Analysis UI | ⏳ | Yeni Statistical Analysis ve Comparison API'leri tüketilmiyor |
| Auth/audit/report/deployment | ⏳ | Uygulama yok |

## Test ve kalite sonuçları

### Backend

| Komut | Sonuç | Ayrıntı |
|---|---|---|
| `poetry run pytest -q` | Başarısız | 421 passed, 8 failed, 11 errors, 11 warnings |
| `poetry run pytest -q --cov=log_parser_engine --cov-report=term` | Başarısız | Aynı kalan hata kümeleriyle toplam coverage %84 |
| Domain/pipeline/plugin/API odak contract seçkisi | Başarılı | 39 passed |
| Redis parser odak seçkisi | Başarılı | 7 passed |
| Built-in parser/pipeline/orchestration seçkisi | Başarılı | 113 passed |
| `poetry run pytest -q tests/test_analysis_*.py tests/test_statistical_analysis_engine.py tests/test_latency_analysis.py tests/test_http_analysis.py` | Başarılı | 139 passed |
| `poetry run ruff check . --statistics` | Başarısız | 226 bulgu |
| `poetry run mypy src` | Başarısız | 5 dosyada 20 hata; 214 dosya kontrol edildi |
| `poetry build` | Başarılı | sdist ve wheel üretildi |

Sandbox yazılabilir sparse clone içinde yeni Poetry virtualenv oluşturamadığı
için bu dilimin pytest/Ruff/mypy kontrolleri mevcut Poetry virtualenv
binaryleri ve `PYTHONPATH=src` ile çalıştırılmıştır. Tablodaki komutlar
repository için canonical tekrar komutlarıdır.

Ruff dağılımı:

| Kural | Adet |
|---|---:|
| `E501` line too long | 170 |
| `F401` unused import | 19 |
| `I001` import order | 18 |
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

- InMemoryEventStore duplicate/collision/replace/clear/reject politikaları,
- thread-safety fixture'larında boş `raw_message`,
- aggregation fixture'larında eksik `raw_message`,
- query engine test fixture'ında eksik `LogEvent` importu.

İlk tam paket baseline'ı 399 passed / 21 failed idi. İki Foundation dilimi
sonunda sonuç 421 passed / 8 failed durumuna ilerlemiş, setup error sayısı
artmamıştır. Kalan storage/query fixture hataları nedeniyle canonical
`LogEvent.raw_message` nonblank kuralı gevşetilmemiştir.

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
- Plugin discovery odak testleri başarılıdır; runtime container discovery'yi
  hâlâ çağırmaz.
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

### Foundation Quality Recovery — Dilim 3: Built-in Parser Immutability

Bir sonraki çalışma:

1. IIS, JSON, RFC3164/RFC5424 ve Windows Event başarılı parser çıktılarının
   root/nested attributes ve tags immutability davranışını yeniden üretir.
2. Pydantic `model_copy(update=...)` ile validation bypass edilen yolları
   belirler.
3. Parser-specific enrichment alanlarını kaybetmeden validated reconstruction
   veya ortak, küçük bir helper uygular.
4. Her parser için mutation, serialization ve canonical field regresyon
   testleri ekler.
5. Bütün built-in parser, pipeline, batch ve application container odak
   seçkisini çalıştırır.
6. Plugin discovery'nin yalnız contract düzeyinde yeşil, startup lifecycle
   düzeyinde eksik olduğunu korur.
7. Roadmap ve bu durum kaydını gerçek komut sonuçlarıyla günceller.

Bu dilim ve kalan Q0 kalite borçları tamamlanmadan Report Engine veya yeni ürün
özelliği başlatılmamalıdır.

### Dilim 3 kabul kriterleri

- Bütün built-in parserların başarılı `LogEvent` çıktılarında root/nested
  attributes ve tags mutate edilemez.
- Parser-specific enrichment ve canonical alanlar korunur.
- JSON serialization ve parser/pipeline contractları gerilemez.
- Built-in parser/pipeline/orchestration odak seçkisi başarılıdır.
- Yeni Ruff/mypy ihlali yok.
- Tam test failure/error sayıları artmamıştır.

## Public contract notu

- API/model JSON çıktılarında enum değerleri lowercase/snake_case'tir.
- Eski uppercase inputlar, member adları ve karışık case değerler trim edilerek
  kabul edilir.
- `ParseStatus.FAILURE`, `FAILED`, `failure` ve `failed` aynı canonical
  `"failed"` değeridir.
- `LogEvent.raw_message` zorunlu ve nonblank kalır.
- Content hash ve index anahtarları canonical lowercase değerleri kullanır.
  Store yalnız process belleğinde olduğu için kalıcı veri migrasyonu yoktur;
  yine de bu wire normalization release notunda belirtilmelidir.

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
