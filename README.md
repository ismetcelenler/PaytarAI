# PaytarAI

**Büyükbaş hayvan sağlığında uzmanlaşmış, Türkçe çalışan, kaynağa dayalı (RAG tabanlı) medikal karar destek sistemi.**

PaytarAI; veteriner hekimlere ve üreticilere yönelik, büyük dil modellerinin tıbbi alandaki **halüsinasyon** (gerçek dışı ama inandırıcı bilgi üretme) riskini azaltmayı hedefleyen bir soru-yanıt sistemidir. Sistem yanıtı uçtan uca güvenilir literatür kaynaklarına dayandırır ve üretilen her iddiayı **cümle düzeyinde** dayandığı kaynakla eşleştirerek kullanıcıya **doğrulanabilir** biçimde sunar.

> ⚠️ **Sorumluluk reddi:** PaytarAI bir karar destek aracıdır, kesin tanı veya reçete iddiası taşımaz. Nihai klinik karar her zaman veteriner hekime aittir.

---

## Amaç ve Sağladığı Fayda

### Çözülen problem

Büyük dil modelleri akıcı metinler üretir; ancak tıbbi gibi yüksek riskli alanlarda, bilmedikleri konularda dahi kendinden emin bir dille **uydurma bilgi** (yanlış doz, var olmayan etken, kaynaksız tanı) üretebilir. Genel bir sohbet uygulamasında rahatsız edici olan bu kusur, hatanın doğrudan bir canlının sağlığını etkilediği veteriner hekimlikte ciddi bir risktir. Buna ek olarak, güncel ve kapsamlı veteriner literatürünün büyük kısmı İngilizcedir; **Türkçe kaynaklar hem sınırlı hem de dijital, aranabilir biçimde her zaman mevcut değildir.** Bu da Türkçe konuşan bir veteriner hekimin ya da üreticinin güvenilir bilgiye erişimini zorlaştırır.

### Projenin amacı

PaytarAI'nin amacı, Türkçe sorulan bir veteriner sorusuna; hem Türkçe hem İngilizce güvenilir kaynaklardan yararlanarak yanıt verebilen, ürettiği **her bilgiyi bir kaynağa dayandıran** ve bu dayanağı kullanıcıya **gösterebilen** bir sistem ortaya koymaktır. Kısacası hedef, "akıcı ama doğrulanamayan" bir yanıt yerine, **kaynağı gösterilebilen ve denetlenebilen** bir yanıt üretmektir.

### Sağladığı fayda

- **Güven ve doğrulanabilirlik:** Yanıttaki her iddia, dayandığı kaynak pasajla cümle düzeyinde eşleştirilir. Kullanıcı yalnızca bir cevap değil, o cevabın *nereden geldiğini* tıklayarak doğrulayabileceği şeffaf bir bilgi katmanı görür.
- **Halüsinasyon riskinin azaltılması:** Dil modeli yalnızca erişilen kaynaklarla sınırlandırılır; kaynak yetersizse sistem uydurmak yerine ek bilgi ister ya da güvenli biçimde geri çekilir.
- **Dil engelinin aşılması:** Çapraz dilli erişim sayesinde sınırlı Türkçe kaynak havuzu, İngilizce literatürle güçlendirilir; böylece Türkçe bir soru, İngilizce kaynaklardaki bilgiye de ulaşabilir.
- **Erişilebilirlik:** Rol ayrımıyla aynı bilgi, veteriner hekime teknik diliyle, üreticiye ise sade bir dille sunulur.
- **Şeffaflık:** Sistem, sınırlarını dürüstçe çizer; kapsam dışı (örneğin başka hayvan türü) ya da yanıtlayamayacağı soruları, yanlış bilgi üretmek yerine açıkça belirtir.

### Kimler için

- **Veteriner hekimler:** Sahada hızlı, kaynaklı bir ön referans; klinik kararı destekleyen denetlenebilir bilgi.
- **Üreticiler:** Günlük dille sorulabilen, sade ve yönlendirici (gerektiğinde veteriner hekime sevk eden) bir başvuru noktası.

---

## Öne Çıkan Özellikler

- **Kaynağa dayalı üretim:** Dil modeli parametrik belleğine bırakılmaz; yanıt yalnızca erişilen literatür bölümleriyle sınırlandırılır.
- **Hibrit bilgi erişimi:** Anlamsal (dense) vektör araması + BM25 anahtar kelime araması + HyDE (sorgunun varsayımsal cevaplarla zenginleştirilmesi).
- **İki aşamalı arama:** Kosinüs benzerliğiyle hızlı aday getirme → cross-encoder reranker ile hassas yeniden sıralama.
- **Çapraz dilli destek:** Sınırlı Türkçe kaynak, sorgunun İngilizceye çevrilmesiyle İngilizce literatürle güçlendirilir; her dil havuzu kendi dilinde ayrı reranklanır.
- **Cümle düzeyinde kaynak atfı:** Her iddia kaynak pasajla eşleştirilip doğrulanır ve tıklanabilir biçimde gösterilir.
- **Güvenlik odaklı akış:** Erişim zayıf olduğunda sistem uydurmak yerine kullanıcıya takip sorusu sorar ya da güvenli biçimde geri çekilir. Kapsam dışı sorular reddedilir.
- **Rol ayrımı:** Veteriner hekim ve üretici rolleri için yanıt dili ve içeriği farklılaşır.

---

## Mimari

```
        Kullanıcı Sorusu
              │
        Kapsam Kontrolü ──(kapsam dışı)──► Reddet
              │
        Hibrit Erişim  (HyDE + BM25 + dense + çapraz dil)
              │
        Cross-encoder Reranker
              │
        ┌──── KARAR KAPISI ─────────────────────────┐
        │ dense düşük   → güvenli geri dönüş         │
        │ rerank düşük  → kullanıcıya takip sorusu   │
        │ ikisi yeterli → yanıt üretimi              │
        └──────────────┬─────────────────────────────┘
                       │
        Yanıt Üretimi → Cümle Düzeyi Atıf → Güven → Yanıt + Kaynaklar
```

Tüm akış **LangGraph** ile bir durum makinesi olarak modellenmiştir.

---

## Teknoloji Yığını

| Katman | Teknolojiler |
|---|---|
| Sunucu (Backend) | Python, FastAPI, LangGraph, Pydantic |
| Belge işleme | Docling, parent-child chunking |
| Gömme (Embedding) | BGE-M3 (1024 boyut, çok dilli) |
| Vektör veritabanı | Qdrant (kosinüs benzerliği) |
| Seyrek arama | BM25 |
| Yeniden sıralama | BGE-reranker-v2-m3 (cross-encoder) |
| Dil modelleri | gpt-oss-120b, Llama-3.3-70B (Groq üzerinden) |
| Arayüz (Frontend) | Next.js, React, TypeScript, Tailwind CSS, shadcn/ui |

---

## Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.10+
- Node.js 18+
- Docker (Qdrant için)
- LLM sağlayıcısı API anahtarı (Groq / OpenRouter)

### 1) Vektör veritabanı (Qdrant)
```bash
docker compose up -d
```

### 2) Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
cp ../.env.example ../.env   # API anahtarlarını .env içine girin
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
> İlk çalıştırmada BGE-M3 ve BGE-reranker modelleri indirilir.

### 3) Frontend
```bash
cd frontend
npm install
# .env.local içine: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```
Arayüz: `http://localhost:3000`

> **Not:** Kaynak belgeler (veteriner literatürü PDF'leri) telif nedeniyle bu depoya dâhil **değildir**. Bilgi tabanını oluşturmak için kendi kaynaklarınızı `backend/data/` altına ekleyip ingestion adımını çalıştırmanız gerekir.

---

## Değerlendirme

Sistem, gerçek kullanım senaryolarını (günlük dille yazılmış sorular, acil durumlar, kapsam dışı sorular, hatalı girdiler) içeren 50 soruluk bir kümeyle değerlendirilmiştir. Bulgular, iyi kapsanan konularda sistemin kaynağa dayalı ve doğru yanıtlar ürettiğini; sınırlı kaynak veya belirsiz girdi durumlarında ise yanlış bilgi üretmek yerine temkinli davrandığını göstermektedir. Ayrıntılı analiz ve değerlendirme betikleri `backend/eval/` altındadır.

---

## Proje Yapısı

```
backend/    FastAPI sunucusu, LangGraph akışı, RAG hattı, değerlendirme
frontend/   Next.js arayüzü (sohbet + hata ayıklama paneli)
DECISIONS.md  Mimari kararlar (ADR)
```

---

## Yazar

**İsmet Can Çelenler** — Balıkesir Üniversitesi, Mühendislik Fakültesi, Bilgisayar Mühendisliği Bölümü
Bitirme Projesi · Danışman: **Doç. Dr. Fatih Aydın** · 2026
