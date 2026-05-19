import sys
import asyncio
sys.stdout.reconfigure(encoding='utf-8')

from app.graph.nodes.retriever import retriever_node

def debug_query():
    state = {
        "messages": [{"role": "user", "content": "hayvanım yere düştü kalkamıyor"}],
        "enriched_query": "",
        "retrieved_docs": [],
        "retrieval_similarity_score": 0.0,
        "critic_attempts": 0,
        "response_status": ""
    }
    
    print("1. Orijinal Sorgu:", state["messages"][0]["content"])
    
    # Arama ve Çeviri
    state = retriever_node(state)
    
    print("\n2. Zenginleştirilmiş Sorgu (Translator Çıktısı):")
    print(state.get("enriched_query", ""))
    
    print("\n3. Qdrant Benzerlik Skoru:")
    print(state.get("retrieval_similarity_score", 0))

    
    print("\n4. Bulunan Dökümanlar:")
    for i, doc in enumerate(state["retrieved_docs"]):
        print(f"\n--- DOC {i+1} ---")
        print(f"Skor: {doc.get('score', 0)}")
        text = doc.get("text", "")
        print(text[:500] + "...")

if __name__ == "__main__":
    debug_query()
