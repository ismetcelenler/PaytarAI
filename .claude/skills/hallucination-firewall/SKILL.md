---
name: hallucination-firewall
description: Hallucination prevention rules for medical RAG. Use when modifying generator/critic/confidence nodes, reviewing model outputs, or debugging cases where the system invents information. Based on OpenEvidence, CRAG, FACTSCORE production patterns.
when_to_use: Triggered when working on generator.py, critic.py, confidence.py, or when an eval case shows hallucination (fabricated drugs, doses, diagnoses, or species/scope violations).
allowed-tools: Read Grep
---

# Hallucination Firewall — Medical RAG kalibi

Medikal RAG'da yanlis bilgi = guvenlik riski. Bu skill, halusinasyonu **uretim ortamlari** (OpenEvidence, Hippocratic AI, Glass Health) seviyesinde onleme kurallari icerir.

---

## Rule 1 — Scope violation (cross-species)

**Durum:** Sorguda kedi/kopek/kus/at/koyun/keci/kanatli/balik geciyor

**Aksiyon:**
- Generator: Asla tedavi tarifi yazma
- Yanit zorunlu template: *"Bu konuda kesin bilgi veremem, lütfen ilgili uzmanına/veterinerinize danışın."*

**Implementasyon onerisi:**
```python
# retriever.py veya yeni scope_check.py
EXOTIC_SPECIES = ["kedi", "kopek", "kus", "at", "koyun", "keci",
                  "kanatli", "balik", "tavuk", "kuzu", "horoz",
                  "cat", "dog", "bird", "horse", "sheep", "goat"]

def is_out_of_scope(query: str) -> bool:
    return any(s in query.lower() for s in EXOTIC_SPECIES)
```

**Eval ile dogrula:** `out_of_scope` kategorisindeki sorularda `expect_retrieval_fail: true` + LLM-judge fact yakalamali.

---

## Rule 2 — Low confidence retrieval

**Durum:** `state["retrieval_similarity_score"] < 0.45`

**Aksiyon:**
- Confidence node: `evidence_confidence = "insufficient"` zorla
- Final_response'u template ile degistir, generator LLM yanitini kullanma
- Template: *"Bu konuda kaynaklarımda yeterli bilgi bulamadım, lütfen veterinerinize danışın."*

**Onemli:** Bu, mevcut O2 (Holstein) sorunumuzu cozer — kaynak yetersizken model uydurma yapiyor.

**Implementasyon yeri:** [confidence.py](backend/app/graph/nodes/confidence.py)

---

## Rule 3 — Numerical hallucination

**Durum:** Yanitta gecen sayisal degerler kaynaklarda yok

**Aksiyon (mevcut critic):** [critic.py:_check_hallucination](backend/app/graph/nodes/critic.py) zaten yapiyor
- Yanittan tum sayilari cikar
- Her sayi icin kaynaklarda %10 toleransla esleme ara
- 3'ten fazla eslesmeyen sayi varsa reddet

**Iyilestirme firsati:** Threshold (3) cok gevsek; **2'ye dusurulebilir** sonrasi eval gosterirse. Ama ucuncu sayi cok dusuk false positive verecektir, dikkatli ol.

---

## Rule 4 — Drug name hallucination

**Durum:** Yanit, kaynaklarda olmayan specific Rx ilac adi iceriyor

**Aksiyon (mevcut critic):** Producer modunda yasak prescription_markers listesi var. Vet modunda **yok** — eklenebilir:
```python
# Vet icin: yanit kaynaklarda olmayan ilac adi iceriyor mu?
def _check_drug_name_in_source(draft: str, docs: list[dict]) -> str | None:
    drug_patterns = ["penisil", "tetrasik", "amoksisil", "deksameta",
                     "flunixin", "meloksikem", "oksitosin", "seftiofur"]
    source_text = " ".join(d["text"] for d in docs).lower()
    for pat in drug_patterns:
        if pat in draft.lower() and pat not in source_text:
            return f"Yanitta '{pat}' geciyor ama kaynaklarda yok. Kaynaktan dogrulanmayan ilac onerme."
    return None
```

---

## Rule 5 — CRAG pattern (Corrective RAG)

**Durum:** Retrieval sonuc kalitesi belirsiz, yanlis chunk gelmis olabilir

**Aksiyon (yeni node — opsiyonel):**
1. Retriever sonuc dondur
2. **CRAG judge:** Kucuk LLM cagrisi: "Bu chunk'lar soruyla alakali mi? Tek kelime: relevant/irrelevant/ambiguous"
3. Eger `irrelevant` → query rewrite + tekrar dene, ya da template fallback
4. Eger `ambiguous` → top_score esiklerini dusur, daha cok chunk getir

**Maliyet:** Her sorguda 1 ekstra LLM cagrisi (~$0.001).

**NE ZAMAN ekle:** Eger BGE-M3 + reranker faz'larinda **hala** alakasiz chunk gelme problemi varsa.

---

## Rule 6 — Citation enforcement (advanced)

**OpenEvidence pattern:** Her klinik iddia kaynak chunk_id ile baglanmali

**Implementasyon (gelecek):**
1. Generator prompt'una ekle: "Her klinik bilgiden sonra [src:N] yaz"
2. Post-validator regex: `\[src:\d+\]` patterni ara
3. Cumlede iddia var ama atif yoksa → cumleyi sil veya reddet

**Dezavantaj:** gpt-oss-120b bu format icin egitilmedi, %30-50 uyumsuzluk olabilir. Once **claim decomposition** (Faith-Judge) dene.

---

## Rule 7 — Faith-Judge (claim decomposition)

**Durum:** Yanit dogru kavramlari iceriyor ama bazi cumleler hala uydurma olabilir

**Aksiyon (yeni metrik veya critic adimi):**
1. Yanit metnini atomik iddialar listesine ayir (LLM ile)
2. Her iddiayi kaynak chunk'lara karsi NLI (Natural Language Inference) ile dogrula
3. Reddedilen iddialari yanittan cikar veya tumden reddet

**Maliyet:** Her sorguda N+1 ekstra LLM cagrisi (N = iddia sayisi). ~$0.01-0.05/sorgu.

**NE ZAMAN ekle:** Eval'de **fact_coverage yuksek ama forbidden_pass dusuk** ise (yanit kapsami iyi ama detayda halusinasyon var).

---

## Karar matrisi — hangi rule'u ne zaman aktive et

| Sorun gosteren eval | Aktive et |
|---|---|
| Out-of-scope sorularda halusinasyon | Rule 1 (scope detector) — HEMEN |
| top_sim dusuk ama yanit veriyor | Rule 2 (confidence gate) — HEMEN |
| Vet yanitlarinda uydurma ilac adi | Rule 4 (drug name check) — ihtiyac varsa |
| Retrieval skoru iyi ama yanlis konu | Rule 5 (CRAG) — ihtiyac varsa |
| Spesifik cumlede halusinasyon | Rule 7 (Faith-Judge) — son care |

---

## Kacinilmasi gereken anti-pattern'ler

- **Birden cok katmanda ayni kontrol:** Critic + CRAG + confidence ucu de "low confidence → bilmiyorum" yapiyorsa kafalar karisir, biri yeter
- **Citation enforcement'a guvenip diger kontrolleri kapatma:** LLM uyumu %100 degil
- **NeMo Guardrails entegrasyonu:** Mevcut critic'le cakisir, buyuk framework yuku
- **Her sorguda Faith-Judge:** Pahali ve gereksiz, sadece flag'lenen sorularda calistir
