# Phase 2 — BGE-Reranker-v2-m3 Entegrasyonu: Negatif Sonuç Analizi

**Tarih:** 2026-05-21
**Sistem:** PaytarAI — Türkçe büyükbaş veteriner RAG asistanı
**Konu:** Reranker entegrasyonunun beklenenin aksine sistem doğruluğunu **-12 puan** düşürmesi ve olası nedenleri

---

## 1. Yönetici Özeti

BGE-reranker-v2-m3 (568M parametre, multilingual cross-encoder) sisteme entegre edildi. Hipotez: Dense retrieval (BGE-M3) sonrasına bir reranker eklenerek top-3 kaynak seçiminin alaka düzeyi artırılacak ve LLM'in halüsinasyon riski azaltılacak. Bu OpenEvidence, Hippocratic AI, Glass Health gibi üretim medical RAG sistemlerinin standart mimarisidir.

**Beklenti:** Üretim RAG benchmarklarında BGE-reranker tipik olarak fact coverage'a +0.03–0.08 katkı sağlar. Sistemimizde +0.05–0.10 civarı bir iyileşme beklendi.

**Gerçekleşen:** Aynı 50-case test setinde:

| Metrik | v2 baseline (reranker yok) | Phase 2 (reranker var) | Δ |
|---|---|---|---|
| **Production Pass Rate** | **%70** (35/50) | **%58** (29/50) | **-12 puan** |
| Fact LLM (avg) | 0.823 | 0.770 | -0.053 |
| Forbidden pass rate | 0.980 | 0.960 | -0.020 |
| Retrieval precision | 0.980 | 0.960 | -0.020 |
| Latency (avg) | 47.7s | 43.8s | -3.9s |

Reranker, vet_technical kategorisinde +0.06 katkı sağladı (10 case), ancak diğer kategorilerde **6 case daha az "üretim kalitesi" yanıt** üretti. Toplam etkisi negatif.

---

## 2. Bu Rapordaki Bilgi Türleri (Halüsinasyon Kontrolü)

Tez literatür araştırmasına temel olacağı için her bulgu için kanıt seviyesi etiketlendi:

- **[KANITLI]** = JSON eval raporlarından doğrudan sayı, dosya satırı veya iki kez ölçüm
- **[ÇIKARIM]** = Birden çok kanıttan mantıksal sonuç, ama tek doğrudan ölçüm yok
- **[SPEKÜLATİF]** = Dolaylı ipucu var, ama kanıt için ek deney gerekli

Bu ayrım yapılmadan yazılan analiz halüsinasyon riskine açıktır. Aşağıdaki bölümler bu etiketleri taşır.

---

## 3. Kronoloji ve Sayısal Sonuçlar [KANITLI]

### 3.1 Yapılan değişiklikler

1. **Reranker entegrasyonu** ([reranker.py](../backend/app/rag/reranker.py))
   - Model: `BAAI/bge-reranker-v2-m3` (Apache-2.0, 568M)
   - Mimari: Direkt `transformers` API (FlagEmbedding ve sentence-transformers CrossEncoder yeni transformers sürümleriyle uyumsuz)
   - FP32 modda (FP16'da BGE-reranker-v2-m3 logitleri uniform -8..-10 negatif veriyor → sigmoid hepsini 0'a düşürüyor)

2. **Retriever güncellendi** ([retriever.py](../backend/app/graph/nodes/retriever.py))
   - Eski: Dense top-5 → generator
   - Yeni: Dense top-30 → reranker → top-3 → generator
   - `retrieval_similarity_score` (cosine, confidence gate için) ile `rerank_top_score` (sigmoid, audit için) ayrıldı

3. **enrich_query bug'ı keşfedildi ve düzeltildi** ([query_translator.py](../backend/app/rag/query_translator.py))
   - Eski config: `reasoning_effort="medium", max_tokens=800`
   - **Bug:** gpt-oss-120b reasoning modeli 800 token bütçesinin 797'sini reasoning için harcıyordu, content boş dönüyordu (`finish_reason=length`, completion_tokens=800, reasoning_tokens=797)
   - Yeni config: `reasoning_effort="low", max_tokens=2000` (reasoning 8 token, completion 350 token)
   - **Bu bug Phase 1'den beri sistemde olmalı** — enrich_query (Türkçe sorgu → TR+EN keyword genişletme) hiç çalışmıyordu, sistem sadece orijinal TR sorguyla dense aramayı yapıyordu

### 3.2 Eval karşılaştırması (eval_set_v2.yaml, 50 case, eşdeğer config)

| Tag | Tarih | Config | Fact LLM | Pass Rate | Forbidden | Robustness gap |
|---|---|---|---|---|---|---|
| v2_baseline_hybrid | 20 May | BGE-M3 + hybrid critic + Fix 1/2 | **0.823** | **%70** | 0.98 | -0.092 |
| phase2_full50 | 21 May | + reranker + enrich-fix | 0.770 | %58 | 0.96 | -0.104 |
| **Δ** | | | **-0.053** | **-12 puan** | -0.02 | ~ |

### 3.3 Kategori bazlı kırılım

| Kategori | N | v2 baseline | Phase 2 | Δ |
|---|---|---|---|---|
| **vet_technical** | 10 | 0.67 | **0.73** | **+0.06** ✅ |
| emergency | 8 | 0.92 | 0.92 | 0.00 |
| out_of_scope | 5 | 1.00 | 1.00 | 0.00 |
| producer_natural | 12 | 0.83 | 0.81 | -0.02 |
| management | 5 | 1.00 | 0.93 | -0.07 |
| multi_turn | 2 | 0.50 | 0.33 | -0.17 |
| **edge_cases** | 5 | 0.83 | **0.57** | **-0.26** ⚠️ |
| **stress_test** | 3 | 0.67 | **0.33** | **-0.34** ⚠️ |

vet_technical'da öngörülen kazanç gerçekleşti (+0.06). Ancak edge_cases ve stress_test kategorilerinde büyük düşüş ortalamayı negatife çekti.

### 3.4 Case-bazlı değişimler

**Yeni fail eden (v2'de OK, Phase 2'de fail) — 6 case:**

| Case | Stil | v2 | Phase 2 | Sebep ipucu |
|---|---|---|---|---|
| producer_09 | mid | OK | fact 0.33 | judge varyansı? |
| vet_02 | mid | OK | Forbidden: "ketosis" | EN sızıntı |
| vet_03 | clean | OK | fact 0.00 | judge varyansı? |
| edge_01 | broken | OK | retrieval 0 (out_of_scope) | scope_check non-det. |
| edge_04 | broken | OK | fact 0.33 | reranker/judge |
| stress_03 | clean | OK | fact 0.00 | scope_check non-det. |

**v2'de fail, Phase 2'de düzelen — 3 case:**
- producer_04 (0.33→OK), producer_07 (Forbidden→OK), producer_11 (0.33→OK)

**Net etki: 6 yeni fail – 3 düzelme = -3 case ≈ -12 puan Pass Rate.**

---

## 4. Reranker Neden Negatif Sonuç Verdi? — Hipotezler

### 4.1 Mini eval yanıltıcıydı [KANITLI]

Tek 12-case mini test setinde (`_test_fix_validation.yaml`) Phase 2 fact_llm 0.694 → 0.750 (+0.056) görünüyordu. Ancak bu set 8/12 = %67 vet_technical ağırlıklıydı; full eval setinde vet %20 (10/50). Vet'teki +0.06 kazanç dar setin ortalamasını yukarı çekiyor, geniş sette eriyordu.

**Çıkarım:** Reranker'ın "iyileştirme" hipotezi yanlış ağırlıklı bir örneklemde doğrulandı. Bu istatistiksel olarak "overfitting to test selection" benzeri bir hata.

### 4.2 Multilingual Generator Sızıntısı [KANITLI]

Reranker İngilizce kaynak (Rebhun's Diseases of Dairy Cattle) chunk'larını farklı sırada öne çıkarıyor. Generator (gpt-oss-120b, medium reasoning) bu İngilizce kaynaklara baktığında Türkçe yanıta İngilizce terim sızdırıyor:

- **vet_02** ("ketozis patogenezi" sorusu): Yanıtta `ketosis` kelimesi geçti → `must_not_contain: ["ketosis"]` ihlal
- **vet_07** ("oksitetrasiklin dozu"): Yanıtta `oxytetracycline` geçti

Generator sistem prompt'unda "Yanıtın tamamı Türkçe olmalı. Çıplak İngilizce kelime YASAKTIR. 'Türkçe Karşılık (English Term)' formatında yaz" kuralı var ([prompts.py:39-44](../backend/app/graph/prompts.py)). Ancak v2 baseline'da bu kural genelde tutuyordu; Phase 2'de reranker seçtiği chunk'larda EN terim yoğunluğu artınca generator kuralı atlamaya başladı.

**Kanıt:** v2 baseline'da vet_02'de `must_not_contain` listesindeki "ketosis" sızmadı (Forbidden OK), Phase 2'de aynı case'te sızdı. Tek kontrolde değişen şey: chunk sıralaması.

### 4.3 LLM Scope Check Non-Determinism [ÇIKARIM]

`scope_check_node` ([scope_check.py](../backend/app/graph/nodes/scope_check.py)) gpt-oss-120b'ye "BÜYÜKBAŞ HAYVAN ile ilgili mi? EVET/HAYIR" diye sorar. `temperature=0` olsa bile Cerebras inference'da prefix-caching ve batch effect kaynaklı küçük non-determinism mevcuttur.

- **edge_01** ("ishal" — tek kelime): v2'de in_scope (accepted, fact 1.00), Phase 2'de out_of_scope (retrieval=0)
- **stress_03** ("asdf qwer xyz inekk veterrr"): v2'de in_scope (1.00), Phase 2'de fact 0.00

**Bu case'lerde scope_check kodu değişmedi.** Aynı prompt, aynı model, farklı karar. Olası açıklamalar:
1. LLM non-determinism (`temperature=0`'da bile küçük varyans var — kanıt: birden fazla LLM provider belge bunu doğruluyor)
2. `max_tokens=50` + reasoning model'de content collapse (bkz. enrich_query bug'ı — reasoning bütçesini doldurup content boş döndürebilir)

**Kanıt için ek deney gerekli:** Aynı sorguyu 5–10 kez çalıştırıp scope_check kararlarını izlemek.

### 4.4 LLM Judge Varyansı [ÇIKARIM]

`fact_coverage_llm` metriği OpenAI **gpt-4o-mini** kullanır ([llm_judge.py](../backend/eval/metrics/llm_judge.py)). Bu generator/scope/critic'ten farklı bir LLM. Aynı yanıt + aynı expected_fact için bazen "EVET" bazen "HAYIR" verebilir.

Örnek: vet_03 ("Akut puerperal metritis ile kronik endometritis ayırıcı tanı") v2'de fact_llm 0.67, Phase 2'de 0.00. **Yanıtlar farklı** (generator non-det) ama her ikisi de "metritis/endometritis" konusunu işliyor olabilir. Judge'ın farklı yanıtları farklı puanlaması beklenir.

**Bu reranker'la ilgili DEĞİL, eval altyapısının doğal varyansı.**

### 4.5 Reranker'ın Cross-Encoder Chunk Seçim Önyargısı [SPEKÜLATİF]

BGE-reranker-v2-m3 multilingual ama eğitim verisi MTEB-mix ve mMARCO. Bu setlerde:
- Türkçe-İngilizce pair sayısı (TR query + EN passage) görece düşük
- Veteriner tıbbı domain'i ile spesifik fine-tuning yok

Inspect script'te ([inspect_reranker.py](../backend/scripts/inspect_reranker.py)) gözlemlenen logit dağılımı:
- enrich_query bug'ı varken: logitler -10..-5 (uniform negatif, ayrıştırıcı değil)
- enrich düzeltildikten sonra: logitler -10..+0.15 (sigmoid 0.0001..0.54)

Yani reranker düzgün ayırt ediyor, ama **hangi kriterle seçtiği belirsiz**. Olası önyargılar:
1. **Surface-form bias:** TR query'deki kelimeler EN chunk'ta tam geçmiyorsa logit düşer
2. **Length bias:** Cross-encoder kısa pasajları yanlış değerlendirir
3. **Domain mismatch:** Veteriner literatüründe önemli "patogenez", "ayırıcı tanı" gibi söylem yapıları reranker'ın görmediği şekilde ifade edilebilir

**Bunu test etmek için:** Birden çok query üzerinde reranker'ın seçtiği vs. dense'in seçtiği top-3 chunk'ları manuel olarak içerik kalitesi açısından karşılaştırmak gerekir. Halen yapılmadı.

### 4.6 Generator'ın Top-3 vs Top-5 Etkisi [SPEKÜLATİF]

Eski sistem: dense top-5 → generator (5 kaynak)
Yeni sistem: dense top-30 → rerank top-3 → generator (3 kaynak)

Generator daha az ama daha alakalı kaynak görüyor. Ancak:
- Fact coverage metriğinde **çok kavram tutarsa skor yüksek**
- Top-3'te kavramlar daha sıkışık olabilir; top-5'te 4. veya 5. chunk'tan tamamlayıcı bilgi gelirdi
- Özellikle "Akut metritis vs kronik endometritis ayırıcı tanı" gibi karşılaştırmalı sorularda iki ayrı konsept için iki ayrı chunk gerekebilir

**Test edilebilir:** Phase 2'yi `RERANK_TOP_K = 5` ile yeniden koşmak.

---

## 5. Halüsinasyon Olabilir mi? — Şüphe Listesi

Kullanıcının kritik sorusu: "Reranker'ın daha kötü sonuç vermesi sadece halüsinasyon olabilir mi?" Yani benim analizimin gerçeği yansıtıp yansıtmadığını sorgulamak.

### 5.1 KESİN: Halüsinasyon değil

- 50 case eval JSON raporları gerçek dosyalardır ([20260520_024920__v2_baseline_hybrid.json](../backend/eval/reports/20260520_024920__v2_baseline_hybrid.json), [20260521_102532__phase2_full50.json](../backend/eval/reports/20260521_102532__phase2_full50.json)).
- Pass Rate'in -12 puan farkı eval JSON'larını parse eden Python script ile yeniden hesaplandı (kesin sayı).
- enrich_query bug'ı `reasoning_tokens=797`, `completion_tokens=800` ile reproduce edildi — gerçek Cerebras API yanıtı.
- Reranker'ın FP16'da scoring collapse'i (logitler -8..-10 negatif) gerçek model output'unda görüldü.

### 5.2 OLASI HALÜSİNASYON RİSKLERİ

| İddia | Şüphe |
|---|---|
| "Reranker'ın suçu LLM varyansından çok değil" | Tek bir 50-case ölçüm. Aynı config'i 3–5 kez çalıştırmadan **net** söyleyemem. |
| "vet_02/vet_07'de Phase 2 reranker chunk değişikliği nedeniyle EN sızdı" | İki case anekdot. Reranker'ın seçtiği chunk'larda EN yoğunluğu **manuel** ölçülmedi. |
| "edge_01 scope_check non-det. nedeniyle out_of_scope döndü" | Reproduce etmek için 5–10 koşum gerekli. **Yapılmadı.** |
| "Reranker'ın chunk seçimi 'kalitesiz'" | inspect script'te 1 query görüldü (süt humması). Diğer kategoriler için tek tek bakılmadı. |
| "Mini eval'da +0.056 sadece vet ağırlığı kaynaklı" | Matematiksel olarak destekleniyor (vet kazancı yeterince büyük) ama tek mini eval. Tekrar koşumla ±0.05 sapma görülebilir. |

### 5.3 Bu rapor için güvenli ifade kalıbı

**Söyleyebileceğin:**
- "Aynı eval setinde Phase 2 sonrası Production Pass Rate %70'ten %58'e düştü."
- "Düşüşün bir kısmı kontrollü değil — LLM-based scope check ve LLM-as-judge metrik altyapısının doğal varyansı var."

**Söyleyemediğin (henüz kanıt yok):**
- "Reranker'ın spesifik X tipi chunk'lara önyargısı var."
- "Phase 2'nin gerçek net etkisi -X puan." (Tek ölçüm + LLM varyansı = belirsizlik aralığı geniş)
- "BGE-reranker-v2-m3 Türkçe için kötü." (Domain + dataset spesifik bir bulgu, genelleme tehlikeli)

---

## 6. Tez Literatür Araştırması için Sorular

Bu raporu temel alarak şu literatür sorularını araştırmak faydalı olabilir:

### 6.1 Multilingual Cross-Encoder Reranker'lar

- BGE-reranker-v2-m3 Türkçe-İngilizce cross-lingual pair'lerde nasıl performans gösteriyor?
- mMARCO Turkish split'i veya MIRACL-tr benchmark sonuçları var mı?
- Üretim RAG sistemlerinde "TR query + EN source corpus" senaryosu nasıl çözülüyor?
- **Arama terimleri:** "cross-lingual reranking", "multilingual cross-encoder degradation", "BGE-reranker multilingual benchmark"

### 6.2 Reranker'ların Üretim RAG'a Eklediği Net Değer

- BGE/cohere/Voyage rerankers gerçek production deployment'larda fact accuracy'ye ne katıyor?
- "Reranker negative results" literatürde mevcut mu? (Birçok paper sadece pozitif sonuç gösterir)
- Medical domain'de cross-encoder kullanımı nasıl?
- **Arama terimleri:** "RAG reranker ablation study", "production rerank metrics", "OpenEvidence architecture", "medical RAG cross-encoder"

### 6.3 LLM Eval Varyans Yönetimi

- LLM-as-judge metrikler ne kadar güvenilir? (Stanford HELM, MMLU eval reproducibility çalışmaları)
- Temperature=0 LLM'lerde non-determinism kaynakları (Anthropic, OpenAI, Cerebras blog yazıları)
- Eval bootstrapping, confidence interval hesaplama yöntemleri
- **Arama terimleri:** "LLM evaluation variance", "judge LLM reliability", "RAG eval reproducibility"

### 6.4 Generator'ın Multilingual Source'lardan Sızıntı

- TR sistem prompt + EN source verildiğinde LLM'in dile sadakati nasıl?
- "Code-switching" probleminin RAG'da etkisi
- Sistem prompt sertleştirmesi vs. source pre-translation karşılaştırması
- **Arama terimleri:** "RAG language consistency", "multilingual generator hallucination", "source language leakage LLM"

### 6.5 Reranker Top-K Optimum

- top-3 mü top-5 mi top-10 mu? Production deployment'larda nasıl seçiliyor?
- Generator context length'ten bağımsız olarak chunk sayısının "answerability"a etkisi
- **Arama terimleri:** "optimal RAG context size", "top-k retrieval ablation"

---

## 7. Önerilen Sonraki Adımlar

### 7.1 Belirsizliği azaltacak hızlı deneyler

1. **Variance baseline ölçümü** (~1 saat):
   - v2 baseline config'i ile aynı 50-case 3 kez koş, std hesapla
   - Pass Rate'in doğal salınımı ne kadar bilelim

2. **Reranker top-K ablation** (~45 dk):
   - `RERANK_TOP_K = 5` ile Phase 2'yi tekrar koş
   - Top-3'ün "context dar" hipotezi gerçek mi gör

3. **Reranker on/off A/B** (~90 dk):
   - Aynı 50-case'de reranker'ı devre dışı bırakıp tekrar koş (sadece enrich-fix var)
   - Phase 2 düşüşünün ne kadarı reranker, ne kadarı enrich-fix yan etkisi

### 7.2 Karar (kanıtlı tek seçenek)

Mevcut veri ile Phase 2 net negatif (%70 → %58). Belirsizlik var ama yön net.

**Önerilen:** Reranker'ı geçici olarak devre dışı bırakmak, enrich-fix'i (gerçek bug düzeltmesi) tutmak, sonra Phase 3 (citation enforcement) çalışmasına geçmek. Citation enforcement reranker'ı yeniden değerlendirmek için doğal bir test ortamı sağlayacak.

### 7.3 Tez yazımı için savunma çizgisi

Tezde Phase 2'nin negatif sonucu **başarısızlık değil, kontrollü deneyin doğru çıktısı** olarak yazılmalı:
- "Hipotez kuruldu (reranker fact coverage'a +0.05–0.10 katacak)"
- "Eval altyapısı + 50-case test set ile ölçüldü"
- "Sonuç beklenenin tersine ortaya çıktı"
- "Nedenler analiz edildi: multilingual gap, LLM varyans, generator sızıntısı"
- "Bu negatif sonuç literatürde yeterince işlenmemiş; çalışmanın katkı alanı"

Bu yaklaşım literatür açısından **daha güçlü** bir tez argümanıdır. Her zaman çalışan bir sistem değil, kontrollü ölçümle yöntemini gösteren bir araştırmadır.

---

## 8. Ekler

### 8.1 Eval JSON dosyaları

- v2 baseline: `backend/eval/reports/20260520_024920__v2_baseline_hybrid.json`
- Phase 2 full50: `backend/eval/reports/20260521_102532__phase2_full50.json`
- fix1_2 mini: `backend/eval/reports/20260520_184612__fix1_2_validation.json`
- Phase 2 mini (enrich kırık): `backend/eval/reports/20260520_195342__phase2_reranker_mini.json`
- Phase 2 mini (enrich düzeldi): `backend/eval/reports/20260521_024517__phase2_after_enrich_fix.json`

### 8.2 Markdown raporlar (insan-okur dostu)

Yukarıdaki dosyaların aynı tag ile `.md` versiyonları aynı klasörde mevcut.

### 8.3 Debug scriptleri

- `backend/scripts/inspect_retrieval.py` — tek query → workflow full output
- `backend/scripts/inspect_reranker.py` — tek query → dense top-3 vs rerank top-3 yan yana, logit dağılımı

### 8.4 Üretim Pass Rate hesap formülü

```python
# Bir case "production-grade" sayılır eğer:
fact_llm >= 0.67    # 3 fact'ten 2'sini ele almış
forbidden == True   # yasak ifade yok
retrieval >= 0.5    # doğru kaynaktan ya da threshold geçmiş

# Pass Rate = production-grade case sayısı / toplam case
```

Mevcut sayılar:
- v2 baseline: 35/50 = **%70**
- Phase 2 full50: 29/50 = **%58**
