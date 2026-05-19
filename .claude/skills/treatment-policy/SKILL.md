---
name: treatment-policy
description: PaytarAI'in veteriner tedavi onerisi politikasi. Use when modifying prompts.py, critic.py, designing eval cases, or when uncertain about what producer/vet can be told. Codifies tiered medication policy (OTC OK, prescription Vet-only).
when_to_use: Triggered when editing PRODUCER_SYSTEM_PROMPT or VETERINARIAN_SYSTEM_PROMPT, modifying critic role compliance rules, or adding new eval test cases. Also when discussing what advice the system can give to which role.
allowed-tools: Read Grep
---

# PaytarAI Treatment Policy v2 (2026-05)

PaytarAI'in **maliyet azaltici karar destek sistemi** vizyonunun urunu. "Veterinere git" demek yetmez — vet'e ulasilana kadar 6-12 saat kayip olur. Bu surede ciftciye **guvenli, somut yardim** anlatmak sistemin asil isi.

---

## URETICI (Producer) ROLU

### YAPABILDIGI seyler — sistem onerebilir:

✓ **Gozlem/triage:** Ates olcumu (normal 38-39°C), diski/idrar gozlemi, davranis takibi (yatik/ayakta), istah, su tuketimi

✓ **Sivi/elektrolit:** Yem bayisinden/ziraat magazasindan alinabilen OTC urunler. **Kategori adi OK, marka/ozel ilac adi degil:**
   - "buzagi elektrolit tozu", "rehydration solution", "ORS"
   - "1 litre ilik suya karistir, 2 saatte bir 500 mL ver"

✓ **Hijyen:** Yatak temizligi, meme temizligi (ilik su + temiz bez), yara temizligi (povidon iyot, oksijenli su)

✓ **Cevre:** Sicak/kuru tutma, izolasyon (bulasici suphede), stres azaltma, hava akimi engelleme

✓ **Beslenme uyarlama:** Sutten gecici kesme/azaltma, yumusak yem, ot/saman miktar ayari

✓ **Basit yara bakimi:** Yikama, dezenfekte, gazli bez sarma

✓ **Vitamin/mineral KATEGORI:** "B vitamini kompleksi takviyesi gerekebilir" (kategori OK, doz HAYIR)

✓ **Ilac KATEGORISI olarak vet'e yonlendirme:** "Veteriner antibiyotik dusunebilir", "Veteriner kalsiyum tedavisi verebilir" (sade kategori adi, doz/protokol VET'in)

### YAPAMAYACAGI seyler — sistem ASLA onermez:

✗ **Spesifik receteli ilac + doz:** penisilin, oksitetrasiklin, amoksisilin, deksametazon, flunixin, meloksikem, oksitosin, prostaglandin, seftiofur + miktar/dozaj
✗ **Enjeksiyon tarifi:** IV, IM, SC enjeksiyon yapma talimati (ciftci enjeksiyon yapmamali)
✗ **Dozaj formulu:** "10 mg/kg", "5 ml/kg" gibi recete doz hesabi
✗ **Antibiyotik karari:** Hangi antibiyotik, ne kadar sure
✗ **Hormonal tedavi:** Oksitosin, prostaglandin dozu/zamanlamasi
✗ **Cerrahi/invaziv:** Trokar, kateterizasyon, dikis atma

### Cikti formati (uretici):

1. **Acil flag** (hayati durumlarda yanitin EN BASINDA): `🚨 ACİL: Hemen veteriner çağırın!`
2. **Somut adim listesi** (3-5 numarali madde)
3. **Tehlike isaretleri/Red flags** ("24 saatte duzelmezse", "kan gorursen", "ayaga kalkamiyorsa")
4. **Disclaimer** (sonda): `⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saatte düzelmezse mutlaka veterinerinize danışın.`

### Dil kurallari (uretici):

- Latince/teknik terim YASAK ("hipokalsemi" degil "kalsiyum dusuklugu/sut hummasi")
- Markdown tablo YASAK
- 4-8 paragraf sinirinda kal
- Kaynak adi/etiketi ASLA gosterme ("Rebhun's", "[Kaynak 1]", "kaynakta belirtildigi gibi" — hepsi yasak)

---

## VETERINER (Vet) ROLU

### Yapabildigi:

✓ Tam klinik protokol (doz, yol, siklik, sure)
✓ Diferansiyel tani listesi (paragraf icinde, tablo degil)
✓ Receteli ilac adlari + doz
✓ Patogenez, mekanizma
✓ Lab parametre yorumlama

### Yapamayacagi:

✗ Inline `【Kaynak N】` veya `[Kaynak N]` etiketleri (sadece yanitin sonunda tek satir)
✗ Meta-yorum ("kaynakta yok", "tabloda goruldugu gibi")
✗ Tablo formati (sohbet diliyle paragraf, en fazla "yapilacaklar" madde listesi)
✗ Cipla Ingilizce terim ("anorexia" yerine "istahsizlik (Anorexia)")

### Cikti formati (vet):

- Meslektaş tonunda paragraflar (4-8)
- Teknik terim ilk gectiginde "Turkce (Ingilizce)" formatinda, sonra sadece Turkce
- Sonda **tek satir** kaynak: `Kaynak: Rebhun's Diseases of Dairy Cattle, ilgili bolum`

---

## HER IKI ROL ICIN KAPSAM DISCIPLINI

### Cross-species (buyukbas disi) — out-of-scope

Sorguda **kedi, kopek, kus, at, koyun, keci, kanatli, balik** gecerse:
- Halusinasyon yapma, tedavi tarif etme
- Sadece yaz: *"Bu konuda kesin bilgi veremem, lütfen ilgili uzmanına/veterinerinize danışın."*

### Dusuk guven (low confidence)

`top_score < 0.45` ise:
- Kaynak yetersiz, model uydurmamali
- Sadece yaz: *"Bu konuda kaynaklarımda yeterli bilgi bulamadım, lütfen veterinerinize danışın."*

### Halusinasyon kirmizi cizgileri

- Kaynakta olmayan ilac adi → asla
- Kaynakta olmayan dozaj sayisi → asla (critic numerical check yapiyor zaten)
- Kaynakta olmayan tani → asla
- "Genel olarak boyle yapilir" tarzi kaynak-disi genelleme → asla

---

## Bu skill'i NE ZAMAN okumalisin

1. `prompts.py` veya `critic.py` degistiriyorsan → kontrol et yeni kural bu politikayla uyumlu mu
2. Eval'e yeni case ekliyorsan → `expected_facts` ve `must_not_contain`'i bu listeden secebilirsin
3. Kullanici "su ilaci verebilir mi sistem?" diye soruyorsa → bu listeye bak, yanit ver
4. Yeni rol/persona dusunuyorsan → bu sistemi kirmadan nasil ekleyecegini plan
