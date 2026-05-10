# PaytarAI — Geliştirici Onboarding Yönergesi

> Bu doküman, projeye sıfırdan dahil olan bir geliştiricinin adım adım okuması ve
> sistemi tam olarak anlaması için hazırlanmıştır.

---

## 1. Proje Nedir?

**PaytarAI**, büyükbaş hayvan sağlığına özel bir **Veteriner Karar Destek Asistanı**dır.
Bu bir chatbot DEĞİLDİR — güvenlik, izlenebilirlik ve kanıta dayalı yanıt üretimi ön plandadır.

### İki Kullanıcı Rolü

| Rol | Açıklama | UI | LLM Çıktısı |
|-----|----------|----|-------------|
| **Veteriner Hekim** | Lisanslı profesyonel | 3-panel workspace, boş chat | Teknik: Latince terimler, mg/kg dozaj, kaynak citasyonu |
| **Üretici (Çiftçi)** | Tıp bilgisi olmayan çiftçi | 2-panel, semptom rehberi | Sade Türkçe, reçeteli ilaç yok, her yanıtta disclaimer |

### Temel Mimari Prensipler

1. **Halüsinasyon minimizasyonu** — Generator-Critic döngüsü
2. **Deterministik hesaplama** — LLM asla matematik yapmaz, Decimal modülü
3. **Kanıt zorunluluğu** — Her yanıt retrieval ile desteklenmeli
4. **Rol bazlı erişim** — Üretici reçeteli ilaç bilgisine erişemez

---

## 2. Teknoloji Stack'i

| Katman | Teknoloji | Amaç |
|--------|-----------|------|
| Backend | FastAPI (Python) | API, AI işleme, ses |
| AI Orchestration | LangGraph | Multi-agent workflow, state yönetimi |
| Retrieval | LlamaIndex + Qdrant | RAG pipeline, hybrid search |
| Primary LLM | Claude Sonnet (Anthropic) | Reasoning, tool calling, critic |
| Secondary LLM | Llama 3.3 70B (Groq) | Summarization, state compression |
| Embeddings | OpenAI text-embedding-3-small | Vektör oluşturma |
| Vector DB | Qdrant Cloud | Hybrid search (dense + sparse) |
| PDF Parsing | Docling + TableFormer | Veteriner doküman işleme |
| Frontend | Next.js 14 (App Router) | UI framework |
| UI Components | Shadcn/UI + Radix UI | Component library |
| Styling | Tailwind CSS | CSS framework |
| Generative UI | Vercel AI SDK | Tool rendering, streaming |
| STT | OpenAI Whisper Large V3 | Sesli komut (transkript input'a duser, kullanici duzenler) |
| TTS | Vercel AI SDK Voice | Yanit sesli okuma |
| Database | SQLite | Audit log, session |
| Deploy | Vercel + Railway | Frontend + Backend |

---

## 3. Proje Yapısı

```
Bitirme_PaytarAI/
├── AI-PROMPT.md            ← Orijinal gereksinim dökümanı (DOKUNMAYIN)
├── DECISIONS.md            ← Mimari kararlar logu
├── ERRORS.md               ← Hata takip logu
├── YONERGE.md              ← Bu dosya
├── docker-compose.yml
├── .env.example            ← Env template (keyleri .env'e kopyalayın)
│
├── backend/                ← Python FastAPI uygulaması
│   ├── app/
│   │   ├── main.py         ← FastAPI entry point
│   │   ├── config.py       ← Pydantic Settings
│   │   ├── api/v1/         ← REST endpoints (chat, voice, ingest, health)
│   │   ├── graph/          ← LangGraph workflow
│   │   │   ├── state.py    ← AgentState tanımı
│   │   │   ├── nodes/      ← Compress, Generator, Retriever, Dosage, Critic, Confidence
│   │   │   ├── prompts.py  ← Rol bazlı sistem promptları
│   │   │   ├── workflow.py ← Graph derleme
│   │   │   └── audit.py    ← Audit log
│   │   ├── rag/            ← RAG pipeline (ingestion, chunking, validation, embeddings, qdrant)
│   │   ├── tools/          ← Deterministik araçlar (dosage_calculator, drug_lookup)
│   │   ├── voice/          ← Ses isleme (whisper)
│   │   └── models/         ← Pydantic data models
│   ├── data/documents/     ← Veteriner PDF'leri (gitignore'da)
│   ├── tests/              ← Pytest test suite
│   └── pyproject.toml
│
└── frontend/               ← Next.js 14 uygulaması
    ├── src/
    │   ├── app/            ← App Router sayfaları
    │   │   ├── page.tsx    ← Rol seçim ekranı
    │   │   ├── vet/        ← Veteriner dashboard
    │   │   └── producer/   ← Üretici dashboard
    │   ├── components/     ← UI bileşenleri
    │   │   ├── chat/       ← ChatInput, ChatMessage, VoiceInput
    │   │   ├── cards/      ← DosageCard, ProducerCard, ErrorBoundary
    │   │   ├── symptom/    ← SymptomGuide, SymptomDetailStep
    │   │   └── layout/     ← VetWorkspace, ProducerWorkspace
    │   ├── hooks/          ← Custom React hooks
    │   ├── lib/            ← API client, constants
    │   └── types/          ← TypeScript type definitions
    └── tailwind.config.ts  ← Design tokens
```

---

## 4. İlk Kurulum (Adım Adım)

### 4.1 Ön Gereksinimler

- **Python 3.10+**
- **Node.js 20+** ve **npm**
- **Git**

### 4.2 Repo'yu Klonlayın

```bash
git clone https://github.com/[username]/Bitirme_PaytarAI.git
cd Bitirme_PaytarAI
```

### 4.3 Environment Variables

```bash
cp .env.example .env
# .env dosyasini acin ve asagidaki keyleri doldurun:
# - ANTHROPIC_API_KEY
# - OPENAI_API_KEY
# - GROQ_API_KEY
# - QDRANT_URL
# - QDRANT_API_KEY
```

### 4.4 Backend Kurulumu

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -e ".[dev]"
```

### 4.5 Frontend Kurulumu

```bash
cd frontend
npm install
```

### 4.6 Çalıştırma

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Tarayıcıda `http://localhost:3000` adresine gidin.

---

## 5. LangGraph Workflow Akışı

```
Kullanıcı Mesajı
      │
      ▼
┌─────────────┐
│  Compress   │  ← State çok büyükse Llama 3.3 ile özetle
└──────┬──────┘
       ▼
┌─────────────┐
│  Generator  │  ← Claude Sonnet, rol bazlı prompt, tool calling
└──────┬──────┘
       ▼
┌─────────────┐
│  Retriever  │  ← Qdrant hybrid search + drug disambiguation
└──────┬──────┘
       ▼
┌─────────────┐
│   Dosage    │  ← Deterministik Decimal hesaplama (opsiyonel)
└──────┬──────┘
       ▼
┌─────────────┐
│   Critic    │  ← Triplet match, format, citation, rol kontrolü
└──────┬──────┘
       │
       ├── OK → Confidence Score → Final Response
       │
       └── REJECT (max 2) → Generator'a geri dön
                             3. red → Güvenli fallback
```

---

## 6. Kritik Kurallar (Geliştirici İçin)

1. **LLM asla matematik yapmaz** — Dozaj hesabı `Decimal` ile `dosage_calculator.py`'da yapılır
2. **`float` kullanmayın** — Tıbbi bağlamda `Decimal` zorunludur
3. **Her node'da `_audit_log()` çağrısı zorunludur**
4. **Üretici rolünde `prescription_required=True` olan dokümanlar retrieval'dan filtrelenir**
5. **Critic max 2 kez reddedebilir** — Sonsuz döngü yasaktır
6. **Docling parse sonrası validation zorunludur** — İlk 50 tablo manuel onaylanmalıdır
7. **Kaynak atıf her yanıtta zorunludur** — "Kaynak: [Kitap Adı], Sayfa [X]"
8. **AI-PROMPT.md dosyasına dokunmayın** — Bu orijinal gereksinim dokümanıdır

---

## 7. Test

```bash
cd backend
pytest tests/ -v
```

### Adversarial İlaç İsmi Test Seti
- Cefazolin ↔ Cefpodoxime
- Oxytetracycline ↔ Tetracycline
- Dexamethasone ↔ Betamethasone
- Penicillin G ↔ Ampicillin
- Flunixin ↔ Meloxicam

---

## 8. Deploy

| Servis | Platform | Komut |
|--------|----------|-------|
| Frontend | Vercel | GitHub repo bağla → otomatik deploy |
| Backend | Railway | GitHub repo bağla → Dockerfile ile deploy |
| Vector DB | Qdrant Cloud | cloud.qdrant.io → Free tier cluster |

---

## 9. İlgili Dokümanlar

| Dosya | İçerik |
|-------|--------|
| `AI-PROMPT.md` | Orijinal proje gereksinimleri (710 satır) |
| `DECISIONS.md` | Mimari kararlar logu |
| `ERRORS.md` | Hata ve çözüm logu |
| `docs/api-reference.md` | API endpoint dokümanı |
| `docs/architecture.md` | Mimari diyagram |

---

_Bu dosya proje boyunca güncellenir._
