# Parsel Engine Proje Yol Haritası

Son güncelleme: 29 Temmuz 2026
Doğrulama tabanı: `79d8ec3` sonrası çalışma ağacı

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

**Foundation Quality Recovery tamamlandı.** Backend ve frontend kalite kapıları
birlikte yeşildir; upload akışı bounded/chunked çalışır, güvenli request ID,
explicit CORS ve temel API security header sözleşmeleri testlerle sabittir.
Sıradaki ürün dilimi **Q1 Statistical Analysis UI entegrasyonu**dur.

## Büyük aşamalar

| Aşama | Durum | Mevcut gerçeklik | Tamamlanma ölçütü | Ana risk |
|---|---|---|---|---|
| 1. Foundation | 🟡 | Poetry/src layout, yeşil backend/frontend kalite kapıları ve temiz generated-file sınırı var; merkezi structured logging/config eksik | Config/logging sözleşmesi Q4'te tamamlanmış | Dağınık environment/config davranışı |
| 2. Parser Core | ✅ | BaseParser, context, registry, manager, detection, normalization ve güvenli plugin startup lifecycle var | Yeni pluginler aynı allowlist, staging ve sözleşme testlerinden geçer | Güvenilir plugin kodu process yetkileriyle çalışır |
| 3. Built-in Parsers | ✅ | Sekiz built-in parser fixture ve canonical deep-immutability testlerinden geçiyor | Yeni parserlar aynı validated reconstruction contract kapısından geçer | Yeni plugin parserın doğrulamayı atlayan güncelleme yapması |
| 4. Ingestion | ✅ | Text/byte/path, encoding, BOM, binary, line ending, gzip/zip ve güvenlik kontrolleri; API uploadında 64 KiB chunk ve byte limiti var | Odak ingestion/upload testleri yeşil; limitler belgeli | Upload request süresince bounded içerik process belleğindedir |
| 5. Batch Orchestration | ✅ | Line/document/stateful mode, sampling, session, error policy, streaming ve typed oversized-record failure testli | Yeni policy yolları aynı typed exception ve stream testlerinden geçer | Karmaşık session lifecycle'ında regresyon riski |
| 6. In-Memory Storage | ✅ | Typed single write, gerçek atomic rollback, retention, eviction, monoton sequence ve snapshot query var | Yeni write politikaları aynı rollback/index/thread testlerinden geçer | Process/pod restartında veri kaybı tasarım gereğidir |
| 7. Query Engine | ✅ | Typed ve deterministik filter, sort, pagination, facet ve aggregation sözleşmeleri testli | API/UI contractı aynı modellerle sabitlenir | Büyük snapshotlarda O(n log n) sort maliyeti |
| 8. Application Service | 🟡 | Container parsing/store/query/analysis ve tek seferlik plugin startup lifecycle'ı bağlıyor | Güvenli response mapping ve merkezi config testleri tamam | API lifecycle/config boşlukları sürüyor |
| 9. REST API | 🟡 | FastAPI app factory, bounded upload, güvenli request ID/CORS/header davranışları ve temel endpointler var | Versioned contract, ortak error envelope ve readiness tamam | Çoğu endpoint versiyonsuz; error sözleşmesi tamamen birleşik değil |
| 10. Web UI | 🟡 | React/Vite UI'da yedi sayfa, backend uyumlu temel contractlar ve yeşil kalite kapıları var | Analysis/comparison UI, erişilebilirlik ve route-level code splitting tamam | İstatistiksel analiz API'si henüz ekranda tüketilmiyor |
| 11. Statistical Analysis | 🟡 | Engine ve `/api/v1/analysis*` API kapsamı tamam; 139 odak test geçiyor | Statistical Analysis UI, comparison ve dashboard entegrasyonu tamam | UI mevcut analiz API'sini tüketmiyor |
| 12. Report Engine | ⏳ | Uygulama yok | Bounded HTML/Markdown/JSON/CSV çıktısı, güvenli download lifecycle ve testler | PDF/Excel dependency ve response boyutu |
| 13. Rule Engine | ⏳ | Uygulama yok | Typed ve deterministik koşullar; `eval`/arbitrary code yok; testli API/UI | Güvensiz expression tasarımı |
| 14. Alert Engine | ⏳ | Uygulama yok | In-memory state, deduplication, suppression, cooldown ve acknowledgement testli | Restartta state kaybı |
| 15. Scheduler ve Automation | ⏳ | Uygulama yok | Güvenli in-process lifecycle ve duplicate-job riski belgeli | Multi-pod duplicate execution |
| 16. Audit ve Enterprise Controls | ⏳ | Uygulama yok | Redacted, bounded ve in-memory audit eventleri; kritik operasyonlar kapsanmış | Kalıcı audit garantisi verilemez |
| 17. Authentication/Authorization | ⛔ | Abstraction yok | Açık kullanıcı onayı sonrası identity/role/permission abstractionı; adapter sınırı testli | Kurumsal sağlayıcı varsaymak |
| 18. Observability | 🟡 | Request ID, health ve process-local runtime metrics var | Structured logs, Prometheus metrics, readiness ve cardinality sınırları tamam | Raw log/PII sızıntısı ve yüksek cardinality |
| 19. Security Hardening | 🟡 | Parser/analysis limitleri, bounded upload, explicit CORS, güvenli request ID ve temel response headerları var | Threat model, dependency/static/secret scan, auth readiness, CSP ve container kontrolleri yeşil | Auth ve otomatik supply-chain taramaları eksik |
| 20. Deployment | ⏳ | Containerfile veya OpenShift manifesti yok | Non-root, read-only, resource/probe tanımlı image ve OpenShift manifestleri doğrulanmış | Process-local verinin replica'larda ayrışması |
| 21. CI/CD | ⏳ | Workflow yok | Backend/frontend quality gate, image scan, SBOM, release ve rollback akışı var | Kırık kalite kapılarının otomatikleşmemesi |
| 22. Performance/Stability | 🟡 | Bazı bounds, concurrency ve memory testleri var | Parser/store/query/analysis benchmark, API load, soak ve kapasite rehberi tamam | 779 kB frontend bundle ve belirsiz kapasite |
| 23. AI Analysis | ⛔ | Uygulama yok | Yalnız açık talep sonrası provider abstraction, redaction, evidence ve cost limitleri | Veri dış servise çıkışı ve hallucination |

## Aktif subsystem envanteri

| Katman | Subsystem | Durum | Bağımlılık | Not |
|---|---|---|---|---|
| Foundation | Repository/package yapısı | ✅ | Yok | Python ve frontend paketleri var; dependency ve build-cache çıktıları Git dışında |
| Foundation | Domain models | ✅ | Pydantic v2 | Canonical enum çıktıları lowercase; legacy uppercase input kabul ediliyor |
| Foundation | Exception hierarchy | 🟡 | Domain models | Geniş hiyerarşi var; storage ve API mapping tutarlılığı eksik |
| Foundation | Configuration | 🟡 | Application container | Bazı options/env kullanımları var; merkezi ve doğrulanmış config yüzeyi yok |
| Foundation | Logging conventions | ⏳ | Request ID | Structured logging ve redaction standardı yok |
| Foundation | Quality tooling | ✅ | Poetry/npm | Backend pytest/coverage/Ruff/mypy/build ve frontend typecheck/ESLint/Vitest/Prettier/build başarılı |
| Parser Core | BaseParser/metadata/context | ✅ | Domain models | Sözleşme ve güvenli wrapperlar mevcut |
| Parser Core | Registry/manager/detection | ✅ | BaseParser | Confidence, ambiguity ve registry yüzeyleri mevcut |
| Parser Core | Plugin discovery | ✅ | Registry | Default-off allowlist, strict staging, warn izolasyonu ve container startup testleri yeşil |
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
| Batch | Streaming ve parser session | ✅ | Parser manager | Oversized-record stop yolu typed exception üretir; source mypy temiz |
| Storage | InMemoryEventStore | ✅ | LogEvent | Typed errors, duplicate/capacity/clear ve concurrency testleri yeşil |
| Storage | Atomic batch write | ✅ | InMemoryEventStore | Store state/index/counter/sequence rollback testli |
| Query | Filter/sort/pagination/index | ✅ | StoredEvent snapshot | Deterministik davranış ve source type/lint kapısı yeşil |
| Query | Facet/aggregation | ✅ | Query engine | Bounded facet ve UTC aggregation sözleşmeleri testli |
| Application | ApplicationContainer/service | 🟡 | Tüm backend katmanları | Ana orchestration var; lifecycle/config boşlukları sürüyor |
| API | FastAPI routes/middleware | 🟡 | Application service | Bounded upload, güvenli request ID/CORS/header ve analiz limitleri var; ortak versioning eksik |
| UI | React shell ve temel sayfalar | 🟡 | REST API | Parse/query/store/system akışları ve contract/component testleri var; analysis UI bekliyor |
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
   biçimde bağla — tamamlandı.**
   - Harici discovery varsayılan kapalı ve yalnız allowlist kaynaklarla
     etkinleşiyor.
   - Package manifesti, entry-point adı, candidate/warning limitleri ve yalnız
     `BaseParser` sınıfı kabulü doğrulanıyor.
   - Strict mod gerçek registry'yi kısmi değiştirmiyor; warn mod sağlıklı
     pluginleri koruyor.
   - Built-in kayıt sırası, duplicate reject/replace ve built-in replacement
     opt-in davranışları testli.
   - Sonuç: plugin/application odak seçkisi 60 passed; tam backend paketi
     481 passed, 8 failed ve 11 setup error. Açık hatalar storage/query
     baseline'ındadır.
5. **InMemoryEventStore atomic batch, duplicate, capacity ve clear
   davranışlarını tamamla — tamamlandı.**
   - Single write typed duplicate/collision/capacity hatalarını koruyor.
   - Atomic batch başarısızlıkta event, index, sayaç ve sequence state'ini geri
     yüklüyor.
   - Duplicate ignore capacity eviction'dan önce çözülüyor; replace ID ve
     sequence'i koruyor.
   - Clear sequence'i sıfırlamıyor; concurrent add/query/delete testleri
     geçiyor.
   - Query ve aggregation fixture'ları canonical nonblank `raw_message`
     sözleşmesine taşındı.
   - Sonuç: tam backend paketi 505 passed; coverage %85.
6. **Query/aggregation test ve mypy sorunlarını gider — tamamlandı.**
   - Pydantic v2 model validatorları ve aggregation bucket sözleşmeleri
     düzeltildi.
   - Yalnız yapılandırılmış indexler kullanılıyor; eksik indexte full-scan
     fallback uygulanıyor.
   - Parser filter/facet/aggregation, optional sort, bounded facet ve UTC time
     bucket davranışları testlendi.
   - Sonuç: tam backend paketi 521 passed; coverage %85; query/storage source
     Ruff ve mypy kontrolleri başarılı.
7. **Backend Ruff ve mypy borcunu sıfırla — tamamlandı.**
   - Oversized batch record stop yolu typed domain exceptionına bağlandı.
   - `mypy src` 216 source dosyasında sıfır hata ile tamamlandı.
   - Kalan import sırası, kullanılmayan sembol ve satır uzunluğu bulguları
     davranış değiştirmeyen temizliklerle giderildi.
   - Sonuç: 523 test, %86 coverage, repository geneli Ruff ve mypy başarılı;
     wheel/sdist build başarılı.
8. **Frontend API sözleşmesini ve kalite araçlarını düzelt — tamamlandı.**
   - Canonical `LogEvent`, parse, batch, pagination, query ve analysis tipleri
     backend response modelleriyle eşleştirildi.
   - Parser kimliği `attributes.parser_name` üzerinden okunuyor; pagination
     backendin serialize ettiği `offset`, `limit`, `returned` ve `total`
     alanlarından türetiliyor.
   - `/api/v1/analysis` ve `/api/v1/analysis/compare` istemcileri eklendi.
   - ESLint 9 flat config, Vitest jsdom/setup ve Prettier kapıları çalışıyor.
   - Sonuç: 11 frontend testi, typecheck, lint, format check ve production
     build başarılı; backend paketi 525 test ve %86 coverage ile yeşil.
9. **Generated frontend dosyalarını Git takibinden çıkar — tamamlandı.**
   - `node_modules`, `.vite`, `coverage`, `*.tsbuildinfo` ve `.DS_Store`
     ignore kuralları eklendi.
   - Dependency manifesti ve `package-lock.json` kaynak kontrolünde korunuyor.
   - Build ve test cache'leri yeniden üretilebilir yerel çıktılar olarak
     değerlendiriliyor.
10. **File upload ve API güvenlik sınırlarını tamamla — tamamlandı.**
    - Upload streami 64 KiB chunklarla ve en fazla `max_bytes + 1` probe ile
      okunuyor; başarı, limit, boş içerik ve hata yollarında her zaman
      kapatılıyor.
    - Varsayılan 50 MiB upload limiti uygulama options modeliyle doğrulanıyor;
      aşım güvenli `413`, boş veya geçersiz ingestion girdisi güvenli `400`
      cevabı üretiyor.
    - Incoming request ID varsayılan olarak güvenilmez; opt-in trusted modda
      yalnız bounded ve güvenli karakterli değerler kabul ediliyor.
    - CORS yalnız doğrulanmış explicit HTTP(S) origin, method ve header
      allowlistleriyle çalışıyor; wildcard ve credential-bearing originler
      reddediliyor.
    - API cevapları `no-store`, `nosniff`, `DENY` ve `no-referrer` headerlarını
      taşıyor.
    - Sonuç: 24 yeni API testi dahil tam backend paketi 549 test ve %86
      coverage ile başarılı; Ruff, 217 source dosyasında mypy ve wheel/sdist
      build kapıları yeşil.

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

Q0 durumu: **tamamlandı**.

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

Bir sonraki `devam et` komutunda Q1'in ilk dilimi uygulanacaktır: frontend için
typed analysis/comparison request-state altyapısı kurulacak, ardından summary,
timeline ve distribution sonuçları bounded ve erişilebilir görünümlerle
sunulacaktır. Backend analiz sözleşmesi değiştirilmeden kullanılacak; SQL veya
harici kalıcı veri tabanı eklenmeyecektir.
