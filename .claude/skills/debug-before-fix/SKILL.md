---
name: debug-before-fix
description: Bir sistem davranışı beklenmedik şekilde başarısız olduğunda VEYA bir bileşen "yanlış pozitif" üretiyorsa, fix önermeden ÖNCE kök nedeni gerçek veri ile tespit et. Patch reflexine karşı koruma. Use when critic/judge/embedder/scope_check unexpected reject, when test gives unexpected score, when retry loop isn't converging, when eval metric drops without obvious reason.
when_to_use: Triggered when an existing system component (critic, LLM judge, retrieval scoring, embedder similarity, scope detector) behaves wrongly OR produces unexpected reject/accept decisions. Also when user asks "why is X failing?" or "X seems broken".
allowed-tools: Bash Read Grep Edit
---

# Debug Before Fix — Kök Neden Analizi

Bir sistem bileşeni beklenmedik davranıyorsa (yanlış pozitif, sürekli reject,
metric düşüşü, retry loop'u, vb.), **fix önermeye TUTKLU OLMA**. Önce **gerçek
veriyle kök nedeni tespit et**, sonra düzelt.

## Tetiklendiği durumlar

- Critic veya LLM-judge sürekli reject ediyor
- Eval metric beklenmedik düştü/yükseldi
- Retry loop'u 2 max'a ulaşıp accepted_after_max_retries ile bitiyor
- Embedder skoru beklenenden çok düşük/yüksek
- Scope detector yanlış sınıflandırma yapıyor
- Bir LLM çağrısı boş veya hatalı JSON dönüyor

## ZORUNLU iş akışı

### 1. Soruyu net yaz
Patch düşünmeden önce **gözleneni tek cümlede yaz**:
- ❌ *"critic kötü çalışıyor"*
- ✓ *"hibrit critic 5/5 case'de LLM-judge tarafından reject ediyor, retry max'a ulaşıyor"*

### 2. Gerçek veriye dokun — varsayım yapma

**Pareto kuralı:** debug süresinin %80'i veri toplama olmalı, %20'si fix.

Yapılması gerekenler:
- **Eval JSON raporunu oku** — `state["audit_log"]` veya `state["critic_rejection_reasons"]` alanlarına bak
- **Component'a debug print ekle** — kararını ve gördüğü veriyi logla
- **1 sorulu izole test koştur** — production'da değil minimum reproducible örnekle
- **Asıl LLM/regex çıktısını gör** — özet/agrega değil

### 3. Kategori sor

Yanlış davranış hangi tip?
- **A) False positive** — yanlış reject. Kural çok agresif. Örnek: "Temiz kompres" → "halüsinasyon" demek
- **B) False negative** — yanlış accept. Kural eksik. Örnek: yasak ilaç adı listede yok
- **C) Mantık hatası** — kural yanlış yer. Örnek: vet sorgusunda producer kuralı uygulanıyor
- **D) Encoding/format** — Unicode, JSON parse, regex pattern hatası
- **E) Race condition / state** — birden fazla bileşen aynı state'i değiştiriyor

Kategori belirlenmeden fix önerme.

### 4. Hipotezi gerçek örnekle çürüt veya doğrula

*"Sanırım LLM-judge halüsinasyon kavramını yanlış anlıyor"* — bu **hipotez**.
Tek sorulu debug ile asıl JSON çıktısı görülmeli:
```
{"hallucinations": ["Temiz kompres uygulanması"]}
```
İşte bu **kanıt**. Hipotez doğrulandı, fix bilinçli yapılır.

### 5. Fix'i hedefli ve dar yap

Aceleyle "üzerine bina at" yapma:
- ❌ Yeni kural ekle, yeni katman ekle, yeni LLM çağrısı ekle
- ✓ Mevcut kuralın **sınırlarını sıkılaştır** (prompt netleştir, regex daralt, threshold ayarla)

Genellikle 5-15 satır kod değişikliği yeterli, **yeni mimari ekleme değil**.

### 6. Fix'ten sonra eval/test ile doğrula

Aynı veriyi tekrar koştur — sorunun çözüldüğünü ve yan etki olmadığını gör.

---

## Yapma listesi (anti-patterns)

- **❌ Sorunu fix öneren cümle ile başlatma.** Önce *"şu görüldü..."* ile başla.
- **❌ Birkaç olası neden yazıp birden fazlasını birden düzeltme.** Tek hipotez, tek fix, tek test.
- **❌ "Belki şudur" ile fix uygulama.** Kanıt olmadan kod değiştirme.
- **❌ Yeni katman ekleme refleksi.** Önce mevcut katmanı düzelt.
- **❌ Hata mesajını okumadan tahmin etme.** Stack trace + raw output her zaman bak.

## Yapma listesi içinden gerçek hayattan örnek

**Senaryo:** PaytarAI hibrit critic'i kurduktan sonra 5/5 case reject oldu.

**❌ Yanlış yaklaşım (debug-before-fix yok):**
> "LLM-judge çok katı, prompt'u yumuşatayım"
> *(prompt değişti, smoke test tekrar koştu, hala 4/5 reject — kök neden bulunmadı, kör atış)*

**✓ Doğru yaklaşım (bu skill ile):**
1. Soru: *"LLM-judge 5/5 case'de hangi sebeple reject etti?"*
2. Veri: critic.py'a debug print ekle, JSON çıktısını gör
3. Bulgu: `"hallucinations": ["Temiz kompres uygulanması", "Meme hijyeni..."]`
4. Kategori: A — false positive. LLM "kaynakta birebir yok" = "halüsinasyon" sandı
5. Fix: prompt'ta halüsinasyon tanımını sıkılaştır — "klinik iddia VE kaynakla çelişen"
6. Test: aynı 5 case ile tekrar, retry oranı ölç

---

## Diğer skillerle ilişki

- **rag-change-guard**: değişiklik YAPARKEN regression kontrolü. Bu skill ise değişiklik
  yapmadan ÖNCE neyi düzelteceğini anlamana yarar — ikisi tamamlayıcı.
- **hallucination-firewall**: medical RAG hallucination prevention kuralları. Bu skill
  ise bir kural yanlış pozitif verdiğinde nasıl analiz edileceğini söyler.
