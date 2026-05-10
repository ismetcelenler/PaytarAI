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

_Bu dosya proje boyunca güncellenir. Yeni kararlar kronolojik sırayla eklenir._
