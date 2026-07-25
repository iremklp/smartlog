# Parsel Engine Proje Yol Haritası

Son güncelleme: 25 Temmuz 2026  
Referans commit: `64d604c`

Bu belge repository içindeki gerçek kod ve kalite kontrollerine göre hazırlanmıştır.
Bir pazarlama veya hedef mimari belgesi değildir. Durumlar her subsystem
tamamlandığında yeniden doğrulanmalıdır.

## Durum göstergeleri

| İşaret | Anlam |
|---|---|
| ✅ | Tamamlandı ve mevcut kapsamındaki odak kontrolleri başarılı |
| 🟡 | Kullanılabilir bir uygulama var; kapsam veya kalite boşlukları bulunuyor |
| ⛔ | Dış karar, açık kullanıcı onayı veya tamamlanmamış bağımlılık nedeniyle bloke |
| ⏳ | Başlanmadı |
| 🔧 | Kod mevcut ancak sözleşme, test veya kalite sorunları nedeniyle düzeltilmeli |

## Değişmez mimari kararlar

- SQL ve harici kalıcı veri tabanı kullanılmaz.
- Aktif storage implementasyonu `InMemoryEventStore` olarak kalır.
- Eventler process/pod belleğindedir; restart sonrasında kaybolur ve replica'lar
  arasında paylaşılmaz.
- Parserlar `BaseParser`, metadata, detection ve normalization sözleşmelerine
  uyar.
- API, application service ve domain/storage katmanları ayrı tutulur.
- UI parser algoritması veya backend iş kurallarını tekrar uygulamaz.
- Authentication adapterı, kurumsal kimlik sağlayıcısı ve AI entegrasyonu ancak
  açık bir karar sonrasında geliştirilir.
- Yeni ürün özelliğinden önce repository genel kalite kapıları yeşil olmalıdır.

## Mevcut öncelik

Sıradaki çalışma yeni Report Engine değildir. Önce **Foundation Quality
Recovery** tamamlanmalıdır. İlk teknik dilim domain model ve parser sözleşmesi
kaymalarını gidermektir. Ardından plugin/Redis, storage/query/aggregation,
frontend sözleşmeleri ve repository hijyeni ele alınır.

## Büyük aşamalar

| Aşama | Durum | Mevcut gerçeklik | Tamamlanma ölçütü | Ana risk |
|---|---|---|---|---|
| 1. Foundation | 🔧 | Poetry/src layout ve test altyapısı var; kalite kapıları kırmızı, merkezi structured logging/config eksik | Tam pytest, Ruff ve mypy başarılı; generated dosyalar izlenmiyor; config/logging sözleşmesi belgeli | Kırık temel üzerine yeni özellik eklenmesi |
| 2. Parser Core | 🔧 | BaseParser, context, registry, manager, detection ve normalization var | Plugin loader sözleşmeleri ve startup lifecycle testleri başarılı | Plugin keşfi container'a bağlı değil |
| 3. Built-in Parsers | 🔧 | Sekiz built-in parser ailesi kayıtlı | Bütün parser contract/fixture testleri başarılı; Redis regresyonları kapalı | Model enum/sözleşme kayması parser sonuçlarını etkiliyor |
| 4. Ingestion | ✅ | Text/byte/path, encoding, BOM, binary, line ending, gzip/zip ve güvenlik kontrolleri var | Odak ingestion testleri yeşil; limitler belgeli | API upload route'u ingestion öncesinde boundsuz okuyor |
| 5. Batch Orchestration | 🟡 | Line/document/stateful mode, sampling, session, error policy ve streaming var | Batch testleri ve mypy tamamen başarılı; public sınırlar tutarlı | Orchestrator tip hataları ve karmaşık lifecycle |
| 6. In-Memory Storage | 🔧 | Store, identity, retention, eviction ve istatistik yüzeyi var | Atomic batch gerçekten atomik; duplicate/capacity/thread-safety testleri başarılı | `atomic=True` yolu uygulanmamış |
| 7. Query Engine | 🔧 | Typed filter, sort, pagination, facet ve aggregation var | Query/aggregation testleri ve mypy başarılı; API/UI contractı sabit | Test fixture hataları ve tip/sözleşme uyumsuzlukları |
| 8. Application Service | 🟡 | Container ve orchestration servisi parsing/store/query/analysis'i bağlıyor | Lifecycle, güvenli response mapping ve config testleri tamam | Plugin discovery bypass ediliyor |
| 9. REST API | 🟡 | FastAPI app factory ve temel endpointler var | Versioned contract, bounded upload, güvenli error mapping, readiness ve limit testleri tamam | Çoğu endpoint versiyonsuz; file upload boundsuz |
| 10. Web UI | 🟡 | React/Vite UI'da yedi sayfa ve temel akışlar var | Backend contractlarıyla uyumlu, erişilebilir, testli ve lint/typecheck/build kapıları yeşil | Elle tutulan tipler backendden sapmış |
| 11. Statistical Analysis | 🟡 | Engine ve `/api/v1/analysis*` API kapsamı tamam; 139 odak test geçiyor | Statistical Analysis UI, comparison ve dashboard entegrasyonu tamam | UI mevcut analiz API'sini tüketmiyor |
| 12. Report Engine | ⏳ | Uygulama yok | Bounded HTML/Markdown/JSON/CSV çıktısı, güvenli download lifecycle ve testler | PDF/Excel dependency ve response boyutu |
| 13. Rule Engine | ⏳ | Uygulama yok | Typed ve deterministik koşullar; `eval`/arbitrary code yok; testli API/UI | Güvensiz expression tasarımı |
| 14. Alert Engine | ⏳ | Uygulama yok | In-memory state, deduplication, suppression, cooldown ve acknowledgement testli | Restartta state kaybı |
| 15. Scheduler ve Automation | ⏳ | Uygulama yok | Güvenli in-process lifecycle ve duplicate-job riski belgeli | Multi-pod duplicate execution |
| 16. Audit ve Enterprise Controls | ⏳ | Uygulama yok | Redacted, bounded ve in-memory audit eventleri; kritik operasyonlar kapsanmış | Kalıcı audit garantisi verilemez |
| 17. Authentication/Authorization | ⛔ | Abstraction yok | Açık kullanıcı onayı sonrası identity/role/permission abstractionı; adapter sınırı testli | Kurumsal sağlayıcı varsaymak |
| 18. Observability | 🟡 | Request ID, health ve process-local runtime metrics var | Structured logs, Prometheus metrics, readiness ve cardinality sınırları tamam | Raw log/PII sızıntısı ve yüksek cardinality |
| 19. Security Hardening | 🟡 | Parser/analysis limitleri ve bazı güvenli hata davranışları var | Threat model, dependency/static/secret scan, upload/CORS/CSP/container kontrolleri yeşil | Boundsuz upload ve auth eksikliği |
| 20. Deployment | ⏳ | Containerfile veya OpenShift manifesti yok | Non-root, read-only, resource/probe tanımlı image ve OpenShift manifestleri doğrulanmış | Process-local verinin replica'larda ayrışması |
| 21. CI/CD | ⏳ | Workflow yok | Backend/frontend quality gate, image scan, SBOM, release ve rollback akışı var | Kırık kalite kapılarının otomatikleşmemesi |
| 22. Performance/Stability | 🟡 | Bazı bounds, concurrency ve memory testleri var | Parser/store/query/analysis benchmark, API load, soak ve kapasite rehberi tamam | 779 kB frontend bundle ve belirsiz kapasite |
| 23. AI Analysis | ⛔ | Uygulama yok | Yalnız açık talep sonrası provider abstraction, redaction, evidence ve cost limitleri | Veri dış servise çıkışı ve hallucination |

## Aktif subsystem envanteri

| Katman | Subsystem | Durum | Bağımlılık | Not |
|---|---|---|---|---|
| Foundation | Repository/package yapısı | 🟡 | Yok | Python ve frontend paketleri var; yaklaşık 9.928 `node_modules` dosyası izleniyor |
| Foundation | Domain models | 🔧 | Pydantic v2 | Enum JSON değerleri ile test/UI beklentileri uyuşmuyor |
| Foundation | Exception hierarchy | 🟡 | Domain models | Geniş hiyerarşi var; storage ve API mapping tutarlılığı eksik |
| Foundation | Configuration | 🟡 | Application container | Bazı options/env kullanımları var; merkezi ve doğrulanmış config yüzeyi yok |
| Foundation | Logging conventions | ⏳ | Request ID | Structured logging ve redaction standardı yok |
| Foundation | Quality tooling | 🔧 | Poetry/npm | Backend Ruff/mypy ve frontend ESLint/Prettier başarısız |
| Parser Core | BaseParser/metadata/context | ✅ | Domain models | Sözleşme ve güvenli wrapperlar mevcut |
| Parser Core | Registry/manager/detection | ✅ | BaseParser | Confidence, ambiguity ve registry yüzeyleri mevcut |
| Parser Core | Plugin discovery | 🔧 | Registry | Loaderlar var; testler kırık ve application startup'a bağlı değil |
| Parser Core | Normalization/pipeline | 🔧 | Parser manager | Uygulama var; eski ParseResult/Pipeline beklentileri kaymış |
| Built-in Parsers | IIS W3C | ✅ | Stateful context | Header ve field mapping desteği var |
| Built-in Parsers | JSON/JSON Lines | ✅ | JSON profiles | Structured JSON ve line profilleri var |
| Built-in Parsers | Redis | 🔧 | Canonical models | Üç Redis parser testi başarısız |
| Built-in Parsers | Apache/Nginx access/error | ✅ | Webserver parser | Ortak parser ailesi ve plugin entry modülleri var |
| Built-in Parsers | Windows Event XML | ✅ | `defusedxml` | Güvenli XML decoder ve mapping var |
| Built-in Parsers | RFC3164/RFC5424 | ✅ | Syslog tokenizer | İki ayrı parser mevcut |
| Ingestion | Text/bytes/path ve encoding | ✅ | Ingestion options | BOM, binary, encoding ve metadata var |
| Ingestion | Gzip/Zip güvenliği | ✅ | Archive options | Entry seçimi ve archive güvenlik kuralları var |
| Batch | Streaming ve parser session | 🟡 | Parser manager | İşlevsel; `batch/orchestrator.py` mypy hataları taşıyor |
| Storage | InMemoryEventStore | 🔧 | LogEvent | Duplicate/capacity/clear/thread-safety testleri kırık |
| Storage | Atomic batch write | 🔧 | InMemoryEventStore | `atomic=True` dalında gerçek transaction planı yok |
| Query | Filter/sort/pagination/index | 🔧 | StoredEvent snapshot | Test setup ve mypy hataları var |
| Query | Facet/aggregation | 🔧 | Query engine | Model validator ve bucket type sorunları var |
| Application | ApplicationContainer/service | 🟡 | Tüm backend katmanları | Ana orchestration var; lifecycle/config boşlukları sürüyor |
| API | FastAPI routes/middleware | 🟡 | Application service | Request ID ve analiz limitleri var; versioning/upload güvenliği eksik |
| UI | React shell ve temel sayfalar | 🟡 | REST API | Parse/query/store/system akışları var; sözleşme ve test kapsamı yetersiz |
| Analysis | StatisticalAnalysisEngine | ✅ | Store snapshot | Summary, distribution, timeline, latency, HTTP, comparison ve insight var |
| Analysis | Analysis UI/dashboard | ⏳ | Analysis API | `/api/v1/analysis` ve compare UI tarafından çağrılmıyor |

## Yakın dönem teslimat sırası

### Q0 — Foundation Quality Recovery

1. **Domain model ve parser sözleşmesi stabilizasyonu — sıradaki iş**
   - Enum serialization kararını tek sözleşmede sabitle.
   - `LogEvent`, `ParseError`, `ParseResult` ve `PipelineResult` beklentilerini
     kod/test/API/UI arasında eşleştir.
   - İlgili odak testlerini ve ardından tam backend test paketini çalıştır.
2. Plugin discovery ve Redis parser regresyonlarını gider.
3. InMemoryEventStore atomic batch, duplicate, capacity ve clear davranışlarını
   tamamla.
4. Query/aggregation test ve mypy sorunlarını gider.
5. Backend Ruff ve mypy borcunu sıfırla.
6. Frontend API tiplerini gerçek backend sözleşmesiyle eşleştir; ESLint 9
   konfigürasyonunu ve temel component/contract testlerini ekle.
7. `node_modules`, TypeScript build cache ve generated Vite dosyalarını
   Git takibinden çıkarıp `.gitignore` kurallarını düzelt.
8. File upload akışını bounded/chunked yap; CORS/request ID/security header
   davranışlarını test et.

Q0 kabul kriterleri:

- `poetry run pytest` başarılı.
- `poetry run pytest --cov=log_parser_engine` başarılı ve mevcut %84 coverage
  gerilememiş.
- `poetry run ruff check .` başarılı.
- `poetry run mypy src` başarılı.
- `npm test`, `npm run lint`, frontend typecheck ve `npm run build` başarılı.
- Prettier check başarılı.
- Üretilmiş dependency/build-cache dosyaları Git tarafından izlenmiyor.
- API/UI sözleşme testleri mevcut.

### Q1 — Statistical Analysis UI entegrasyonu

- Analysis ve comparison request builder.
- Summary, distribution, timeline, latency ve HTTP görünümleri.
- Bounded chart/table rendering.
- Loading, empty, partial ve güvenli error state'leri.
- Dashboard global filtreleri ve drill-down.
- Component, API contract ve accessibility testleri.

Bağımlılık: Q0.

### Q2 — Report Engine

- Önce HTML, Markdown, JSON ve CSV.
- Report request/section/chart/table abstractionları.
- Size limitleri, güvenli dosya adı ve request-bound download lifecycle.
- API, UI ve testler.
- PDF/Excel ancak dependency ve güvenlik kararı sonrasında.

Bağımlılık: Q0 ve Q1.

### Q3 — Rule, Alert ve Audit

- Deterministik typed rule engine.
- In-memory alert state, deduplication ve acknowledgement.
- Redacted in-memory audit events.
- Restart ve multi-pod sınırlamalarının UI/API'de görünür olması.

Bağımlılık: Q0 ve Q2.

### Q4 — Operasyonel production hazırlığı

- Authentication/authorization readiness abstractionı.
- Structured logging ve Prometheus metrics.
- Security hardening ve threat model.
- Non-root container ve OpenShift manifestleri.
- Performance/load/E2E testleri.
- CI/CD quality gates, release/versioning ve runbook.
- Final architecture ve production-readiness review.

Bağımlılık: Q0; kimlik sağlayıcısı ve kurumsal adapterlar için ayrıca açık
kullanıcı kararı gerekir.

### Q5 — AI Analysis

Yalnız açık kullanıcı talebiyle ve en son değerlendirilir. Sistem AI olmadan
tam çalışmaya devam eder.

## Bir sonraki `devam et`

Bir sonraki `devam et` komutunda yeni özellik açılmayacaktır. Önce domain model
ve parser sözleşmesi kaymaları yeniden üretilecek; beklenen public JSON
sözleşmesi kod, test ve mevcut frontend kullanımı karşılaştırılarak
sabitlenecektir. En küçük uyumlu düzeltmeler uygulanacak, odak testleri ve tam
backend kalite kontrolleri çalıştırılacak, ardından bu belge ile
`DEVELOPMENT_STATUS.md` güncellenecektir.
