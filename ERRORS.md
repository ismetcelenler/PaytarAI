# PaytarAI — Hata Takip ve Çözüm Logu

Bu dosya proje boyunca karşılaşılan hataları, kök nedenlerini ve çözümlerini kaydeder.

---

## Format

```
### ERR-XXX: [Başlık]
**Tarih:** YYYY-MM-DD  |  **Bileşen:** [Backend|Frontend|RAG|LangGraph|Voice|Deploy]  |  **Önem:** [Kritik|Yüksek|Orta|Düşük]

**Hata:** `hata mesajı`

**Bağlam:** Hatanın oluştuğu koşullar

**Kök Neden:** Sebebi

**Çözüm:** Uygulanan düzeltme

**Dosya(lar):** Değiştirilen dosyalar
```

---

### ERR-001: Python Versiyon Uyumsuzluğu
**Tarih:** 2026-05-10  |  **Bileşen:** Backend  |  **Önem:** Orta

**Hata:** `ERROR: Package 'paytar-ai-backend' requires a different Python: 3.10.9 not in '>=3.11'`

**Bağlam:** `pyproject.toml`'da `requires-python = ">=3.11"` tanımlanmıştı, ancak sistemde Python 3.10.9 kurulu.

**Kök Neden:** Geliştirme ortamındaki Python versiyonu kontrol edilmeden pyproject.toml yazıldı.

**Çözüm:** `requires-python` değeri `">=3.10"` olarak güncellendi.

**Dosya(lar):** `backend/pyproject.toml`

---

### ERR-002: Windows cp1254 Encoding — Emoji Hatası
**Tarih:** 2026-05-10  |  **Bileşen:** Backend  |  **Önem:** Düşük

**Hata:** `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f404' in position 0`

**Bağlam:** FastAPI startup'ta `print()` ile emoji kullanıldı. Windows konsolunun varsayılan encoding'i cp1254, emoji desteklemiyor.

**Kök Neden:** Windows PowerShell varsayılan olarak cp1254 (Türkçe) encoding kullanır, UTF-8 emoji karakterleri encode edilemez.

**Çözüm:** `print()` içindeki emoji karakterleri ASCII-safe metinlerle değiştirildi.

**Dosya(lar):** `backend/app/main.py`

---

### ERR-003: Qdrant CollectionInfo — vectors_count Attribute Hatasi
**Tarih:** 2026-05-10  |  **Bilesen:** RAG  |  **Onem:** Dusuk

**Hata:** `AttributeError: 'CollectionInfo' object has no attribute 'vectors_count'`

**Baglam:** Pipeline basarili calistiktan sonra `get_collection_info()` cagrisinda hata aldi.

**Kok Neden:** Yeni Qdrant client surumleri `CollectionInfo` objesinden `vectors_count` field'ini kaldirmis.

**Cozum:** `vectors_count` satirı silindi, sadece `points_count` kullanildi.

**Dosya(lar):** `backend/app/rag/qdrant_store.py`

---

### ERR-004: Qdrant Filtre — prescription_required Alani Yok
**Tarih:** 2026-05-10  |  **Bilesen:** RAG/LangGraph  |  **Onem:** Yuksek

**Hata:** Uretici modunda chat endpoint 500 hatasi verdi.

**Baglam:** Retriever node'da `prescription_required=False` filtresi uygulaniyordu, ancak chunk metadata'sinda bu alan henuz tanimli degil.

**Kok Neden:** Chunk metadata'sina `prescription_required` field'i eklenmemisti, Qdrant var olmayan field'a filtre uygulayinca hata verdi.

**Cozum:** Filtre gecici olarak kaldirildi. Rol bazli icerik kontrolu generator prompt'a birakildi. Ileride dokuman metadata'sina `prescription_required` eklendikce filtre aktiflestirilecek.

**Dosya(lar):** `backend/app/graph/nodes/retriever.py`

---

### ERR-005: Groq Rate Limit (429) ve Critic Döngüsü
**Tarih:** 2026-05-11  |  **Bileşen:** LangGraph/Generator  |  **Önem:** Yüksek

**Hata:** `Error code: 429 - Rate limit reached for model llama-3.3-70b-versatile...`

**Bağlam:** Yoğun E2E testleri sırasında Groq'un günlük ücretsiz kullanım limiti (100K token) dolduğunda, Generator node'u 429 hatası fırlatarak fallback yanıtı (ham kaynak metni) döndürüyordu.

**Kök Neden:** Fallback olarak dönülen ham metin, formata veya referans kurallarına uymadığı için Critic tarafından reddediliyordu. Bu durum, Generator'ın 429 hatası almasına rağmen tekrar tekrar çalışmasına ve token limitlerinin daha da aşılmasına yol açıyordu.

**Çözüm:** Critic node'una bir kontrol eklendi: Eğer gelen yanıt `fallback` durumundaysa, Critic kontrolleri atlanarak yanıt (retry yapılmadan) direkt kabul ediliyor.

**Dosya(lar):** `backend/app/graph/nodes/critic.py`
