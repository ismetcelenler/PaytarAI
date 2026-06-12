# PaytarAI — Grounded Check Report

Dataset: `fixed_quick.yaml`  ·  Cases: `3`  ·  Backend: `http://localhost:8000`

Her case icin: **top-3 chunk** (generator'a giden, rerank sirali) ile **generator yaniti** yan yana. Yanitin chunk'lardan ne kadar dogrudan turetildigini eyeball kontrol icin.

---
## `producer_02`  ·  producer_natural  ·  broken  ·  producer
**Signals**: dense_top=`0.853` · rerank_top=`0.6096` · confidence=`high` · attempts=`0`  
**Critic chain**: `scope_check_in_scope → critic_accepted → confidence_scored`

### ❓ Soru
> dogumdan 3 gun gecti sutum dusuk hayvan da halsiz gozukuyor normal mi

### 🎯 Beklenen kavramlar (eval YAML)
- `doğum sonrası|lohusalık|doğum komplikasyonu`- `veteriner|veterinerinize`- `süt düşüşü|halsizlik|verim azalması`

### 📚 Generator'a giden top-3 chunk (rerank sıralı)

**Chunk [1]** — `Buyukbas Hayvan Yetistiriciligi` · dense_score=`0.807`

> Bununda yolu işletme bünyesinde kaliteli kaba yem üretilmesinden geçmektedir. Sığırlarda yüksek kaliteli kaba yemin özellikle de çayır otunu yerini tutacak başka bir yem maddesinin mevcut olmadığı unutulmamalıdır. Süt Humması (Hipokalsemi‐Doğum Felci) Sütçü ırklarda görülmekle beraber, üçüncü sağım dönemini aşmış yaşlı, yüksek verimli ve holstein x limousin melezi doğum yapan inekleri daha çok etkilemektedir. Genellikle doğumu izleyen 6-48 saat içerisinde ineklerin yatıp, kalkamamasıyla (doğum felci) karakterize bir hastalıktır. Ancak birçok durumda klinik belirtiler ortaya çıkmamaktadır. Nedeni, kolostrum ve süt salgısıyla aniden ve yüksek miktarda kalsiyum harcanmasıyla, kandaki kalsiyum düzeyinin düşmesidir. Kandaki kalsiyum seviyesi, paratiroid hormonu (PTH) kontrollü altında çeşitli h

**Chunk [2]** — `Pratik Sigircilik` · dense_score=`0.853`

> Tedavide memeler iyice boşaltıldıktan sonra meme içine ilaçlar verilmeli, memedeki şişliği ve kızarıklığı gidermek için memelere dıştan merhem uygulanmalı ve gerektiğinde kas içi antibiyotikler kullanılmalıdır. Bunun için bir Veteriner Hekime müracaat edilmelidir. Mastitisten korunmak için temizlik ve sağım kurallarına uyulmalı, ahırın temizliğine ve dezenfeksiyonuna özen gösterilmelidir. Sağımdan önce ve sonra memeler antiseptikli su ile iyice temizlenmelidir. Makine ile sağım yapılıyorsa sağım başlıkları memeye iyice yerleştirilmeli, vakum ayarının doğru yapılmasına dikkat edilmelidir. Memede süt biter bitmez başlıklar çıkarılmalı ve memede süt kalmamasına özen gösterilmelidir. Sık sık mastitise yakalanan, memeleri ve meme başları uygun olmayan hayvanlar sürüden çıkartılmalıdır. 13.2. Hİ

**Chunk [3]** — `Buyukbas Hayvan Yetistiriciligi` · dense_score=`0.740`

> Toksititeden dolayı tavsiye edilen sürelerden daha uzun süre kullanmaktan kaçınılmalıdır. Buzağılamadan 8 gün önce uygulanan tek bir 10 milyon IU kristalin vitamin D enjeksiyonu (damar içi veya deri altı) etkili bir önleyici tedbirdir. Beklenen tarihte inek henüz doğum yapmamışsa doz tekrarlanmalıdır. Bu durumda vitamin D yerine kullanılan ve hipervitaminozise neden olma ihtimali daha düşük olan, yeni bileşikler (25-hidroksikolekalsiferol, 1,25-dihidroksikolekalsiferol) kullanılmalıdır. Vitamin D metabolitleri gastrointestinal kalsiyum emilimini arttırırken, Sentetik sığır paratiroid hormon (PTH), gastrointestinal kalsiyum emilimini arttırır ve kemik rezorpsiyonunu uyarır. PTH, doğumdan 60 saat önce damar içi veya doğumdan 6 gün önce kas içi uygulanabilir. PTH kullanımının dezavantajları,

### 💬 Generator yanıtı

**Yapılacaklar:**
1. **Hayvanı gözlemle:** Vücudunun sıcaklığını ölç. Normal sıcaklık 38‑39 °C’dir. Dışkı ve idrarın olup olmadığını, yem yemeyi, su içmeyi ve ayakta durup durmadığını kontrol et.
3. **Kalsiyum takviyesi sağla:** Veterinerin önerdiği kalsiyum içeren yem, yalama taşı ya da sıvı takviyeyi temin et. Bu takviyeyi yemle birlikte vererek, hayvanın kalsiyum ihtiyacını karşılamaya yardımcı ol.
4. **Ortamı sıcak ve kuru tut:** Yatağını temiz samanla değiştir, ıslak ya da soğuk bir yerde bırakma. Gerekiyorsa, hayvanın üzerine hafif bir battaniye ört.
5. **Beslenmeyi düzenle:** Süt vermeyi geçici olarak azalt; ilk 12‑24 saat sadece elektrolit ve su ver. Daha sonra yumuşak yem (örneğin ince doğranmış ot) ekle.
**Tehlike işaretleri (bunları görürseniz ACİL):**
- Hayvan ayakta duramıyor, uzun süre yere uzanıyor.
- Vücut sıcaklığı 39,5 °C’nin üzerine çıkıyor.
- Dışkı ve idrar yapmıyor, ya da dışkıda kan var.
- Gözler çukurlaşmış, solukluk ve halsizlik artıyorsa.
- 24 saat içinde durumunda iyileşme gözükmüyorsa.
**Takip sorusu:**
- Sıcaklığını ölçtünüz mü?
- Dışkı ve idrar hâlâ devam ediyor mu?
- Hayvan suyu ne kadar içiyor, yem yemeyi ne kadar sürdü?
⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saatte düzelmezse mutlaka veterinerinize danışın.

---
## `emergency_02`  ·  emergency  ·  broken  ·  producer
**Signals**: dense_top=`0.768` · rerank_top=`0.1115` · confidence=`high` · attempts=`1`  
**Critic chain**: `scope_check_in_scope → critic_rejected → critic_safe_fallback → confidence_scored`

### ❓ Soru
> hayvanim kari sisdi balonlamis gibi nefes alamior ne yapayim hemen

### 🎯 Beklenen kavramlar (eval YAML)
- `acil|hemen|🚨`- `şişkinlik|gaz|balonlama`- `veteriner|veteriner çağırın|acil`

### 📚 Generator'a giden top-3 chunk (rerank sıralı)

**Chunk [1]** — `Amasya DSYB Yayini` · dense_score=`0.666`

> Böylece ortaya çıkan durağan köpük işkembe girişini “maskeler” ve hayvanın geğirmesine engel olur. İşkembe büyük hızla şişer, diyaframa baskı yapar, akciğerleri, kalbi, ana damarları sıkıştırır ve böylece hayvanın boğulmasına ve kalp-damar yetmezliğine yol açar. Sığır yere yatar ve ölür. Ortaya çıkma şartları ve belirtileri Sebep olan besinlerin türüne göre, AKSB, mevsime bağlı özellikler göstererek, merada veya ahır ortamında ortaya çıkabilir. Vakalar tek tük görülebildiği gibi birden fazla sığır aynı anda rahatsızlanabilir. Genç sığırlar kadar yetişkinlerde de görülebilir. En belirgin belirtisi işkembenin sırt pozisyonunda hızla genişlemesi ve hayvanın önce sol böğrünün (foto 20.1), sonra sağ böğrünün şişmesidir. Karın bölgesindeki şişkinlik ciddi boyutta ise, hayvanın soluması hızlanır,

**Chunk [2]** — `Sigir Besiciligi - Ciftci Egitim Serisi` · dense_score=`0.688`

> BE Sİ SI ĞIR LA RI NIN BA ZI ÖNEM Lİ HAS TA LIK LA RI Besi sığırlarında hastalıklara direnci artırmak için hayvanlara verilen vitamin ve mineral madde takviyeleri yeterli olmamakta, verilen yoğun kesif yeme bağlı olarak çoğu zaman mide barsak hastalıkları oluşmak- tadır. Bu hastalıkları azaltabilmek için besideki hayvana günlük tükete- bileceği kadar yem vermek, küflü ve bozuk gıdaları vermemek ve hayvan hastalandığında tedaviye erken başlamak gereklidir. Beside görülen bazı hastalıklar şunlardır. TİM PA Nİ : Fazla miktarda kesif yem veya yeşil kaba yem verilmesi sonucu işkembede gaz oluşumunun hızlanması, oluşan gazların dışarı atılamaması ve işkembenin şişmesiyle karakterize bir hastalıktır. İşkembede oluşan gazlar genellikle köpüklü olduğundan geğirme suretiyle gazın dışarı atılması mü

**Chunk [3]** — `Amasya DSYB Yayini` · dense_score=`0.686`

> Sindirim sistemine bağlı sebeplerin başında her türden börkenek-işkembe hastalıkları gelir. Gaz birikmesi Sığırda gaz birikmesi belirtisi börkenek-işkembede gaz birikmesiyle kendini gösterir. Hayvan tümden şişer veya karnında şişkinlik görülür (şekil 15.1). Biriken gaz serbest halde olabileceği gibi, bir köpük oluşturacak şekilde minik baloncuklar halinde de olabilir (köpüklü gaz birikmesi). İşkembenin sırt bölgesine doğru genişlemesi, çok belirgin olmayan vakalarda, hayvanın sol böğründeki çukurluğun önce düzleşmesi ve ardından şişkinleşmesiyle kendini gösterir (sol abdominal profil elma şeklini alır). Gaz birikimi ciddi seviyede ise, işkembenin genişlemesiyle birlikte sol karın bölgesi alt ve üst yandan şiştiği gibi sağ karın bölgesi de şişer. Gaz birikmesi işkembede üretilen gazların dı

### 💬 Generator yanıtı

Bu konuda elimdeki kaynaklarda yeterli ve guvenilir bilgi bulamadim. Lutfen veteriner hekiminize dogrudan danisin — durumun ciddiyetine gore muayene gerekebilir.

⚠️ Bu bilgi karar destegidir. Acil bir durumsa hemen veterinerinize basvurun.

---
## `vet_01`  ·  vet_technical  ·  mid  ·  veterinarian
**Signals**: dense_top=`0.782` · rerank_top=`0.6622` · confidence=`medium` · attempts=`1`  
**Critic chain**: `scope_check_in_scope → critic_rejected → critic_safe_fallback → confidence_scored`

### ❓ Soru
> süt humması patogenezi nedir kalsiyum homeostazı mekanizması doğum öncesi sonrası nasıl değişiyor

### 🎯 Beklenen kavramlar (eval YAML)
- `süt humması|hipokalsemi|milk fever`- `parathormon|PTH|kalsiyum homeostazı`- `D vitamini|kalsiyum emilimi|kemik rezorpsiyonu`

### 📚 Generator'a giden top-3 chunk (rerank sıralı)

**Chunk [1]** — `Buyukbas Hayvan Yetistiriciligi` · dense_score=`0.574`

> Toksititeden dolayı tavsiye edilen sürelerden daha uzun süre kullanmaktan kaçınılmalıdır. Buzağılamadan 8 gün önce uygulanan tek bir 10 milyon IU kristalin vitamin D enjeksiyonu (damar içi veya deri altı) etkili bir önleyici tedbirdir. Beklenen tarihte inek henüz doğum yapmamışsa doz tekrarlanmalıdır. Bu durumda vitamin D yerine kullanılan ve hipervitaminozise neden olma ihtimali daha düşük olan, yeni bileşikler (25-hidroksikolekalsiferol, 1,25-dihidroksikolekalsiferol) kullanılmalıdır. Vitamin D metabolitleri gastrointestinal kalsiyum emilimini arttırırken, Sentetik sığır paratiroid hormon (PTH), gastrointestinal kalsiyum emilimini arttırır ve kemik rezorpsiyonunu uyarır. PTH, doğumdan 60 saat önce damar içi veya doğumdan 6 gün önce kas içi uygulanabilir. PTH kullanımının dezavantajları,

**Chunk [2]** — `RebhunsDiseasesDairyCattle` · dense_score=`0.633`

> In this way, milk fever and subclinical hypocalcemia rates can be reduced via the relative acidification of cattle in late gestation. It is worth noting that strong univalent cations, such as potassium and sodium, probably increase the propensity for milk fever via their alkalinizing effects and subsequent diminished tissue responsiveness to PTH far more than does calcium in the diet during the late dry and early lactational period. Low-calcium diets can theoretically be fed as a means of reducing milk fever incidence because prolonged exposure to high PTH levels can overcome some of the negative effects of alkalinization on tissue responsiveness; however, these prolonged and low-calcium diets are often impractical to formulate and deliver. A more detailed discussion on catio

**Chunk [3]** — `Buyukbas Hayvan Yetistiriciligi` · dense_score=`1.000`

> Geçiş dönemindeki sığırlarda kan pH'sını düşürmek için önemli bir strateji, rasyon potasyum içeriğini azaltmaktır. Kuru dönemde ineklere verilecek kaba yemlerin yetiştirilmesinde kullanılan tarlalarda potasyum gübrelerinin kullanılmaması, kaba yemlerde potasyum düzeylerini düşürmenin diğer bir yoludur (işletmenin arazi varlığı ve ölçeğinin önemi). Laktasyondaki ineklerin rasyon kuru maddesi içeriğinde % 0,1 sodyum (Na) ve %1 potasyum (K) değerleri ideal olup, bu değerlere olabildiğince yakın olmaya çalışılmalıdır. Ancak, kurudaki ineklerin rasyonlarında temel olarak sodyum (Na) ve potasyum (K) fazlalığından kaçınmak gerekir. Rasyona, düşük potasyum seviyelerinin kanın alkaliliği üzerine etkileri dengelemek için klorür katılmalıdır. Rasyondaki klorür (CI) miktarı, K miktarının her zaman 5g

### 💬 Generator yanıtı

Elimdeki kaynaklarda bu spesifik konuya iliskin guvenilir bir veri dogrulanamadi. Halusinasyon riskini onlemek icin yanit uretilmedi; lutfen baska bir literatur kaynagina danisin.
