# Türkçe Kaynak Manifest

Qdrant'taki `source_title` (ASCII) ile orijinal Türkçe başlık eşlemesi.
ASCII isimler dosya path safety ve Qdrant payload sadelik için kullanıldı.

| Qdrant `source_title` | Orijinal Türkçe Başlık | Orijinal Dosya | İngestion Anahtarı |
|---|---|---|---|
| Buzagi Sagligi | Buzağı Sağlığı | buzağı sağlığı.pdf | tr01 |
| Buyukbas Hastaliklari El Kitabi | Büyükbaş Hastalıkları El Kitabı | büyükbaş hastalıkları el kitabı.pdf | tr02 |
| Buyukbas Hayvan Yetistiriciligi | Büyükbaş Hayvan Yetiştiriciliği | Büyükbaş Hayvan Yetiştiriciliği.pdf | tr03 |
| Sigir Besiciligi - Ciftci Egitim Serisi | Sığır Besiciliği — Çiftçi Eğitim Serisi | sığır besiciliği-çiftçi eğitim serisi.pdf | tr04 |
| Sut Sigirlarinin Bakimi - Aziz Ozturk | Süt Sığırlarının Bakımı — Aziz Öztürk | süt sığırlarının bakımı - aziz öztürk.pdf | tr05 |
| Pratik Sigircilik | Pratik Sığırcılık | pratik sığırcılık.pdf | tr06 |
| Amasya DSYB Yayini | Amasya DSYB Yayını (014) | Amasya_DSYB_Yayin_014.pdf | tr07 |

## İlişkilendirme

- **Tek doğru kaynak**: `backend/scripts/ingest_tr_sources.py` içindeki `SOURCES` dict
- Yeni PDF eklerken o dict'e yeni bir satır ekle, `MANIFEST.md` dosyasını da güncelle
- Orijinal Türkçe dosyalar `C:\Projects\Github_Repo\Bitirme_PaytarAI\RAG ham döküman\` altında
- ASCII kopyalar `backend/data/sources/tr/` altında (Docling/PyMuPDF path safety için)

## Qdrant Payload

Her chunk'ın metadata'sında:
- `source_title`: ASCII başlık (örn. "Buzagi Sagligi")
- `source_file`: ASCII dosya adı (örn. "tr01_buzagi_sagligi.pdf")
- `original_title`: Orijinal Türkçe başlık (2026-06-10 sonrası eklendi) (örn. "Buzağı Sağlığı")
- `language`: "tr" veya "en"
- `parent_text`: Üst chunk metni
- `text`: Child chunk metni (embed edilen)
- `chunk_index`: Sıra numarası
- `chunk_total`: Toplam chunk sayısı
- `total_pages`: PDF sayfa sayısı

UI tarafında kaynak gösterirken **`original_title`** kullanılabilir (Türkçe doğru gösterim için).
