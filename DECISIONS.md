# PaytarAI — Mimari Kararlar Logu (ADR)

Bu dosya proje boyunca verilen tüm önemli mimari ve teknik kararları kronolojik sırayla kaydeder.
Her karar bir bağlam, değerlendirilen alternatifler ve nihai gerekçe içerir.

---

## ADR-001: Auth Sistemi — Basit Rol Seçimi

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** Projenin iki farklı kullanıcı tipi (Veteriner Hekim / Üretici) var.
Her tip için farklı UI, farklı LLM prompt'u ve farklı erişim kontrolü gerekiyor.

**Karar:** Gerçek bir auth sistemi (NextAuth.js, JWT vb.) yerine basit bir rol seçim ekranı kullanılacak.
Landing page'de iki kart gösterilecek — kullanıcı tıklayarak rolünü seçecek, rol `localStorage` ve `AgentState`'e inject edilecek.

**Gerekçe:** Bu bir bitirme projesi / demo uygulaması. Gerçek kullanıcı yönetimi scope dışında.
Rol seçimi tüm sisteme (UI rendering, LLM prompt, Critic kuralları, retrieval filtreleri) propagate ediliyor —
auth katmanı olmadan da rol bazlı davranış farkı tam olarak gösterilebilir.

**Alternatifler:**
- NextAuth.js + Credential Provider → Gereksiz karmaşıklık, demo için overkill
- Basit username/password form → Aynı şekilde gereksiz, ek DB tablosu gerektirir

---

## ADR-002: Veritabanı — SQLite

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** Audit log, konuşma geçmişi ve manual review queue verilerinin saklanması gerekiyor.
Bu bir sürü takip sistemi değil, bir AI karar destek asistanı. Veri modeli basit.

**Karar:** SQLite kullanılacak. `paytar.db` dosyası backend root'unda oluşturulacak.

**Gerekçe:**
- Ek bir DB sunucusu gerekmez (Railway'de dosya sistemi yeterli)
- Audit log, session ve manual review queue için yeterli performans
- Zero-config — setup süresini minimuma indirir
- Production'a geçişte PostgreSQL'e migration kolay (SQLAlchemy ile)

**Alternatifler:**
- PostgreSQL → Ek servis maliyeti, bu aşamada gereksiz
- MongoDB → Veteriner verileri ilişkisel yapıda, document DB uygun değil

---

## ADR-003: Qdrant — Cloud Free Tier

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** Vektör veritabanı olarak Qdrant kullanılacak (AI-PROMPT.md zorunlu kılıyor).
Deployment kolaylığı ve sıfır altyapı yönetimi için cloud seçildi.

**Karar:** cloud.qdrant.io üzerinden free tier cluster oluşturulacak. URL ve API key `.env`'e eklenecek.

**Gerekçe:**
- Free tier 1GB storage — başlangıç doküman seti için yeterli
- Managed servis — Docker container yönetimi gereksiz
- Rust-based payload filtering — ilaç ismi disambiguation için kritik
- Production-ready — demo'dan sonra ölçeklendirilebilir

---

## ADR-004: Llama 3.3 70B Provider — Groq

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** State compression ve summarization görevleri için düşük maliyetli bir LLM gerekiyor.
AI-PROMPT.md Claude Haiku veya Llama 3.3 70B Instruct önerir.

**Karar:** Groq API üzerinden Llama 3.3 70B Instruct kullanılacak.

**Gerekçe:**
- Groq'un LPU inference engine'i ile çok düşük latency (~200ms)
- Ücretsiz tier mevcut (rate-limited ama summarization için yeterli)
- Llama 3.3 70B, Türkçe text summarization'da iyi performans gösterir

**Alternatifler:**
- Claude Haiku → Ek Anthropic maliyet, Groq daha hızlı
- Together AI → Benzer, ama Groq'un latency avantajı belirleyici
- Fireworks AI → Destekleniyor ama Groq tercih edildi

---

## ADR-005: Deploy — Vercel (Frontend) + Railway (Backend)

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** Frontend ve backend ayrı platformlarda deploy edilecek.

**Karar:**
- Frontend (Next.js): Vercel — native Next.js desteği, zero-config deploy
- Backend (FastAPI): Railway — persistent container, SQLite dosya sistemi desteği

**Gerekçe:**
- Vercel, Next.js'in yapımcısı — edge functions, image optimization, ISR native
- Railway, Python backend için ideal — Docker container, persistent filesystem (SQLite için)
- Her iki platform da ücretsiz tier sunuyor
- CI/CD GitHub entegrasyonu her ikisinde de otomatik

---

## ADR-006: Semantic Chunking Stratejisi

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** AI-PROMPT.md, generic RecursiveCharacterTextSplitter kullanılmasını açıkça yasaklıyor.
Tıbbi bağlamda rastgele bölme, dozaj tablolarını kırarak tehlikeli omissions'a yol açabilir.

**Karar:** Sentence-level semantic chunking uygulanacak:
1. Metni cümlelere böl
2. Her cümlenin embedding'ini hesapla
3. Ardışık cümlelerin cosine similarity'sini ölç
4. Büyük benzerlik düşüşlerinde chunk sınırı koy
5. Hedef chunk boyutu: 1200-2500 token

**Gerekçe:** Dozaj tabloları, kontrendikasyon listeleri ve klinik referanslar
semantik bütünlük içinde kalmalı. Tablo yapıları daha büyük chunk'larda tutulabilir.

---

## ADR-007: AssemblyAI Kaldirildi — Whisper-Only STT + Kullanici Duzenleme

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Baglam:** AI-PROMPT.md'de Whisper primary + AssemblyAI Medical Mode fallback mimarisi tanimlanmisti.
Ancak AssemblyAI ek bir API key, ek maliyet ve ek karmasiklik getiriyordu.

**Karar:**
- AssemblyAI entegrasyonu tamamen kaldirildi
- Ses transkripsiyonu yalnizca Whisper Large V3 ile yapilacak
- Whisper transkripti otomatik gonderilmeyecek — chat input alanina dusecek
- Kullanici transkripti gorup duzenledikten sonra gonder butonuna basacak

**Gerekcesi:**
- Ek provider gereksiz karmasiklik ve maliyet
- Kullanicinin transkripti gondermeden once duzenleyebilmesi, hatali ilac isimlerini manual duzeltme imkani verir
- Bu yaklasim AssemblyAI fallback'inden daha guvenilir — insan dogrulama her zaman AI fallback'inden iyidir

**Kaldirilan dosyalar/satirlar:**
- `pyproject.toml`: `assemblyai>=0.33.0` dependency
- `config.py`: `assemblyai_api_key` field
- `.env.example`: `ASSEMBLYAI_API_KEY` satiri
- `voice.py`: AssemblyAI referanslari

---

## ADR-008: STT Provider — OpenAI Whisper (Groq'a Gecis Opsiyonu)

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Baglam:** Sesli komut transkripsiyonu icin STT provider secimi gerekiyordu.

**Karar:**
- Baslangicta OpenAI Whisper Large V3 kullanilacak
- Ileride Groq'a gecis opsiyonu acik tutulacak (Groq ucretsiz Whisper sunuyor)
- Embedding her durumda OpenAI'da kalacak (text-embedding-3-small)

**Gerekcesi:**
- OpenAI Whisper zaten bagimlilikta var (embedding icin OpenAI client kullaniliyor)
- Groq'un ucretsiz Whisper tier'i daha sonra maliyet optimizasyonu icin degerlendirilecek
- Embedding modeli degistirmek tum vektorlerin yeniden olusturulmasini gerektirir, bu yuzden sabit kalacak

---

## ADR-009: Dual Language Search — Cift Dil Arama

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Baglam:** Veteriner kaynaklar hem Ingilizce (Rebhun's vb.) hem Turkce olabilir.
Turkce sorgu ile Ingilizce kaynak arasinda embedding similarity dusuyor (0.46 vs 0.65+).
Bu dusuk skor yanlisilkla "Dusuk Guven" olarak yansiyordu.

**Karar:**
- Retriever node'da "dual query" stratejisi uygulanacak
- Kullanici sorusu Groq/Llama ile diger dile cevrilecek (ucretsiz)
- Hem orijinal hem cevrilmis sorgu ile Qdrant'ta arama yapilacak
- Sonuclar skor bazinda birlestirilecek
- Chunk metadata'sina `language` field'i eklendi

**Gerekcesi:**
- Groq ucretsiz oldugu icin ek maliyet yok
- Her iki dildeki kaynaklar da yuksek skorla bulunabilir
- Turkce kaynak eklendiginde sistem otomatik olarak onu da kullanir

**Dosya(lar):**
- `backend/app/rag/query_translator.py` (YENI)
- `backend/app/graph/nodes/retriever.py` (guncellendi)
- `backend/app/rag/pipeline.py` (language metadata eklendi)

---

## ADR-010: Generator LLM — Claude Sonnet 4 → Groq Llama 3.3 70B

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** Generator node Claude Sonnet 4 kullanıyordu. Birkaç test sorguda bile ~$0.50 harcandı.
Critic retry'lar maliyeti 3x artırıyordu (her red = yeni Claude çağrısı).

**Karar:**
- Generator tamamen Groq Llama 3.3 70B'ye taşındı
- Claude Sonnet 4 hiçbir node'da kullanılmıyor
- Tüm LLM çağrıları (compress, translate, generate) Groq üzerinden

**Gerekçe:**
- $0 maliyet (Groq ücretsiz tier)
- Generator zaten kaynak metni formatlamak için kullanılıyor — yaratıcı düşünce gerektirmiyor
- Groq latency avantajı (~3sn vs ~8sn)
- Dezavantaj: 100K token/gün limiti (günde ~20 sorgu, retry olmadan)

**Dosya(lar):** `backend/app/graph/nodes/generator.py`

---

## ADR-011: Pipeline Text Cleanup — Görsel Placeholder Temizleme

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** Docling PDF parse sonucunda `<!-- image -->` placeholder'ları metinde kalıyordu.
Bu placeholder'lar chunk'larda gereksiz yer kaplıyor ve embedding kalitesini düşürüyordu.
20 chunk'tan 6'sında toplam 13 adet görsel placeholder tespit edildi.

**Karar:**
- Pipeline'a chunking öncesi `_clean_parsed_text()` adımı eklendi
- `<!-- image -->` tagları siliniyor
- Boş markdown linkleri (`[]()`) temizleniyor
- 3+ ardışık boş satır 2'ye düşürülüyor

**Gerekçe:**
- Docling görsellerin OCR'ını yapamıyor (RapidOCR Çince optimize)
- Görsellerin alt yazıları/açıklamaları zaten metin olarak mevcut — bilgi kaybı yok
- İleride vision model ile görsel açıklaması eklenebilir (GPT-4V vb.)

**Dosya(lar):** `backend/app/rag/pipeline.py`

---

## ADR-012: Critic Hallucination Check — Toleranslı Sayısal Karşılaştırma

**Tarih:** 2026-05-10
**Durum:** Kabul Edildi

**Bağlam:** Critic'in halüsinasyon kontrolü sayısal değerleri birebir regex eşleşmesiyle karşılaştırıyordu.
Format farkları (ör. kaynak "500-mL" vs yanıt "500 ml") sahte alarm üretiyordu.
Her sorguda 2 gereksiz red → 3x LLM çağrısı → maliyet ve süre artışı.

**Karar:**
- Regex tabanlı birebir eşleşme yerine normalize edilmiş sayısal karşılaştırma
- Sayılar birimlerinden bağımsız olarak çıkarılıyor
- %10 tolerans ile eşleşme aranıyor
- 3'ten fazla doğrulanamayan sayı varsa red
- Fallback yanıtları (LLM hatası/rate limit) critic'ten muaf tutuldu

**Gerekçe:**
- Gerçek hataları (22→220 mg/kg) yakalıyor
- Format farklarını yok sayıyor
- Fallback durumunda sonsuz retry döngüsünü engelliyor

**Dosya(lar):** `backend/app/graph/nodes/critic.py`

---

_Bu dosya proje boyunca güncellenir. Yeni kararlar kronolojik sırayla eklenir._
