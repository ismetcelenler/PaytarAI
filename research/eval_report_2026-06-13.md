# LettuceDetect Performans Raporu — 2026-06-13

**Veri kaynağı**: [eval_data_2026-06-13_182720.md](eval_data_2026-06-13_182720.md)
**Yöntem**: 5 farklı soru → pipeline çalıştır → her cümleyi (drop + keep hepsini) chunk'lara karşı elle kontrol et.
**Değerlendiren**: PaytarAI mühendisi (LLM judge YOK).

---

## Sonuç tablosu

| Soru | Cümle | Drop | Drop'lardan doğru | Kaçırılan halluc | Hata |
|---|---|---|---|---|---|
| 1 bloat | 14 | 4 | **0 / 4** | 1 ("kırkbayır = abomasum") | 5 / 14 = **%36** |
| 2 calf_diarrhea | 23 | 0 | — | 0 | 0 / 23 = **%0** |
| 3 postpartum | 13 | 8 | **0 / 8** | 0 | 8 / 13 = **%62** |
| 4 milk_fever | 16 | 0 | — | 0 | 0 / 16 = **%0** |
| 5 abomasal | 17 | 1 | **0 / 1** | 0 | 1 / 17 = **%6** |
| **TOPLAM** | **83** | **13** | **0 / 13 = %0** | **1** | **14 / 83 = %17** |

### Ana bulgu

**Sistem 13 drop kararının HEPSİNİ yanlış verdi. Tek gerçek halüsinasyon yakalanmadı.**

---

## Soru bazında detay

### Soru 1 — bloat (vet)

**Soru**: Sığırlarda karın şişkinliği nedenleri nelerdir?

**4 drop, hepsi yanlış**:

- **Drop #1**: *"Bu duvar hastalıkları arasında travmatik retiküloperitonitis, apse, tümör, aktinobasillozis ve paramphistomum paraziti yer alır."*
  Kaynak 1'de **birebir** geçiyor (parantez içinde aynı liste). **YANLIŞ DROP**.

- **Drop #2**: *"Ayrıca şirdenin aşırı dolu olması, listeriosis ve tetanoz gibi ek faktörler de şişkinliğe yol açabilir."*
  Kaynak 1'de **birebir** geçiyor. **YANLIŞ DROP**.

- **Drop #3**: *"Kaynak: Amasya DSYB Yayını, ilgili bölüm"*
  Generator prompt'unda zorunlu kıldığımız atıf satırı, halüsinasyon değil. **YANLIŞ DROP**.

- **Drop #4**: *"⚠️ Bu bilgi karar destegidir; klinik karar yetkisi sizdedir."*
  Disclaimer, generic safety. **YANLIŞ DROP**.

**1 kaçırılan halüsinasyon**:

- Cümle 5 KEEP: *"Süreğen gaz birikmesinin temel nedeni genellikle **kırkbayır (abomasum)** ya da işkembe duvarıyla ilişkilidir."*
  **Kırkbayır = omasum (3. mide), abomasum = şirden (4. mide).** Generator yanlış eşanlamlı kullandı. LettuceDetect kaçırdı.

### Soru 2 — calf_diarrhea (vet)

**Soru**: Yenidoğan buzağılarda ishal yapan başlıca etkenler ve ayırıcı tanı nasıldır?

**0 drop, 23 cümle hepsi KEEP doğru.**

Yanıt kaynaklardan kelimesi kelimesine paraphrase edilmiş:
- E. coli, Clostridium, Salmonella → Kaynak 1
- K99, CS 31A, Rotavirus, Coronavirus → Kaynak 1, 2
- Cryptosporidium, Eimeria, Giardia → Kaynak 2
- %50-60 rotavirus, %90 üç etken → Kaynak 3

Sadece "Önerilen tetkikler" listesinde **PCR ve kan gazı paneli** açıkça kaynaklarda yok, ama bu klinik sevk bilgisi olarak kabul edilebilir.

### Soru 3 — postpartum (üretici) — **FELAKET**

**Soru**: İneğim doğurduktan 5 gün sonra halsiz yürüyor ve sütü azaldı, ne yapayım?

**13 cümleden 8'i drop, hepsi yanlış.**

- **Drop #1**: *"Oral propilen glikol (doses range from 250 mL twice a day to 300 mL once a day, for up to 5 days) verin."*
  Kaynak 5 (Rebbuns EN)'de **kelimesi kelimesine İngilizce parantez içinde** geçiyor. Model muhtemelen İngilizce metni tanımayıp halüsinasyon sandı.

- **Drop #2**: *"Yemine kalsiyum içeren yalama taşları... kemik unu veya mermer tozu karıştırın."*
  Kaynak 2'de aynen var. **YANLIŞ DROP**.

- **Drop #3-8**: Vücut sıcaklığı (38-39°C), tehlike sinyalleri (40°C, hareketsizlik, kan dışkı, 12 saat).
  Generator prompt'umuzda **"tehlike işareti ve gözlem talimatı kaynak gerektirmez"** açıkça yazıyor. Yine de drop edildi. **8 / 8 YANLIŞ DROP**.

**Sonuç**: Kullanıcıya **tehlike sinyalleri gitmedi**. Sistem üretici için kritik safety bilgisini sildi. Bu medikal güvenlik açısından kabul edilemez.

### Soru 4 — milk_fever (vet)

**Soru**: Süt humması (parturient paresis) patogenezi ve tedavisi nedir?

**0 drop, 16 cümle hepsi KEEP doğru.**

Yanıt Pratik Sığırcılık + Büyükbaş Hayvan Yetiştiriciliği'nden **kelimesi kelimesine paraphrase**:
- Patogenez (kalsiyum-fosfor düşüşü) → Kaynak 1
- Klinik bulgular (titreme, sallantı, yatış) → Kaynak 1
- Tedavi (IV serum, kalsiyum propiyonat 50-125 g, subkutan kalsiyum) → Kaynak 1, 2
- Önlem (60-70 gün kuruya alma, yalama taşı, kemik unu) → Kaynak 1
- 24 saat sağım yasağı → Kaynak 2

Mükemmel performans.

### Soru 5 — abomasal_displacement (vet)

**Soru**: Şirden sola kayması nasıl teşhis ve tedavi edilir?

**1 drop, yanlış**:

- **Drop #1**: *"Cerrahi, deneyimli bir veteriner hekimin uzmanlığını gerektirir ve her müdahale sonrası hayvanın normal üretime dönmesi garantisi yoktur."*
  Önceki Q1 chunklarında **birebir** geçiyor: "Tüm bu teknikler veteriner hekimin uzmanlığını gerektirir. Bununla birlikte, tedavi edilen her sığırın normal üretime geri döneceğinin garantisi yoktur."
  **YANLIŞ DROP**.

Diğer 16 cümle keep doğru, yanıt kaliteli.

---

## Drop pattern analizi

LettuceDetect aşağıdaki cümle tiplerini sistematik olarak yanlış drop ediyor:

| Pattern | Örnek | Drop hatası |
|---|---|---|
| Atıf satırı | "Kaynak: Amasya DSYB, ilgili bölüm" | 2 |
| Disclaimer | "⚠️ Bu bilgi karar destegidir" | 1 |
| Liste maddeleri | "- Vücut sıcaklığı 40 °C'nin üzerine çıkarsa" | 4 |
| Tehlike sinyali (sayı içeren) | "12 saat içinde durumunda iyileşme olmazsa" | 2 |
| İngilizce parantez | "(doses range from 250 mL twice a day...)" | 1 |
| Birebir alıntı | "travmatik retiküloperitonitis, apse, tümör..." | 3 |

---

## Çıkarımlar

1. **DROP başarı oranı = %0**. Hiçbir gerçek halüsinasyon yakalanmadı.
2. **KEEP başarı oranı ≈ %99**. Tek kaçırılan halluc "kırkbayır = abomasum" (anatomik eşanlamlı hatası).
3. **Generic yanıt kalitesi yüksek**: Q2 ve Q4'te kaynaklardan birebir paraphrase, 0 drop, 0 hata.
4. **Q3'teki üretici sorusunda sistem güvenlik sinyalini sildi** — kabul edilemez davranış.
5. LettuceDetect'in 0.30 ratio threshold + 0.60 confidence + 4-char span filter ayarları yeterli değil. Modelin döndüğü span'lar genellikle yanıtın belirli kısımlarını (liste maddeleri, parantezler, tehlike eşikleri) drop etmeye yatkın.

## Sonraki adım

Önerilen: LettuceDetect'i kaldır, Faz C (per-claim attribution) ile değiştir. Drop kararı "%30 ratio aştı" olmaktan çıkıp "bu cümlenin hangi chunk'a bağlandığını bulamadık" olacak — daha tanılanabilir.
