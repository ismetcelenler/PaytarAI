import time
from app.rag.qdrant_store import get_qdrant_client
from app.config import settings

def monitor():
    print("Veritabanı Yükleme Monitörü Başlatıldı (Çıkmak için Ctrl+C)\n")
    client = get_qdrant_client()
    
    last_count = -1
    start_time = time.time()
    
    try:
        while True:
            try:
                count_result = client.count(collection_name=settings.qdrant_collection_name)
                current_count = count_result.count
                
                if current_count != last_count:
                    elapsed = int(time.time() - start_time)
                    print(f"[{elapsed} saniye] Güncel Parça (Chunk) Sayısı: {current_count}")
                    last_count = current_count
                
                # Her 5 saniyede bir kontrol et
                time.sleep(5)
            except Exception as e:
                print(f"Qdrant'a bağlanılamadı: {e}")
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nMonitör durduruldu.")

if __name__ == "__main__":
    monitor()
