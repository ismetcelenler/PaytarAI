# PaytarAI Eval Set Worksheet — v0.1

Bu belge **soruların ne olması gerektiğini** anlatır. Soruları sen kendi cümlelerinle yazacaksın. Toplam hedef: **25 soru**.

---

## Hedef Kullanıcı Personaları

### Persona A — Tech-literate Üretici
- Akıllı telefon kullanıyor, WhatsApp / sosyal medya aktif
- Hayvanlarını iyi tanıyor, semptomu doğru tarif edebiliyor
- Günlük Türkçe yazıyor, **tıbbi terim bilmiyor** ama hastalığı halk diliyle adlandırabilir ("süt humması", "şap")
- %20-30 oranda **yazım hatası** doğal (telefon klavyesi, telaş, otokorektör)
- Cümleler kısa, bazen noktalama eksik
- Tipik yaş: 25-55, modern hayvancılık yapan

### Persona B — Veteriner Hekim
- Meslektaş tonu, teknik terim rahat
- Protokol/dozaj/patogenez soruları sorar
- Kaynak atfı bekler
- Halüsinasyona en duyarlı kullanıcı

---

## Kategori Dağılımı (25 soru)

| Kategori | Sayı | Persona |
|---|---|---|
| Üretici doğal | 9 | A |
| Veteriner teknik | 9 | B |
| Acil durum | 4 | A (3) + B (1) |
| Kapsam dışı | 2 | A veya B |
| Muğlak/kısa | 1 | A |

---

## Yazım hatası kuralı

Toplam 25 sorudan **5-7 tanesinde** doğal yazım hataları olsun. Bunları kategori farkı yapmadan dağıt — emergency'de de olabilir, vet_technical'da bile bir doktorun acele yazışı görünebilir.

**Doğal yazım hatası örnekleri:**
- Noktalama eksik: *"hayvanım yere yatti kalkamiyor ne yapayim"*
- Türkçe karakter kaçırma: *"buzagimin ishali var"*
- Hızlı yazımdan harf yutma: *"ineim sabah yemyio"*
- Otokorektör hataları: *"süt verimi düştü iştahıda iyi değil"* (yapışık yazım)
- Kısaltma: *"vet çağrdm ama gelmiyo napayim"*

**Yapma:**
- Tamamen anlaşılmaz seviyede bozukluk (hedef kitle değil)
- Yapay görünen abartı hatalar

---

# KATEGORİ 1 — Üretici Doğal (9 soru)

Günlük çiftçi soruları. Acil değil, bilgi/yönlendirme arıyor. Halk diliyle yazılmış.

## Slot P1 — Süt verimi düşüşü
**Konsept:** Çiftçi hayvanın sütünün azaldığını söylüyor.
**Beklenen yanıtta geçmesi gerekenler:**
- Olası nedenler halk diliyle (beslenme, stres, mastitis = "meme iltihabı")
- Takip sorusu (kaç gündür, doğum yaptı mı, başka belirti)
- Veteriner çağırma önerisi
**Yanıtta KESİNLİKLE olmamalı:** `mg/kg`, `intramusküler`, `mastitis` (Latince), reçeteli ilaç adı
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P2 — Buzağıda ishal
**Konsept:** 3-7 günlük buzağı, ishal başlamış.
**Beklenen yanıtta:** Sıvı kaybı/dehidratasyon, ORS benzeri öneri, acil veteriner, yaş önemli
**KESİNLİKLE olmamalı:** Antibiyotik dozu, `mg/kg`, "rotavirus" tek başına (açıklamasız Latince)
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P3 — Topallayan inek
**Konsept:** Hayvan bir bacağını yere basamıyor / topallıyor.
**Beklenen yanıtta:** Olası nedenler halk diliyle (tırnak problemi, eklem iltihabı, yara), gözlem soruları, vet
**KESİNLİKLE olmamalı:** `polyarthritis`, `mg/kg`, reçeteli ilaç
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P4 — Memede sertlik / şişlik
**Konsept:** Sağarken meme sıcak, sert, hayvan rahatsız.
**Beklenen yanıtta:** Meme iltihabı (mastitis halk dili), süt görünümü, vet, sağım hijyeni
**KESİNLİKLE olmamalı:** Latince "mastitis" çıplak, antibiyotik adı, dozaj
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P5 — Karın şişmesi / geviş getirememe
**Konsept:** Hayvan geviş getirmiyor, karnı şişmiş.
**Beklenen yanıtta:** Timpani / şişkinlik halk dili, aciliyet derecesi, vet
**KESİNLİKLE olmamalı:** `ruminal tympani` Latince, dozaj
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P6 — İştahsızlık + halsizlik
**Konsept:** Belirsiz, hayvan iyi değil, yemiyor, halsiz.
**Beklenen yanıtta:** Takip soruları (ateş, dışkı, süt, yaş), birden fazla olası neden, vet
**KESİNLİKLE olmamalı:** Tek bir hastalığa erken atlama, dozaj
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P7 — Yeni doğan buzağı emmiyor
**Konsept:** Buzağı doğdu ama ana hayvanı emmiyor / yatıyor.
**Beklenen yanıtta:** Kolostrum aciliyeti, vet, ölüm riski, ısı kaybı
**KESİNLİKLE olmamalı:** Reçete, doz
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P8 — Doğum sonrası plasenta atmıyor
**Konsept:** İnek doğum yapalı 12+ saat oldu, plasenta hâlâ üzerinde.
**Beklenen yanıtta:** Retansiyo plasentae (halk dili: "son atmama"), bekleme süresi, vet
**KESİNLİKLE olmamalı:** `oksitosin` çıplak, doz, müdahale tarifi
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot P9 — Süt yapısında değişiklik (renk/kıvam)
**Konsept:** Sütte pıhtı / kanlı / sulu görünüm.
**Beklenen yanıtta:** Meme iltihabı belirtisi, sağım hijyeni, vet
**KESİNLİKLE olmamalı:** Antibiyotik dozu, Latince terim
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

---

# KATEGORİ 2 — Veteriner Teknik (9 soru)

Meslektaş tonu. Klinik bilgi arıyor. Türkçe ama tıbbi terim rahat.

## Slot V1 — Süt humması patogenezi + tedavi protokolü
**Konsept:** Vet hipokalsemi patogenezini ve standart kalsiyum protokolünü soruyor.
**Beklenen yanıtta:** Hipokalsemi mekanizması, IV kalsiyum boroglükonat, doz aralığı, takip
**KESİNLİKLE olmamalı:** `【Kaynak 1】` inline etiket, "kaynakta yok" meta yorum, çıplak İngilizce
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot V2 — Ketozis ayırıcı tanı + biyokimyasal markerler
**Konsept:** Postpartum ketozis tanısı için BHB, NEFA değerleri.
**Beklenen yanıtta:** Subklinik vs klinik ketozis, BHB cutoff, NEFA, propilen glikol
**KESİNLİKLE olmamalı:** İnline kaynak etiketi, meta yorum
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot V3 — Akut mastitis vakası yönetimi
**Konsept:** Klinik mastitis vakasında ampirik tedavi.
**Beklenen yanıtta:** Süt kültürü önemi, ampirik antibiyotik seçimi (genel kategoriler), withhold süresi
**KESİNLİKLE olmamalı:** İnline etiket, halk dili (vet'e yönelik)
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot V4 — Buzağı pnömonisi ayırıcı tanı
**Konsept:** 2-6 aylık buzağıda solunum yolu enfeksiyonu.
**Beklenen yanıtta:** BRD kompleksi, viral vs bakteriyel etken, antibiyotik kategorileri
**KESİNLİKLE olmamalı:** Inline etiket, meta yorum
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot V5 — Abomasum yer değiştirmesi (LDA/RDA)
**Konsept:** Sol veya sağ deplasman tanısı ve cerrahi/medikal yaklaşım.
**Beklenen yanıtta:** Ping testi, klinik bulgular, omentopeksi opsiyonu
**KESİNLİKLE olmamalı:** Inline etiket
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot V6 — Retansiyo plasentae yönetimi
**Konsept:** Vet, manuel müdahale ve farmakolojik yaklaşımı soruyor.
**Beklenen yanıtta:** 12-24 saat bekleme protokolü, manuel müdahale riski, prostaglandin/antibiyotik kullanımı
**KESİNLİKLE olmamalı:** Inline etiket, halk dili
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot V7 — Şap hastalığı klinik tanı ve raporlama
**Konsept:** Vet, FMD şüpheli vakada ne yapacağını soruyor.
**Beklenen yanıtta:** Vesiküler lezyon, ihbar zorunluluğu, izolasyon, dezenfeksiyon
**KESİNLİKLE olmamalı:** Inline etiket
**Beklenen kaynak:** Amasya (Türkiye mevzuat bilgisi için) veya Amasya

## Slot V8 — Yenidoğan buzağı ishalinde sıvı tedavisi
**Konsept:** Vet, dehidre buzağıda IV/oral sıvı protokolü soruyor.
**Beklenen yanıtta:** Dehidrasyon yüzdesi hesabı, IV kristalloid, asidoz düzeltimi, oral elektrolit
**KESİNLİKLE olmamalı:** Inline etiket
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot V9 — Hipomagnezemi (otlatma tetanisi) ayırıcı tanı
**Konsept:** İlkbahar otlatmasında akut nörolojik tablo.
**Beklenen yanıtta:** Mg eksikliği, IV Mg + Ca, etiyoloji, koruyucu tedbirler
**KESİNLİKLE olmamalı:** Inline etiket
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

---

# KATEGORİ 3 — Acil Durum (4 soru)

Hayati risk. Sistem **🚨 ACİL** flag'i tetiklemeli.

## Slot E1 — Doğum sonrası yere yatma (üretici)
**Konsept:** Süt humması klasik sunumu.
**Beklenen:** Acil uyarı, süt humması/kalsiyum, vet
**KESİNLİKLE olmamalı:** Dozaj, Latince
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot E2 — Şiddetli timpani / akut karın şişmesi (üretici)
**Konsept:** Hayvan nefes alamıyor, karnı çok şişmiş.
**Beklenen:** Acil uyarı, vet hemen, trokar zamanı yaklaşıyor mesajı
**KESİNLİKLE olmamalı:** Çiftçinin kendisi trokar yapması tarifi, dozaj
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot E3 — Buzağı şiddetli ishal + halsizlik (üretici)
**Konsept:** Sıvı kaybı kritik, buzağı yatıyor, emmiyor.
**Beklenen:** Acil uyarı, vet, oral sıvı bekleyene kadar
**KESİNLİKLE olmamalı:** Antibiyotik dozu
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

## Slot E4 — Akut nörolojik tablo (veteriner)
**Konsept:** Vet, ani başlayan kas titremesi/koma sebebini soruyor.
**Beklenen:** Hipokalsemi, hipomagnezemi, BSE, intoksikasyon ayırıcı; acil yaklaşım
**KESİNLİKLE olmamalı:** Inline etiket
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

---

# KATEGORİ 4 — Kapsam Dışı (2 soru)

Sistem **uydurmamali**, "bu konuda bilgi yok" diyebilmeli.

## Slot O1 — Kedi/köpek hastalığı
**Konsept:** Üretici/vet, küçük hayvan hastalığı soruyor.
**Beklenen:** Bilgi olmadığını söylemeli, vet'e yönlendirmeli
**KESİNLİKLE olmamalı:** Uydurulmuş tedavi/ilaç, "genel olarak şöyle" kaçamak
**Retrieval beklentisi:** `expect_retrieval_fail: true` (alakalı chunk gelmemeli)

## Slot O2 — Egzotik / Türkiye'de görülmeyen hastalık
**Konsept:** Afrika trypanosomozu, BSE klasik tablo gibi nadir/farklı bölge.
**Beklenen:** Kaynaklarda detay yoksa belirtmeli, vet yönlendirmesi
**KESİNLİKLE olmamalı:** Uydurma protokol
**Retrieval beklentisi:** `expect_retrieval_fail: true`

---

# KATEGORİ 5 — Muğlak / Kısa (1 soru)

Tek/iki kelime sorgu. Sistem **takip sorusu** sormalı.

## Slot M1 — Tek kelimelik sorgu
**Konsept:** "öksürük" veya "ishal" gibi tek kelime.
**Beklenen:** Takip soruları (yaş, kaç gün, ateş, iştah), birkaç olası neden
**KESİNLİKLE olmamalı:** Tek hastalığa erken atlama, doz
**Beklenen kaynak:** (boş bırak — `top_score >= 0.45` yeterli)

---

# YAML Dönüşümü

Yukarıdaki slotları doldurduktan sonra her birini `eval_set.yaml`'a şu formatta yazacağız:

```yaml
# Normal soru — kaynak belirtilmemiş, top_score >= 0.45 ile değerlendirilir
- id: P1
  question: "İneğimin sütü son 3 gündür düştü iştahıda iyi değil ne yapmalıyım"
  user_role: producer
  category: producer_natural
  expected_facts:
    - "meme iltihabı|mastitis|meme sorunu"
    - "beslenme|yem"
    - "veteriner"
  must_not_contain:
    - "mg/kg"
    - "intramusküler"
    - "mastitis"          # Latince, parantezsiz olmamalı

# Out-of-scope — retrieval başarısız olmali
- id: O1
  question: "Kedimin tüyleri dökülüyor ne yapayım"
  user_role: producer
  category: out_of_scope
  expect_retrieval_fail: true
  expected_facts:
    - "kaynak yok|bilgi yok|büyükbaş dışı|veteriner"
  must_not_contain:
    - "büyükbaş"

# Türkiye-spesifik — Amasya beklenir
- id: V7
  question: "FMD şüpheli vakada ihbar prosedürü nedir"
  user_role: veterinarian
  category: vet_technical
  expected_facts:
    - "vesiküler|ağız ayak"
    - "ihbar|bildirim|gıda tarım"
    - "izolasyon|karantina"
  must_not_contain:
    - "【Kaynak"
  expected_sources:
    - "Amasya"
```

ID şeması: P1-P9 (producer), V1-V9 (vet), E1-E4 (emergency), O1-O2 (out-of-scope), M1 (muglak).

---

# Sıra

1. **Şimdi:** Yukarıdaki slotları okuyup her birine soru yaz. Defter veya bu dosyanın altına ekle, fark etmez.
2. Yazım hatası dağılımına dikkat (5-7 sorunun doğal hatası olmalı, kasten değil)
3. Bittiğinde haber ver, ben birlikte `eval_set.yaml`'a aktaralım
4. Eval koşumu → baseline metrik
5. Sonra Qwen3-Embedding tartışması + reindex planı
