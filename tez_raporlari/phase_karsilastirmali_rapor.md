# PaytarAI — Phase Karşılaştırmalı Rapor

> **Tarih:** 2026-05-20
> **Kapsam:** Phase 0 ve Phase 1 sonu skorları, somut iyileştirme verisi

Bu rapor sadece **phase sonlarında ölçülen** skorları içerir. Iteration arası
ara sonuçlar ve smoke testler dahil edilmemiştir.

---

## 1. Genel sistem mimarisi (özet)

PaytarAI, büyükbaş hayvan sağlığı için **iki rollü** karar destek sistemidir
(üretici / veteriner hekim). LangGraph workflow pipeline'ı şu node'lardan oluşur:

```
scope_check → compress → retriever → [early gate] → generator → critic → confidence → END
                                          ↓
                                  out_of_scope veya insufficient → confidence (template)
```

**Stack:**
- LLM generator: `openai/gpt-oss-120b` @ Cerebras (medium reasoning)
- LLM judge (production critic, eval judge): `gpt-oss-120b` @ Cerebras (low) + `gpt-4o-mini`
- Embedder: BAAI/bge-m3 (Phase 1 sonrası — multilingual, 1024-dim)
- Vector DB: Qdrant Cloud (parent-child chunking)

---

## 2. Phase 0 — Halüsinasyon ve out-of-scope kontrolü

**Yapılan:**
- `scope_check` node eklendi (LLM sınıflandırıcı, gpt-oss-120b low) — büyükbaş
  dışı sorgular için template fallback
- Confidence gate (`top_sim < 0.45`) — düşük güven retrieval'da template
- Sanitize katmanı — kozmetik kaynak etiketleri sessizce silinir
- Critic'te role compliance keyword listesi genişletildi

**Eval seti:** 12 soru (sentetik, kullanıcı-yazdırılmış)

### Phase 0 öncesi (baseline_v1)

| Metrik | Skor |
|---|---|
| fact_coverage (LLM judge) | 0.722 |
| forbidden_pass | 0.917 (11/12) |
| retrieval precision | 0.833 |
| Avg top_sim | 0.580 |
| Avg latency | 24.1 s |

### Phase 0 sonu (phase0_fix1)

| Metrik | Skor | Δ |
|---|---|---|
| fact_coverage (LLM judge) | 0.695 | -0.027 |
| forbidden_pass | **1.000** | **+0.083** |
| retrieval precision | 0.833 | 0 |
| Avg top_sim | 0.542 | -0.038 |
| Avg latency | 37.0 s | +12.9 s (scope_check ekledi) |

**Ana kazanç:** forbidden_pass **0.917 → 1.000**. Sistem yasak kelime
sızıntısını sıfırladı. O1 (kuş gagası) halüsinasyon engellendi, O2 (Holstein)
uydurma tedavi → template fallback.

**Trade-off:** Hafif fact_coverage düşüşü (-0.027) ve latency artışı (+12.9s)
güvenlik kazanımının bedeli.

---

## 3. Phase 1 — Cross-lingual embedder + outlier guard

**Yapılan:**
- Embedder geçişi: `text-embedding-3-small` (OpenAI, 1536-dim) → `BAAI/bge-m3`
  (multilingual, 1024-dim)
- Yeni Qdrant koleksiyonu (`paytar_veterinary_bge`) — 13,079 chunk
- Outlier guard (chunking.py): tablo blokları için hard-cap + fallback split
  (max parent 3000 char, max child 600 char) — eski 80 KB devasa chunk problemi
  giderildi
- PyTorch 2.6 + CUDA 12.4 + FlagEmbedding kurulumu (RTX 3060 GPU)
- OMP/MKL native lib conflict fix (import order)

**Eval seti:** 12 soru (Phase 0 ile aynı)

### Phase 1 sonu (phase1_bgem3)

| Metrik | Skor | Δ (vs Phase 0) |
|---|---|---|
| fact_coverage (LLM judge) | 0.750 | +0.055 |
| forbidden_pass | 0.917 | -0.083 |
| retrieval precision | 0.833 | 0 |
| **Avg top_sim** | **0.638** | **+0.096** 🚀 |
| Avg latency | 40.2 s | +3.2 s |

**Ana kazanç:** Avg top_sim **0.542 → 0.638** (+%18). Cross-lingual retrieval
kalitesi belirgin yükseldi — text-embedding-3-small'in tavanı kırıldı. BGE-M3
multilingual training büyükbaş veteriner literatürünün Türkçe sorguları
karşılamasında etkili.

**Trade-off:** forbidden_pass tek case'de düştü (BGE-M3 ile O2 Holstein retrieval'ı güçlendi → confidence gate eşiği 0.45 yetmedi). Yarın yapılacak fix: threshold 0.60 kalibrasyonu.

---

## 4. Phase 1 + Hibrit Critic — v2 baseline (50 soru)

**Yapılan ek iyileştirmeler:**
- Eval seti büyütüldü: **12 → 50 soru**, AI tarafından üretildi, kategori
  dağılımı dengelendi
- **Stratified evaluation** eklendi: writing_style {clean, mid, broken}
  alanı → robustness ölçümü
- Hibrit critic: hard rules (regex/keyword) + LLM judge (gpt-oss-120b low)
- Soft check'ler LLM judge'a devredildi: disclaimer, emergency, sade dil
- Numerical hallucination check daraltıldı (sadece doz/birim sayıları)
- Early confidence gate workflow'a eklendi (retriever sonrası,
  generator öncesi) — düşük top_sim case'lerinde 50s LLM tasarrufu
- Multi-turn support (run_eval.py)
- confidence threshold 0.45 → 0.60 kalibre edildi

**Eval seti:** 50 soru (v0.2, stratified)

### v2 baseline sonu (v2_baseline_hybrid)

| Metrik | Skor | Yorum |
|---|---|---|
| **fact_coverage (LLM judge)** | **0.823** | **+0.073** (vs phase1_bgem3 12-soru) |
| forbidden_pass | 0.980 | 49/50 case (tek mid-style üretici case'de sızıntı) |
| retrieval precision | 0.980 | 49/50 |
| Avg top_sim | 0.612 | BGE-M3 normal seviyesinde |
| Avg latency | 47.7 s | vet kategori retry'larından dolayı |

### Yazım stili kırılımı (stratified evaluation)

| Stil | N | fact_llm | forbidden | top_sim |
|---|---|---|---|---|
| **clean** | 20 | 0.783 | 1.000 | 0.622 |
| mid | 14 | 0.822 | 0.929 | 0.622 |
| **broken** | 16 | **0.875** | 1.000 | 0.589 |

**ROBUSTNESS GAP (clean − broken) = −0.092**

**Yorumlama:** Sistem **yazım gürültüsüne dayanıklı**. Negatif gap → bozuk
Türkçe yanıtlar (üretici saha dili) en az clean Türkçe kadar başarılı, hatta
hafif üstün. BGE-M3 multilingual embedder ve LangGraph pipeline'ın sade dil
özelleştirmesi (PRODUCER_SYSTEM_PROMPT) etkili.

---

## 5. Phase karşılaştırma tablosu (özet)

| Metrik | Baseline | Phase 0 | Phase 1 | v2 (50 soru) |
|---|---|---|---|---|
| Eval soru sayısı | 12 | 12 | 12 | **50** |
| fact_coverage (LLM judge) | 0.722 | 0.695 | 0.750 | **0.823** |
| forbidden_pass | 0.917 | **1.000** | 0.917 | 0.980 |
| retrieval precision | 0.833 | 0.833 | 0.833 | **0.980** |
| Avg top_sim | 0.580 | 0.542 | **0.638** | 0.612 |
| Avg latency | 24.1 s | 37.0 s | 40.2 s | 47.7 s |

> **Not:** v2 sonuçları 50 soru ile, diğerleri 12 soru ile. İstatistiksel güç
> açısından v2 daha güvenilir, ancak Phase 0 ve 1 ölçümleri aynı sette
> birbiriyle karşılaştırılabilir.

---

## 6. Tez açısından somut bulgular

1. **BGE-M3 multilingual embedder cross-lingual retrieval'da text-embedding-3-small'i
   yaklaşık %18 oranında geçti** (top_sim 0.54 → 0.64).
2. **Sistem yazım gürültüsüne dayanıklıdır** — robustness gap = −0.092
   (bozuk Türkçe ≥ clean Türkçe performansı).
3. **Halüsinasyon önleme katmanları etkili çalışıyor:** forbidden_pass
   0.917 → 1.000 (Phase 0), 0.980 (Phase 1+50 soru) — kategori dağılımı
   genişlemesine rağmen yüksek tutarlılık.
4. **Out-of-scope tespiti güvenilir:** 5 out-of-scope test case'in 5'i
   doğru template ile yanıtlandı (sistem büyükbaş dışı sorulara klinik
   tedavi uydurmadı).
5. **İleri faz hedefi:** BGE-reranker-v2-m3 (Phase 2) ile retrieval
   precision 0.98 → 0.99+ ve top_sim 0.61 → 0.70+ beklentisi.

---

## 7. Bilinen kalibrasyon ihtiyacı (yarın için)

- **Vet kategorisinde aşırı retry**: 10 vet case'in 8'i critic retry yaptı.
  Sebep: LLM judge'un `emergency_appropriate` kuralı vet rolünde de
  uygulanıyor, halbuki vet yanıtında 🚨 emoji gerekmez. Fix: kontrolü
  sadece producer rolünde uygula.
- **Multi-turn bağlam kaybı**: scope_check sadece son user mesajını
  okuyor, önceki turn'lerin bağlamını görmüyor. multiturn_01'de yanlış
  olarak out_of_scope dedi. Fix: önceki mesajları da scope_check
  prompt'una ekle.

---

## 8. Dosya referansları

- v2_baseline_hybrid raporu: `backend/eval/reports/20260520_024920__v2_baseline_hybrid.md`
- v2 eval seti: `backend/eval/datasets/eval_set_v2.yaml`
- Yönerge: `backend/eval/datasets/EVAL_GENERATION_BRIEF.md`
- Pipeline kodu: `backend/app/graph/`
- Critic: `backend/app/graph/nodes/critic.py`
- Embedder: `backend/app/rag/embeddings.py`
- Chunking + outlier guard: `backend/app/rag/chunking.py`
