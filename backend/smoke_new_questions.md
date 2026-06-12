# Pattern 2 — Yeni Sorular Test


## `new_01_neonatal_diarrhea_vet` · veterinarian

**Test odagi**: Vet teknik — Rebhun's/Buzagi Sagligi'nde ayırıcı tanı var

**Sinyaller**: dense=0.8755, rerank=0.9988, conf=`high`, attempts=`0`, time=`13.5s`

**Critic chain**: `scope_check_in_scope → grounding_done → critic_accepted → confidence_scored`

**Grounding**: `action=passed, total=10, specific=10, generic=0, supported=10, dropped=0, drop_ratio=0.00`

### Soru
> Yenidoğan buzağılarda ishal yapan başlıca etkenler nelerdir, ayırt edici özellikleri nedir?

### Top-3 chunk (rerank sirali)

**[1]** `Buzagi Sagligi` (score=`0.738`)

> Neonatal buzağılarda ishale yol açan başlıca enfeksiyöz etkenler; bakteriler (E. coli, Cl. perfrin­ gens, kampilobakter, salmonella türleri), viruslar (Rotavirus, koronavirus, BVD virusu, adenovirus, parvovirus, astrovirus, kalicivirus ve bredavirus) ve protozoalar (Eimeria, kriptosporidium ve giardi­ a)’dır. İshalli buzağılarda ölümün temel nedeni; is­ hale bağlı sıvı-elektrolit kaybı sonucu meydana gelen hipovolemik şok, azotemi ve metabolik asidozisdir. Sıvı-elektrolit kaybı ve metabolik asi­ dozise bağlı olarak buzağılarda hipovolemi so­ nucu doku perfüzyon yetersizliği meydana gelir. Perf

**[2]** `Buzagi Sagligi` (score=`0.800`)

> Düvelerin/ ineklerin patojen hastalık etkenlerine karşı aşılan­ ması, yeterli ve zamanında ağız sütü verilmesi, hij­ yenik tedbirlerin alınması ve problemli sürülerde koruyucu ilaç uygulamaları ile buzağı ishallerinin yaygınlığının azaltılabileceği ve işletme şartlarına uygun buzağı yönetimi protokolü oluşturulma­ sının gerekli olduğuna dikkat çekilmektedir Yeni doğan buzağı ishallerinin tedavisinin en önemli uygulaması ağızdan ve damar içi yolla sıvı veril­ mesidir. Sıvı tedavisi ihmal edilmemelidir. İshalli buzağılarda belirli bir süre veya ishal devam ettiği sürede süt beslemesinin kesilmes

**[3]** `Amasya DSYB Yayini` (score=`0.728`)

> Risk faktörlerinden bazıları süt işletmelerine özgü olup aşağıdaki sebeplere bağlıdır: Süt sağıldıktan bir süre sonra buzağılara dağıtılıyorsa, sütün doğru oranda pıhtılaşmasını sağlamak ve eğer ön- homojenleştirme işlemi yapılmıyorsa, sütün yüzeyine çıkan 177 yağlı maddelerin yavaş tüketilmesini sağlamak üzere, süt düşük ısılarda (20 °C) buzağıya veriliyor olabilir; Buzağılara dağıtılan sütün doğası; meme enfeksiyonu geçiren inekten sağılmış, süt fabrikasına verilmeyen ve bakterice zengin süt buzağılarda ishal yapabilir. Sürünün ve hayvanların yönetimi Sürü yönetimiyle ilgili pek çok faktör i

### Generator yaniti

Yenidoğan buzağılarda ishalin başlıca etkenleri üç ana grupta toplanabilir: bakteriler, virüsler ve protozoal organizmalar. Bu patojenler, bağırsak epiteline doğrudan zarar vererek su ve elektrolit kaybına, hipovolemik şoka ve metabolik asidoz gibi ölümcül sonuçlara yol açabilir. Bakteriyel etkenler arasında *Escherichia coli*, *Clostridium perfringens*, *Campylobacter* türleri ve *Salmonella* spp. en sık rastlananlardır. Bu bakteriler, özellikle yeni doğmuş buzağının bağışıklık sistemi henüz tam gelişmediği için hızlı bir şekilde kolonize olur ve ishal gelişimine neden olur. Viral etkenler ise *Rotavirus*, *Coronavirus*, *Bovine Viral Diarrhea (BVD) virusu*, *Adenovirus*, *Parvovirus*, *Astrovirus*, *Calicivirus* ve *Bovine Respiratory Coronavirus* gibi çeşitli virüsleri içerir. Virüsler, bağırsak epitelinde daha belirgin hasar oluşturur; bu da mukozal mikrosirkülasyonun bozulması ve oksijenizasyonun yetersiz kalmasıyla sonuçlanır. Protozoal patojenler arasında *Eimeria*, *Cryptosporidium* ve *Giardia* bulunur. Bu protozoalar da epitel hücrelerine zarar vererek ishalin şiddetini artırır ve aynı zamanda bağışıklık sistemi üzerindeki baskıyı güçlendirir. Klinik açıdan, ishalli buzağılarda ölümün temel nedeni sıvı‑elektrolit kaybı sonucu ortaya çıkan hipovolemik şok, azotemi ve metabolik asidozdur. Bu süreç, doku perfüzyonunun yetersiz kalmasıyla tüm organizmada ciddi doku hipoksisine ve bağırsaklarda enterik hasara yol açar; özellikle viral ve protozoal etkenlerin oluşturduğu epitel hasarı, bakteriyel enfeksiyonların ardından gelen endotoksik riskini artırır.

---

## `new_02_producer_postpartum` · producer

**Test odagi**: Üretici broken style — süt humması patogenezi chunk'larında var

**Sinyaller**: dense=0.7883, rerank=0.8383, conf=`high`, attempts=`0`, time=`12.8s`

**Critic chain**: `scope_check_in_scope → grounding_done → critic_accepted → confidence_scored`

**Grounding**: `action=filtered, total=14, specific=7, generic=7, supported=12, dropped=2, drop_ratio=0.29`

### Soru
> ineğim doğurdu 5 gün oldu sallak gibi yürüyor sütü de az ne yapayım

### Top-3 chunk (rerank sirali)

**[1]** `Pratik Sigircilik` (score=`0.734`)

> Tedavide memeler iyice boşaltıldıktan sonra meme içine ilaçlar verilmeli, memedeki şişliği ve kızarıklığı gidermek için memelere dıştan merhem uygulanmalı ve gerektiğinde kas içi antibiyotikler kullanılmalıdır. Bunun için bir Veteriner Hekime müracaat edilmelidir. Mastitisten korunmak için temizlik ve sağım kurallarına uyulmalı, ahırın temizliğine ve dezenfeksiyonuna özen gösterilmelidir. Sağımdan önce ve sonra memeler antiseptikli su ile iyice temizlenmelidir. Makine ile sağım yapılıyorsa sağım başlıkları memeye iyice yerleştirilmeli, vakum ayarının doğru yapılmasına dikkat edilmelidir. Memed

**[2]** `Buyukbas Hayvan Yetistiriciligi` (score=`0.741`)

> Hastalığın tipik belirtileri yoktur. Hastalar çoğunlukla uzun süre yatmayı tercih ederler ve uyarıldıklarında zor ayağa kalkarlar. Tedavi süresince kalın bir altlık serilerek, uzun süreli yatışlarda oluşabilecek kas harabiyetleri ve yatak yaraları oluşumu en aza indirgenmelidir. Özellikle kuru dönemin başında ineklerin enerji miktarları kısıtlanarak, yağlanmaları önlenmelidir. VKS yüksek ineklerin kuru dönemde hareket etmesi sağlanmalı, rasyonda konsantre yem oranı düşük, kaliteli çayır otu oranı ise olabildiğince yüksek tutulmalıdır. Yem değişiklikleri usulüne uygun yapılmalı, koruyucu amaçlı

**[3]** `Sut Sigirlarinin Bakimi - Aziz Ozturk` (score=`0.730`)

> Silajın maliyeti ucuz, süt verimini artırma özelliği fazladır. Süt hayvanlarına mutlaka silaj verilmelidir. Kurak alanlarda arpa-fiğ karışımı silajı, sulak alanlarda mısır veya yonca silajı yapılmalıdır. İmkânı olan işletmeler hayvan pancarı ekimine de ağırlık vermelidirler. Hayvan pancarı da süt ve­ rimini artırmada önemli bir yemdir. Resim 17- Kaba yem yiyen hayvanlar SÜT İNEKLERİNİN MİNERAL MADDE İHTİYACI Süt ineklerinde mineral maddeler de önemlidir, özellikle kalsiyum ve fosfor büyük önem taşır. Kalsiyum ve fosfor eksikliğinde süt verimi düşer, iştah kaybolur ve kemikler kolayca kırılır. 

### Generator yaniti

**ACİL:** Hemen veterinerinizi arayın!
**Yapılacaklar**
1. **Gözlem ve takibe başla** – Hayvanın vücut ısısını ölç, dışkı ve idrar rengini kontrol et, yürüyüşteki dengesizlik, iştah ve süt verimini kaydet.
3. **Sıcak ve kuru bir ortam sağla** – Hayvanı temiz, kuru samanla kaplı bir ahıra koy, rüzgâr ve soğuktan koru. Gerektiğinde battaniye ya da eski bir örtüyle ısıyı artır.
4. **Beslenmeyi düzenle** – Gün içinde iki öğün kaliteli kaba yem ver, konsantre yem miktarını sınırlı tut. Kalsiyum içeren mineral blok ya da yalama taşı ekleyerek kalsiyum takviyesi yap.
5. **Meme ve sağım hijyenine dikkat et** – Memeyi ılık su ve temiz bezle sil, sağım öncesi ve sonrası memeyi antiseptik suyla iyice temizle. Gereksiz sık sağımdan kaçın.
**Tehlike işaretleri (vet’e başvurulmalı)**
- Hayvan ayakta duramıyor, tamamen yere yığılıp kalkamıyorsa.
- Dışkıda kan ya da çok kötü koku varsa.
- Süt tamamen kesilmiş ya da çok az geliyorsa.
- 24 saat içinde yürüyüşteki dengesizlik ve süt verimindeki azalma düzelmezse.
⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saat içinde düzelmezse mutlaka veterinerinize danışın.

---

## `new_03_tympani_emergency` · producer

**Test odagi**: Acil — Amasya DSYB timpani var ama spesifik tedavi (trokar) chunk'a bağlı

**Sinyaller**: dense=0.7916, rerank=0.9591, conf=`high`, attempts=`0`, time=`12.6s`

**Critic chain**: `scope_check_in_scope → grounding_safe_fallback → critic_accepted → confidence_scored`

**Grounding**: `SAFE_FALLBACK: drop_ratio=0.62 > 0.5: total=13, specific=8, generic=5, supported=8, dropped=5, drop_ratio=0.62`

### Soru
> ineğim aniden çok şişti karın bölgesi balon gibi ne yapayım acil mi

### Top-3 chunk (rerank sirali)

**[1]** `Amasya DSYB Yayini` (score=`1.000`)

> Böylece ortaya çıkan durağan köpük işkembe girişini “maskeler” ve hayvanın geğirmesine engel olur. İşkembe büyük hızla şişer, diyaframa baskı yapar, akciğerleri, kalbi, ana damarları sıkıştırır ve böylece hayvanın boğulmasına ve kalp-damar yetmezliğine yol açar. Sığır yere yatar ve ölür. Ortaya çıkma şartları ve belirtileri Sebep olan besinlerin türüne göre, AKSB, mevsime bağlı özellikler göstererek, merada veya ahır ortamında ortaya çıkabilir. Vakalar tek tük görülebildiği gibi birden fazla sığır aynı anda rahatsızlanabilir. Genç sığırlar kadar yetişkinlerde de görülebilir. En belirgin belirt

**[2]** `Amasya DSYB Yayini` (score=`0.711`)

> Sindirim sistemine bağlı sebeplerin başında her türden börkenek-işkembe hastalıkları gelir. Gaz birikmesi Sığırda gaz birikmesi belirtisi börkenek-işkembede gaz birikmesiyle kendini gösterir. Hayvan tümden şişer veya karnında şişkinlik görülür (şekil 15.1). Biriken gaz serbest halde olabileceği gibi, bir köpük oluşturacak şekilde minik baloncuklar halinde de olabilir (köpüklü gaz birikmesi). İşkembenin sırt bölgesine doğru genişlemesi, çok belirgin olmayan vakalarda, hayvanın sol böğründeki çukurluğun önce düzleşmesi ve ardından şişkinleşmesiyle kendini gösterir (sol abdominal profil elma şekl

**[3]** `Amasya DSYB Yayini` (score=`0.709`)

> Sığırda gaz birikmesi belirtisi börkenek-işkembede gaz birikmesiyle kendini gösterir. Hayvan tümden şişer veya karnında şişkinlik görülür (şekil 15.1).

### Generator yaniti

Bu konuda elimdeki kaynaklarda yeterli bilgi bulamadim. Lutfen veterineriniz hekimine danisin.

⚠️ Bu bilgi karar destegidir.

---

## `new_04_mastitis_vet_specific` · veterinarian

**Test odagi**: Vet spesifik — intramammar antibiyotik atılım süresi muhtemelen kaynakta YOK → halüsinasyon riski

**Sinyaller**: dense=0.7623, rerank=0.9088, conf=`high`, attempts=`1`, time=`73.5s`

**Critic chain**: `scope_check_in_scope → grounding_done → critic_rejected → grounding_done → critic_safe_fallback → confidence_scored`

**Grounding**: `action=passed, total=11, specific=6, generic=5, supported=11, dropped=0, drop_ratio=0.00`

### Soru
> Klinik mastitis tedavisinde intramammar antibiyotik seçiminde neye dikkat etmeli, atılım süresi nasıl yönetilir?

### Top-3 chunk (rerank sirali)

**[1]** `Amasya DSYB Yayini` (score=`0.687`)

> Bir örnek verecek olursak, DT 104 diye nitelendirilen bir S. Typhimurium kaynağı 1980’li yılların sonunda İngiltere’de ortaya çıkmış ve ardından, Fransa’yı da içine alan pek çok ülkeye yayılmıştı. Bu bakteri kaynağı (fenotip ACSSuT) ampisiline, kloramfenikole (ve florfenikole), streptomisine (ve spektinomisine), sülfamitlere ve tetrasiklinlere direnç göstermektedir. O yıllardan bu yana, bu bakteri kaynağı kinolonlara ve trimethoprime de yeni dirençler gelişmiştir. Çoklu direnç gösteren yeni bakteri kaynaklarının ortaya çıkma riskini sınırlandırmak için aşağıdaki tavsiyeler dikkate alınmalıdır:

**[2]** `Sut Sigirlarinin Bakimi - Aziz Ozturk` (score=`0.698`)

> Mastitise çeşitli mikroplar, vurma ve çarpmalar, kötü çevre koşulları, bakım ve besleme hataları ve sağım hataları sebep olur. Mastitiste başarı şansı erken teşhis ve uygun tedaviye bağlıdır, gecikmiş vakalarda tedavi şansı azalır. Tedavide memeler iyice bo­ şaltıldıktan sonra meme içine ilaçlar verilmeli, memedeki şişliği ve kızarıklığı gidermek için memelere dıştan merhem uygulanmalı ve gerektiğinde kas içi antibiyotikler kullanılmalıdır. Bunun için bir Vete­ riner Hekime müracaat edilmelidir. Hasta memelerin tedavi edilmesi uzun zaman alır ve pahalıdır. Çoğu zamanda meme kör kalır veya süt 

**[3]** `RebhunsDiseasesDairyCattle` (score=`0.719`)

> Inflammation, cellular debris, and decreased ability to diffuse throughout the quarter diminish the effectiveness of all antibiotics, especially intramammary antibiotic infusions. Therefore the pharmacology of each drug considered, regardless of antibiotic sensitivity results in vitro, must be evaluated. By and large, whereas weak acids are better choices for intramammary administration in the treatment of clinical mastitis, the weak bases achieve better tissue levels when given systemically. Macrolide antibiotics and sulfonamides, when given systemically, establish high milk-toplasma ratios i

### Generator yaniti

Elimdeki kaynaklarda bu spesifik konuya iliskin guvenilir bir veri dogrulanamadi. Halusinasyon riskini onlemek icin yanit uretilmedi; lutfen baska bir literatur kaynagina danisin.

---

## `new_05_calf_vaccination` · producer

**Test odagi**: Üretici — spesifik aşı takvimi (önceki halüsinasyon source'u). Pattern 2 yakalamalı.

**Sinyaller**: dense=0.8346, rerank=0.9667, conf=`high`, attempts=`0`, time=`17.8s`

**Critic chain**: `scope_check_in_scope → grounding_done → critic_accepted → confidence_scored`

**Grounding**: `action=filtered, total=24, specific=15, generic=9, supported=20, dropped=4, drop_ratio=0.27`

### Soru
> buzağılarımı kaç günlükken aşılatmalıyım hangi aşılar gerekli

### Top-3 chunk (rerank sirali)

**[1]** `Buzagi Sagligi` (score=`0.694`)

> Hastalık kontrol testleri 30-60 gün aralıklarla tekrarlanmalıdır. BUZAĞILAR Yeni Doğan Buzağı Doğumu takiben ağız sütünü almalıdır. Anneleri bağışık değilse hiperimmün buzağı septisemisi serumu verilmelidir. 1-2 Aylık Buzağı Vitamin (A, D, E, vs.) ve Mineral Madde (Ca, P, Cu, Se, Mg, vs) verilmelidir. Clostridial aşılar (Karma, 3 hafta arayla 2 kez) 3-4 Aylık Buzağı Şap aşısı (3 hafta arayla 2 kez), Pasteurella/Manhaemia aşısı (3 hafta arayla 2 kez) LSD aşısı, (4 hafta arayla 2 kez, daha sonra yılda tek doz) Theileria aşısı (Aşı kenelerin mevsimsel etkinliğinin başlamasından en az 2 ay önce ha

**[2]** `Sut Sigirlarinin Bakimi - Aziz Ozturk` (score=`0.704`)

> Aşıla­ rın yeterli bağışıklığı sağlaması için aşılamalar 10-14 günlük aralık­ larla yapılmalıdır. Yapılması gereken bu aşılama ve ilaçlamaları şu şekilde sıralayabiliriz. 1- Şap aşısı: Yılda iki defa ilkbaharda ve sonbaharda yapılır. Hayvanları şap (Tabak) hastalığına karşı korur. 2- Antraks aşısı: Yılda bir defa ve ilkbaharda yapılır. Hayvan­ ları Antraks (Şarbon) hastalığına karşı korur. Şarbon süt vasıtasıyla insanlara da bulaşan bir hastalık olduğundan aşılama önemlidir. 3- Brucellosis aşısı: Ya 4-8 aylık dişi buzağılara veya ergin yaştaki dişi hayvanlara bir defa yapılır ve hayat boyu bağ

**[3]** `Buzagi Sagligi` (score=`0.744`)

> Laktasyon ile birleştiğinde, hastalığa maruz kalmaya cevap ver­ me yeteneği zayıflayabilir. Gebe düveleri, doğum­ dan 12 hafta öncesinde hastalıklara karşı koruma sağlayan aşılar ile aşılanmalı ve 3-4 hafta sonra bir doz uygulanmalıdır. Daha sonraki gebelik dö­ nemlerinde doğumdan 5-7 hafta önce tek doz aşı yeniden uygulanmalıdır. Buzağı ishallerinin kontrolü için enterotoksi­ jenik E coli pilus tip k99, rota ve corona virüs aşısı, özellikle Clostridium perfringens tip C ve D’nin neden olduğu enterotokseminin kontrolü için aşılama uygulanır. Süt ineklerinde mastitislerinin önlenmesi için kombi

### Generator yaniti

🚨 ACİL: Hayvanınızda ani ateş, nefes darlığı, kanlı dışkı ya da tamamen hareketsiz kalma gibi çok ciddi belirtiler varsa hemen bir veteriner çağırın!
**Buzağı aşı takvimi – Ne zaman ve hangi aşılar?**
1. **Doğumdan hemen sonra**
- Yeni doğan buzağının annesinden kolostrum alması gerekir. Anne hayvan bağışıklıklı değilse, hiperimmün buzağı serumunun verilmesi önerilir.
2. **1‑2 ay (yaklaşık bir‑iki ay) yaşında**
- Vitamin (A, D, E vb.) ve mineral (Ca, P, Cu, Se, Mg) takviyesi yapılır.
- Clostridial (karma) aşısı 3 hafta arayla iki kez uygulanır.
3. **3‑4 ay (üç‑dört ay) yaşında**
- Şap (tabak) aşısı 3 hafta arayla iki kez.
- Pasteurella / Mannhaemia aşısı da aynı 3‑haftalık aralıkla iki kez.
- LSD (sığır vebası) aşısı 4 hafta arayla iki kez, ardından yılda bir kez tekrarlanır.
- Theileria aşısı, kenelerin aktif olduğu dönemden en az iki ay önce (örnek: Mart‑Nisan ayları öncesi) uygulanır.
4. **9‑12 ay (dokuz‑on iki ay) yaşında**
- Şap aşısı bir kez.
- Antraks aşısı (bölgedeki geçmiş antraks vakalarına göre) bir kez.
- Clostridial aşılar tekrar uygulanabilir.
5. **Aşı aralıkları**
- Aşılar genellikle 10‑14 günlük aralıklarla yapılmalıdır; aynı aşıyı tekrarlarken 3‑hafta (21 gün) veya 4‑hafta (28 gün) aralıklar kullanılabilir.
**Dikkat edilmesi gereken tehlike işaretleri (vet çağırın):**
⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saate içinde düzelmezse mutlaka veterinerinize danışın.

---

## `new_06_reproductive_management` · producer

**Test odagi**: Üretici management — Pratik Sigircilik/Sut Sigirlarinin Bakimi'nda olmali

**Sinyaller**: dense=0.8907, rerank=0.9931, conf=`high`, attempts=`0`, time=`11.7s`

**Critic chain**: `scope_check_in_scope → grounding_done → critic_accepted → confidence_scored`

**Grounding**: `action=filtered, total=10, specific=6, generic=4, supported=9, dropped=1, drop_ratio=0.17`

### Soru
> ineğimi ne zaman tohumlatmalıyım uygun kızgınlık belirtileri nelerdir

### Top-3 chunk (rerank sirali)

**[1]** `Sut Sigirlarinin Bakimi - Aziz Ozturk` (score=`0.756`)

> Diğer hayvanları koklarlar, 3. Diğer hayvanların üzerine atlarlar, bu hayvanların kendi üzer­ lerine atlamasına rıza gösterirler ve bu durumdan hoşlandıklarını belli ederler, 4. Buzağısını teper ve emzirmek istemezler, 5. Süt verimleri azalır ve normal sağımlarını yaptırmazlar, 6. Vulva dudakları kızarmış, nemlenmiş ve hafif şişmiştir. Yu­ murta akına benzer çara akıntısı vardır. 1.5 yaşını tamamlamış düveler ve doğumu takip eden 2. aydan sonra kızgınlık belirtisi gösteren inekler kızgınlık gösterdikleri andan itibaren 24 saat içerisinde tohumlanmalı veya boğaya verilmelidir. Kızgınlık görüldü

**[2]** `Buyukbas Hayvan Yetistiriciligi` (score=`0.731`)

> Oluşturulan protokoller; düzenli kayıt tutma, gözlem, tecrübe, takip ve belirlenmiş hedefler doğrultusunda güncellenmelidir. Her çiftliğin kendine özel bir kızgınlık takip programı olmalıdır. Özellikle süt verimi yüksek olan ineklerde kızgınlık gösterme süresi kısalmaktadır. Orta ve büyük ölçekli işletmeler, kaçırılan her kızgınlığın 21 günlük bir zaman kaybı olduğunu göz önünde bulundurarak, kızgınlık takibinden sorumlu bir kişi belirlenmelidir. Kısa veya rastgele sürelerle yapılan gözlemler sütçü ineklerin kızgınlıklarını yakalamak için yeterli olmamaktadır. Tecrübeli ve sorumlu kişi; inekle

**[3]** `Buzagi Sagligi` (score=`0.742`)

> Kızgınlığı belirlenemeyen ineklerde tohumlama yapılmaya­ cağı gibi, yapılmayan tohumlamadan da gebelik sağlanamayacaktır. Bununla birlikte kızgınlığı be­ lirlenmiş ancak uygun zamanda tohumlanamayan hayvanlarda da gebelikler sağlanamamaktadır. Dolayısıyla işletmeler için en önemli faaliyet; kız­ gınlıkların doğru olarak belirlenmesi ve belirlenen kızgınlıklarda doğru zamanda tohumlamaların yapılmasıdır. Yapılan araştırmalarda kızgınlığı be­ lirlenmiş bir hayvanda tohumlama için en uygun zamanın, kızgınlık başlangıcından 8 saat sonra ol­ duğu ifade edilmektedir. Selçuk Üniversitesi Veteriner Fa

### Generator yaniti

**Yapılacaklar**
1. **Kızgınlık belirtilerini yakından izle** – İnek diğer hayvanları koklar, onlara atlar, kendisine de diğer hayvanların atlamasına izin verir. Bu davranışların yanı sıra vulva dudakları kızarmış, hafif şişmiş ve nemli olur; bazen yumurta akına benzer şeffaf bir akıntı görülür. Bu işaretler ortaya çıktığında inek “kızgınlıkta” demektir.
2. **Kızgınlık başlangıcını not al** – Belirtilerin ilk görülmeye başladığı zamanı kaydet. En uygun tohumlama zamanı, kızgınlık başlangıcından **8‑12 saat** sonra gerçekleşir. Bu sürede yapılan inseminasyon gebe kalma ihtimalini en üst seviyeye çıkarır.
3. **Tohumlamayı 24 saat içinde tamamla** – Kızgınlık belirtilerinin ortaya çıkmasından **24 saat** geçtikten sonra yapılan tohumlama genellikle başarılı olmaz. Bu yüzden inseminasyonu mümkün olduğunca erken, ideal olarak 8‑12 saat içinde yapmaya çalış.
4. **Gün içinde iki kez gözlem yap** – Çoğu inek kızgınlık belirtilerini **18.00‑06.00** saatleri arasında gösterir. Sabah erken ve akşam geç saatlerde, en az **30 dakika** süren gözlemlerle kızgınlık tespiti yap. Bu, doğru zamanlamayı kaçırmamanıza yardımcı olur.
5. **Veterinerle iletişimde kal** – Kızgınlık belirtileri belirsizse, 24 saat içinde net bir belirti ortaya çıkmazsa veya vulva şişliği/akıntı aniden artarsa, veterinerden destek al. Doğru zamanlamayı kaçırmamak ve gebelik şansını artırmak için uzman görüşü önemlidir.
**Dikkat edilmesi gereken durumlar (ACİL)**
- Kızgınlık belirtileri **24 saat** içinde ortaya çıkmazsa ve inek hâlâ normal davranıyorsa, hormonal dengesizlik ya da sağlık sorunu olabilir; veteriner kontrolü gerekir.
⚠️ Bu bilgi karar desteğidir. Belirtiler kötüleşirse veya 24 saatte düzelmezse mutlaka veterinerinize danışın.

---
