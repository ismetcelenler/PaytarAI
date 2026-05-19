---
name: rag-change-guard
description: Use BEFORE and AFTER modifying any RAG pipeline file (graph nodes, prompts, retriever, query translator, ingestion, embedder config). Forces baseline comparison and 5-question planning to prevent silent regression.
when_to_use: Triggered when editing backend/app/graph/**, backend/app/rag/**, backend/app/api/v1/ingest.py, or backend/eval/datasets/eval_set.yaml. Also when planning to swap models or embedders.
allowed-tools: Bash Read Grep
---

# RAG Change Guard — Regression önleyici kontrol

Bu skill, sistemin **bozulup bozulup tekrar yapılmasını engellemek** için var. Her RAG değişikliği öncesi ve sonrası eval karşılaştırmasını **zorunlu** kılar.

## Tetiklendiği dosya/durumlar

- `backend/app/graph/nodes/*.py` (compress, retriever, generator, critic, confidence)
- `backend/app/graph/prompts.py`
- `backend/app/graph/workflow.py`
- `backend/app/rag/*.py` (embeddings, qdrant_store, query_translator)
- `backend/app/api/v1/ingest.py`
- `backend/eval/datasets/eval_set.yaml`
- LLM/embedder model değişikliği planı

## ZORUNLU iş akışı

### 1. DEĞİŞİKLİK ÖNCESİ — Mevcut durumu sabitle

Son baseline raporunu kontrol et:

!`ls -t backend/eval/reports/*.md 2>/dev/null | head -3`

Son raporun ozetini oku:

!`tail -1 $(ls -t backend/eval/reports/*.md 2>/dev/null | head -1) 2>/dev/null || echo "Henuz rapor yok"`

### 2. 5 SORULUK PLAN — Kullanıcıya cevapla

Kod yazmadan önce yanıtla:

1. **Ne değişiyor?** Hangi dosya, hangi node, hangi davranış? Net ifade et (file:line)
2. **Niye değişiyor?** Hangi gerçek probleme yanıt? Hangi eval skoru zayıf?
3. **Ne kırılabilir?** Hangi mevcut özellik etkilenir? Hangi eval case kategorisi risk altında?
4. **Nasıl doğrularım?** Hangi eval kategorisi (producer_natural, emergency, out_of_scope vs.) bu değişikliği test eder?
5. **Geri alabilir miyim?** Rollback planı — git revert mi, config flag mı?

Plan kullanıcı tarafından onaylanmadan kod yazma.

### 3. DEĞİŞİKLİKTEN SONRA — Eval ile doğrula

```bash
cd backend
python -m eval.run_eval --tag <degisikligi-anlatan-tag>
```

Yeni raporu son baseline ile karşılaştır:

| Metrik | Önce | Sonra | Δ |
|---|---|---|---|
| fact_coverage_llm | X | Y | ±Z |
| forbidden_pass | X | Y | ±Z |
| retrieval | X | Y | ±Z |
| top_sim | X | Y | ±Z |
| latency | X | Y | ±Z |

### 4. KARAR KURALI

- **forbidden_pass düşerse:** CRITICAL — değişikliği geri al, problem incele
- **fact_coverage_llm > %5 düşerse:** Kullanıcıyla konuş, kazanç-kayıp tart
- **latency 2x artarsa:** Optimize et veya geri al
- **Sadece top_sim biraz düştü ama fact_coverage_llm yükseldi:** OK, devam
- **Hiçbir metrik düşmedi, en az biri yükseldi:** Commit'e hazır

### 5. "BİTTİ" demeden önce kontrol listesi

- [ ] Eval koşuldu mu?
- [ ] Yeni rapor `eval/reports/`'ta var mı?
- [ ] Karşılaştırma tablosu kullanıcıya gösterildi mi?
- [ ] Regresyon varsa kullanıcı onayladı mı?

## Üst düzey ilkeler

- **Küçük değişiklik, hızlı doğrulama.** Bir dosyada 50 satır değişiklik → eval. Sonra başka dosyaya geç. Topluca yapma.
- **Eval sayısı sabit kalmalı.** Eval'i değiştirip sonra koşmak = kendi notunu vermek. Eğer eval set'ini de değiştirdiysen, önce eski set'le eski metriği al, sonra yeni set'le yeni metriği al, iki ayrı baseline kaydet.
- **Hatalı testlerin tekrar koşumu yasak.** Random varyans için 3 koşum yapıp en iyiyi alma; ilk koşum sayar.
