---
name: medical-rag-roadmap
description: PaytarAI'in mevcut durumunu ve uretim-validated medical RAG upgrade'lerini ROI sirali listeler. Use when planning system improvements, when user asks "what's next?", when latency or accuracy plateaus, or when deciding what to invest in.
user-invocable: true
allowed-tools: Bash Read
---

# PaytarAI Upgrade Roadmap — ROI sirali

Bu skill, **"simdi ne yapsam?"** sorusuna her zaman cevap verir. Asagidaki sira **uretim ortamlari** (OpenEvidence, Hippocratic AI, Glass Health, JMIR 2025-2026 calismalari) tarafindan dogrulanmis pratiklerden.

---

## Mevcut durum

Son baseline raporu:

!`ls -t backend/eval/reports/*.md 2>/dev/null | head -1`

Detaylar:

!`grep -E "Avg|Fact coverage|Forbidden|Retrieval" $(ls -t backend/eval/reports/*.md 2>/dev/null | head -1) 2>/dev/null | head -10`

**Stack:**
- Embedder: text-embedding-3-small (OpenAI, 1536-dim)
- LLM (generator + enrich): gpt-oss-120b @ Cerebras (medium reasoning)
- LLM (judge): gpt-4o-mini @ OpenAI
- Vector DB: Qdrant (~22K chunk, parent-child)
- No reranker, no CRAG, no Faith-Judge

---

## Faz 0 — Hızlı kazanım, LLM yok (kod degisikligi)

**Maliyet:** 30 dakika kod + eval
**Kazanc beklentisi:** forbidden_pass 0.92 → 0.99

### 0a. Scope detector
- Sorguda cross-species kelime (kedi/kopek/kus/at/koyun/keci) → retrieval atla, template don
- Implementasyon: retriever.py basinda kontrol
- Bu, mevcut **O1 (kus)** halusinasyonu kalici cozer

### 0b. Confidence threshold gate
- `top_score < 0.45` ise generator yanitini kullanma
- Confidence node template fallback verir
- Bu, mevcut **O2 (Holstein)** uydurma sorununu cozer

**Onceki olcum:**
- O1 (baseline): uydurma kus tedavisi
- O1 (tiered_v1): "bilmiyorum" — prompt zaten cozdu!
- O2 (tiered_v1): forbidden FAIL ("yuksek sut verimi")
- Faz 0 ile O2 da temizlenir

---

## Faz 1 — BGE-M3 multilingual embedder

**Maliyet:** Eve git + GPU + 6 saat (CPU) ya da 30 dakika (GPU) reindex
**Kazanc beklentisi:** retrieval 0.83 → 0.91 (+%10)

### Niye
- text-embedding-3-small TR↔EN cross-lingual'da zayif (top_sim ~0.55-0.65)
- BGE-M3 MIRACL Turkish benchmark'inda guclu
- Hibrit (dense + sparse + colbert) tek modelde — ucretsiz, Apache-2.0

### Adimlar
1. `pip install -U FlagEmbedding` (ya da langchain-huggingface)
2. `backend/app/rag/embeddings.py` → BGE-M3'e cevir
3. Qdrant collection sema guncelle (dimension 1536 → 1024)
4. Tum chunk'lari reindex et (eve git, GPU'da hizli)
5. Eval koştur, retrieval delta'sini karsilastir

### Risk
- Reindex sirasinda sistem askida kalir
- Yeni embedder eski sorgu vektorleriyle uyumsuz → cache temizle

---

## Faz 2 — Reranker (BGE-Reranker-v2-m3)

**Maliyet:** 2-3 saat kod + eval. Inference: +1-2s/sorgu.
**Kazanc beklentisi:** retrieval_precision +%15-40

### Niye
- Retriever top-50 chunk getirir ama bazilari yanlis
- Cross-encoder reranker top-50 → top-5'i ince ayar
- Multilingual, ucretsiz

### Adimlar
1. `pip install FlagEmbedding`
2. `retriever.py`'ye reranker stage ekle:
   - Dense retrieve top-50
   - Reranker score → resort
   - Top-5/8'i generator'a gonder
3. Eval — retrieval ve fact_coverage'a bak

### Bagimlilik
- Once Faz 1 (BGE-M3) yapilmali — ayni model ailesi, optimum eslesir

---

## Faz 3 — Karar verme: CRAG mi HyDE mi?

Bu **ya/ya da** secimi, ikisi birden gereksizdir.

### Faz 3a. CRAG (Corrective RAG)
**Ne zaman:** Eger Faz 1+2 sonrasi **yanlis chunk** problemi devam ediyorsa
**Maliyet:** Her sorguda +1 LLM cagrisi, ~+3-5s latency
**Implementasyon:** Yeni `crag_judge` node — retriever'dan sonra, generator'dan once

### Faz 3b. HyDE (Hypothetical Document Embedding)
**Ne zaman:** Eger Faz 1+2 sonrasi **cross-lingual gap** devam ediyorsa
**Maliyet:** Her sorguda +1 LLM cagrisi (kucuk model), ~+2-3s latency
**Implementasyon:** Generator yerine kucuk LLM ile EN cevap uret → onu embed et → ara

**Tahmin:** BGE-M3 cross-lingual'i halletse de HyDE'ye gerek kalmayabilir. CRAG ihtiyaci daha olasi.

---

## Faz 4 — Faith-Judge (claim-level validation)

**Maliyet:** Her sorguda N ekstra LLM cagrisi (N = atomik iddia sayisi), +5-10s
**Kazanc:** faithfulness 0.83 → 0.95
**Ne zaman:** Eval'de "fact_coverage iyi ama yanitta hala uydurma cumle var" durumu

**Implementasyon yeri:** Critic node icinde yeni adim, ya da ayri post-validator

---

## Faz 5+ — Opsiyonel/ileri seviye

| Teknik | Ne zaman | Riski |
|---|---|---|
| **Citation enforcement** ([src:N]) | Faith-Judge yetmiyorsa | LLM uyum %30-50 |
| **NeMo Guardrails** | Production scale'e cikarken | Mevcut critic'le cakisir |
| **MedCPT parallel index** | Sadece EN biomedical sorgu icin | Cross-lingual'da BGE-M3 yeterli |
| **Yeni ilaç/yönetim kaynagi ekle** | İrk/rasyon/besi soruları icin | Ingestion + chunking + eval |

---

## Su an icin tavsiyem

Mevcut metrik durumuna bak. Su sirayla git:

1. **Faz 0** (30 dk) — En kolay, en yuksek garanti kazanc
2. **Faz 1** (eve git) — BGE-M3 reindex
3. **Faz 2** (yarim gun) — Reranker
4. **Eval ile durum tespit** — Hala sorun varsa Faz 3a (CRAG)
5. **Hala sorun varsa** — Faz 4 (Faith-Judge)

Faz 4'un otesine **muhtemelen ihtiyacin olmayacak**. 0.95 faithfulness uretim seviyesi.

---

## Onemli notlar

- **Her faz sonrasi eval koştur** ve `rag-change-guard` skill'inin checklist'ini uygula
- **Bir faz birden fazla degisiklik icermesin** — bir embedder degisikligi + bir reranker + bir prompt degisikligi ayni anda yapilirsa hangisi neyi degistirdi anlasilmaz
- **Latency budget belirle:** Su an 30s. Faz 1+2 sonrasi 35s civari kalir. Faz 3+4 ile 45-60s'ye cikar — kullanici icin sinirda
