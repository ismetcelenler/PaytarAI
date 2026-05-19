# PaytarAI Eval Raporu — phase1_no_outliers_test3

- Dataset: `eval_set.yaml`
- Case sayisi: **3**
- Hata sayisi: 0

## Ozet Skorlar

| Metrik | Deger |
|---|---|
| Fact coverage — string match (avg) | 0.778 |
| **Fact coverage — LLM judge (avg)** | **0.667** |
| Forbidden pass rate | **1.000** |
| Retrieval precision (top-3 avg) | **1.000** |
| Avg top similarity score | 0.734 |
| Avg latency | 47.90 s |

## Kategori Kirilimi

| Kategori | N | Fact cov | Forbidden pass | Retrieval |
|---|---|---|---|---|
| producer_natural | 3 | 0.78 | 1.00 | 1.00 |

## Case Detaylari

### `P1` — producer_natural (producer)

**Soru:** hayvanın memesi şişmiş

- Fact (string): 0.33 (matched 1/3)
- **Fact (LLM judge): 0.33 [ZAYIF]** (matched 1/3)
   - LLM kacirdi: ['meme iltihabı|meme sorunu|mastitis', 'sağım|hijyen']
- Forbidden: **[OK]** — ihlal: -
- Retrieval: **1.00** [OK] top_sim=0.78
- Pipeline: status=accepted  critic_retries=1  confidence=high  latency=19.33s

**Yanit:**

> 🚨 ACİL: Eğer hayvanın gözü içeri kaçıyor, çok yüksek ateşi var, yem yemiyor ve tamamen hareketsizse hemen veteriner çağırın!
> 
> **Yapılacaklar:**
> 1. **Meme temizliği** – Ilık su ve temiz bir bezle memeyi nazikçe silin. Süt akıntısı varsa, temiz bir bezle hafifçe kurulayın. 
> 2. **Sıvı ve elektrolit desteği** – Yem bayisinden “elektrolit tozu” alın. Paketteki talimatlara göre ılık suyla karıştırın ve hayvanın bolca içmesini sağlayın. Süt vermeyi geçici olarak azaltın, böylece sindirim sistemi dinlensin. 
> 3. **Meme ortamını kuru ve temiz tutun** – Eski samanı atın, temiz ve kuru samanla değiştirin. Meme çevresine nemli bir örtü takmayın; nemli ortam bakteri üremesini artırır. 
> 4. **Sıcaklık ve konfor** – Hayvanı rüzgârsız, ılık bir yerde tutun. Soğuk havada ya da rüzgârlı alanlarda bırakmayın. 
> 5. **Veterinerle iletişim** – Durumu telefonla bildirin, gerekirse hayvanı hemen klinik ortama taşıyın. Veteriner, gerekirse antibiyotik ve kalsiyum tedavisi gibi iç tedavileri başlatacaktır.
> 
> **Tehlike işaretleri (bu belirtiler görülürse ACİL):** 
> - Gözlerin içeri kaçması (şiddetli su kaybı) 
> - Hayvan tamamen hareketsiz, uyarılara yanıt vermiyorsa 
> - Meme çevresinde şiddetli şişlik, kızarıklık ve sıcaklık artışı 
> - Süt akıntısında kan veya çok kötü koku varsa 
> - Ateş çok yüksek (özellikle buzağınızda 41 °C’nin üzerine çıkıyorsa) 
> 
> **Takip soruları:** 
> - Hayvanınız kaç yaşında ve süt veriyor mu? 
> - Şu ana kadar ateşi ölçtünüz mü? Ölçtüyse kaç derece? 
> - Meme şişkinliğinin yanı sıra yem yemiyor mu, su içiyor mu? 
> 
> Bu adımları uygularken hayvanı gözlemlemeye devam edin; durumun kötüleştiğini fark ederseniz hemen veterinerle iletişime geçin. 
> 
> ⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saat içinde düzelmezse mutlaka veterinerinize danışın.

---

### `P2` — producer_natural (producer)

**Soru:** ineğim topallıyor ne yapym

- Fact (string): 1.00 (matched 2/2)
- **Fact (LLM judge): 1.00 [OK]** (matched 2/2)
- Forbidden: **[OK]** — ihlal: -
- Retrieval: **1.00** [OK] top_sim=0.68
- Pipeline: status=accepted_after_max_retries  critic_retries=2  confidence=medium  latency=65.30s

**Yanit:**

> 🚨 ACİL: Eğer inek ayakta duramıyor, gözleri çukurlaşmışsa, nefesi çok hızlı ve yüzü soluklaşmışsa hemen veteriner çağırın!
> 
> **Yapacaklar:**
> 1. **Yatağı temiz ve kuru tut** – İneğin yatak halini temiz samanla değiştirin, ıslaklık ve çamurdan uzak tutun. Soğuk havada rüzgâr almamasına dikkat edin. 
> 2. **İneği rahat bir yere koy** – Sığ, kaymaz bir zeminde, duvar ya da çit gibi destekli bir alanda tutun. Çoğu zaman topallama, ayakların kayması ya da dengesiz zeminden kaynaklanır. 
> 3. **İneğin ayak ve eklemlerini kontrol et** – Ayak tabanında yara, çürüme, şişlik, çivi ya da taş gibi yabancı maddeler var mı bakın. Şüpheli bir şey görürseniz temiz su ve hafif sabunla yumuşak bir bezle silin, ardından temiz bir bezle kurulayın. 
> 4. **Sıvı ve elektrolit desteği** – Yem bayisinden “elektrolit tozu” alın. Paketteki talimatlara göre ılık suyla karıştırıp, inek su içebiliyorsa sık sık (örneğin her iki‑üç saatte bir) içmesini sağlayın. Süt vermeyi bir iki gün azaltıp, sadece su ve elektrolit çözeltisi vermek topallamayı hafifletebilir. 
> 5. **Veterinerle iletişime geç** – Topallama bir ya da iki günden uzun sürerse, ayakta şişlik, kızarıklık, sıcaklık artışı ya da yürürken ağrı belirtileri varsa, veterinerin müdahalesi gerekir. Veteriner gerekirse antibiyotik, ağrı kesici ya da ayak tedavisi (örneğin yara temizliği, bandaj) önerebilir.
> 
> **Dikkat edilmesi gereken tehlike işaretleri (vet’e git):**
> - 24 saat içinde topallama geçmez ya da kötüleşir. 
> - Ayakta şişlik, kızarıklık, sıcaklık artışı, yara ya da kan görülür. 
> - İnek ayakta duramıyor, tamamen yatıyor ve uyanmıyorsa. 
> - Nefesi çok hızlı, yüzü soluk ya da gözleri çukurlaşmışsa. 
> - İnek su içmeyi reddediyor ve susuz kalıyorsa.
> 
> **Sormam gereken birkaç soru:**
> - Topallama ne kadar süredir devam ediyor? 
> - Ayakta bir şişlik, yara ya da kızarıklık var mı? 
> - İnek ateşli mi (vücudunun sıcaklığı normal mi)? 
> - İnek su içiyor mu, iştahı nasıl?
> 
> Bu adımları uyguladıktan sonra durumun nasıl değiştiğini bana da bildirin, gerekirse daha detaylı önerilerde bulunabilirim. 
> 
> ⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saatte düzelmezse mutlaka veterinerinize danışın.

---

### `P3` — producer_natural (producer)

**Soru:** buzağı yem yemiyor neden

- Fact (string): 1.00 (matched 3/3)
- **Fact (LLM judge): 0.67 [OK]** (matched 2/3)
   - LLM kacirdi: ['iştah|iştahsızlık']
- Forbidden: **[OK]** — ihlal: -
- Retrieval: **1.00** [OK] top_sim=0.74
- Pipeline: status=accepted_after_max_retries  critic_retries=2  confidence=medium  latency=59.07s

**Yanit:**

> 🚨 ACİL: Eğer buzağınız ayakta duramıyor, gözleri çukurlaşmışsa, dışkısında kan varsa ya da 12 saat içinde iyileşme göstermiyorsa hemen bir veteriner çağırın! 
> 
> **Yapacaklar:** 
> 1. **Sıvı ve elektrolit desteği** – Yem bayisinden “elektrolit tozu” alın. 1 litre ılık suya karıştırıp, buzağınıza sık sık (günde birkaç kez) içirin. Süt vermeyi geçici olarak azaltın, böylece mide‑bağırsak sistemi dinlensin. 
> 2. **Sıcak ve kuru ortam** – Yatağını temiz, kuru samanla değiştirin. Üzerine ince bir battaniye ya da eski bir örtü sererek ılık tutun; rüzgâr ve soğuktan koruyun. 
> 3. **Meme ve ağız hijyeni** – Meme uçlarını ılık su ve temiz bir bezle nazikçe temizleyin. Ağız içinde yara varsa, hafif bir povidon iyot çözeltisiyle yıkayıp durulayın. 
> 4. **Beslenme düzeni** – Süt yerine yumuşak, sindirimi kolay yem (örneğin ezilmiş mısır unu ya da yulaf ezmesi) verin. Yem miktarını az tutup sık sık (günde birkaç kez) vererek mideyi yormamaya çalışın. 
> 5. **Gözlem ve kayıt** – Her 4‑6 saatte bir ateş ölçün (normal 38‑39 °C). Dışkı rengini, kıvamını, su tüketimini ve hareket hâlini not edin. 
> 
> **Tehlike işaretleri (vet çağırmanız gereken durumlar):** 
> - 12 saat içinde iştah ve hareket hâli düzelmezse. 
> - Dışkıda kan, çok kötü koku ya da çok sulu dışkı görülürse. 
> - Buzağınız ayakta duramıyor, yürüyemiyor ya da gözleri çukurlaşıyor. 
> - Ateşi 39 °C’nin üzerine çıkarsa ve 1 saatten uzun sürede düşmezse. 
> 
> **Sormam gereken birkaç soru:** 
> - Buzağınız kaç gündür yem yemiyor? 
> - Şu an ateşi var mı, varsa kaç derece? 
> - Dışkısının rengi ve kıvamı nasıl? 
> 
> Bu adımları uygularken, ilaç vermek ya da enjeksiyon yapmak gibi veterinerin yapması gereken işlemlerden kaçının. 
> 
> ⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saat içinde düzelmezse mutlaka veterinerinize danışın.

---
