# Parsel Engine Proje Yol Haritası

Son güncelleme: 25 Temmuz 2026  
Referans taban commit: `d278339`

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
Recovery** tamamlanmalıdır. Domain sözleşmesi, Redis stabilizasyonu ve built-in
parser canonical immutability dilimleri tamamlanmıştır. Sırada plugin startup
lifecycle, storage/query/aggregation, frontend sözleşmeleri ve repository
hijyeni vardır.

## Büyük aşamalar

| Aşama | Durum | Mevcut gerçeklik | Tamamlanma ölçütü | Ana risk |
|---|---|---|---|---|
| 1. Foundation | 🔧 | Poetry/src layout ve test altyapısı var; kalite kapıları kırmızı, merkezi structured logging/config eksik | Tam pytest, Ruff ve mypy başarılı; generated dosyalar izlenmiyor; config/logging sözleşmesi belgeli | Kırık temel üzerine yeni özellik eklenmesi |
| 2. Parser Core | 🔧 | BaseParser, context, registry, manager, detection ve normalization var | Plugin loader sözleşmeleri ve startup lifecycle testleri başarılı | Plugin keşfi container'a bağlı değil |
| 3. Built-in Parsers | ✅ | Sekiz built-in parser fixture ve canonical deep-immutability testlerinden geçiyor | Yeni parserlar aynı validated reconstruction contract kapısından geçer | Yeni plugin parserın doğrulamayı atlayan güncelleme yapması |
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
| Foundation | Domain models | ✅ | Pydantic v2 | Canonical enum çıktıları lowercase; legacy uppercase input kabul ediliyor |
| Foundation | Exception hierarchy | 🟡 | Domain models | Geniş hiyerarşi var; storage ve API mapping tutarlılığı eksik |
| Foundation | Configuration | 🟡 | Application container | Bazı options/env kullanımları var; merkezi ve doğrulanmış config yüzeyi yok |
| Foundation | Logging conventions | ⏳ | Request ID | Structured logging ve redaction standardı yok |
| Foundation | Quality tooling | 🔧 | Poetry/npm | Backend Ruff/mypy ve frontend ESLint/Prettier başarısız |
| Parser Core | BaseParser/metadata/context | ✅ | Domain models | Sözleşme ve güvenli wrapperlar mevcut |
| Parser Core | Registry/manager/detection | ✅ | BaseParser | Confidence, ambiguity ve registry yüzeyleri mevcut |
| Parser Core | Plugin discovery | 🟡 | Registry | Loader/discovery odak testleri yeşil; application startup'a bağlı değil |
| Parser Core | Normalization/pipeline | ✅ | Parser manager | Domain/pipeline odak sözleşme testleri yeşil; non-string input güvenli failure döndürüyor |
| Built-in Parsers | IIS W3C | ✅ | Stateful context | Header ve field mapping desteği var |
| Built-in Parsers | JSON/JSON Lines | ✅ | JSON profiles | Structured JSON ve line profilleri var |
| Built-in Parsers | Redis | ✅ | Canonical models | Yedi Redis testi; enrichment, context precedence ve deep immutability yeşil |
| Built-in Parsers | Canonical immutability audit | ✅ | LogEvent | Sekiz built-in parser root/nested attributes, tags ve serialization testlerinden geçiyor |
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

1. **Domain model ve parser sözleşmesi stabilizasyonu — tamamlandı**
   - Enum serialization kararını tek sözleşmede sabitle.
   - `LogEvent`, `ParseError`, `ParseResult` ve `PipelineResult` beklentilerini
     kod/test/API/UI arasında eşleştir.
   - İlgili odak testlerini ve ardından tam backend test paketini çalıştır.
   - Sonuç: 39 odak test geçti; tam paket 399/21 baseline'ından 417 passed,
     11 failed ve 11 setup error durumuna ilerledi; coverage %84 kaldı.
2. **Redis parser regresyonlarını gider — tamamlandı.**
   - Server, Sentinel ve systemd wrapper fixture'ları canonical event üretiyor.
   - Mapping enrichment alanları korunuyor; context parser alanlarını spoof
     edemiyor.
   - `LogEvent.model_validate()` ile attributes/tags yeniden doğrulanıp
     freeze ediliyor.
   - Sonuç: 7 Redis ve 113 parser/pipeline/orchestration odak testi geçti; tam
     paket 421 passed, 8 failed ve 11 setup error; coverage %84.
3. **Built-in parser canonical immutability audit'i — tamamlandı.**
   - `LogEvent.with_validated_updates(...)` ortak doğrulama kapısı eklendi.
   - Sekiz built-in parser bu kapıya taşındı; parser enrichment alanları ve
     canonical kimlik/zaman alanları korundu.
   - Root/nested attributes, context iç içe koleksiyonları, tags ve JSON
     round-trip gerçek fixturelarla doğrulandı.
   - Sonuç: built-in parser/pipeline/orchestration odak seçkisi 126 passed; tam
     paket 434 passed, 8 failed ve 11 setup error; coverage %84.
4. **Plugin discovery'yi application startup lifecycle'ına güvenli ve testli
   biçimde bağla — sıradaki iş.**
5. InMemoryEventStore atomic batch, duplicate, capacity ve clear davranışlarını
   tamamla.
6. Query/aggregation test ve mypy sorunlarını gider.
7. Backend Ruff ve mypy borcunu sıfırla.
8. Frontend API tiplerini gerçek backend sözleşmesiyle eşleştir; ESLint 9
   konfigürasyonunu ve temel component/contract testlerini ekle.
9. `node_modules`, TypeScript build cache ve generated Vite dosyalarını
   Git takibinden çıkarıp `.gitignore` kurallarını düzelt.
10. File upload akışını bounded/chunked yap; CORS/request ID/security header
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

Bir sonraki `devam et` komutunda yeni özellik açılmayacaktır. Plugin discovery
application startup lifecycle'ına bağlanacaktır. Yükleme allowlist'i, yalnız
`BaseParser` sınıflarının aday olması, deterministik sıra, duplicate politikası,
güvenli startup warningleri ve config ile kapatma davranışı odak ve container
entegrasyon testleriyle sabitlenecektir.
