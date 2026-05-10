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
