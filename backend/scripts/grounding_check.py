"""
Groundedness check — yanit gercekten chunk'lardan mi geliyor?

Bir case icin:
  1. Sorguyu calistir (sadece retrieval, generator atla)
  2. Eval JSON'undan o case'in yanitini al
  3. Yanittaki spesifik claim'leri (sayilar, dozajlar, terimler) cikar
  4. Her claim icin top-3 chunks'ta ara
  5. Eslesmeyen claim = halüsinasyon adayi

Kullanim:
  python scripts/grounding_check.py <case_id> [report_json]
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
from app.rag.query_translator import enrich_query
from app.rag.reranker import rerank


def _ascii(s):
    return str(s).encode("ascii", "replace").decode("ascii")


def get_chunks_for_query(query, top_k=3):
    """Retriever node'un yaptigi seyi calistir, top-K chunks dondur."""
    enriched = enrich_query(query)
    v_orig = embed_single(query)
    dense_orig = search(query_vector=v_orig, limit=30, score_threshold=0.25)
    dense_enr = []
    if enriched:
        v_enr = embed_single(enriched)
        dense_enr = search(query_vector=v_enr, limit=30, score_threshold=0.25)
    seen = set()
    cands = []
    for r in dense_orig + dense_enr:
        if r.get("score", 0) < 0.30:
            continue
        k = r["text"][:100]
        if k not in seen:
            seen.add(k)
            cands.append(r)
    cands.sort(key=lambda x: x["score"], reverse=True)
    cands = cands[:30]
    rerank_q = f"{query} | {enriched}" if enriched else query
    return rerank(rerank_q, cands, top_k=top_k), enriched


def extract_claims(response):
    """Yanittaki spesifik claim'leri cikar."""
    claims = {
        "numbers_with_unit": set(),
        "dosages": set(),
        "english_terms": set(),
        "drug_names": set(),
        "specific_terms": set(),
    }

    # 1. Sayilar + birim (3 mg/kg, 0.4 mEq/L, 38-39 °C, 1400 umol/L vs.)
    for m in re.finditer(r"[\d.,]+\s*[-–]?\s*[\d.,]*\s*(mg/kg|mg/dl|mmol/l|mmol/L|mEq/L|μmol/L|umol/L|umol/l|g/l|°C|°F|kg|mL|ml|hr|saat|gun|hafta|ay|yil|day|week|month)\b", response, re.IGNORECASE):
        claims["numbers_with_unit"].add(m.group().strip())

    # 2. Ingilizce terim (TR yanitta CIPLAK English kelime)
    en_terms_found = []
    en_terms_list = [
        "ketosis", "hypocalcemia", "milk fever", "hepatic lipidosis", "fatty liver",
        "metritis", "endometritis", "mastitis", "downer cow", "displaced abomasum",
        "BHB", "NEFA", "PTH", "DCAD", "BVDV", "IBR", "BRSV", "BRD",
        "oxytetracycline", "penicillin", "ceftiofur", "florfenicol", "flunixin",
        "Rebhun", "Brachyspira", "Mannheimia", "Mycoplasma", "Pasteurella",
    ]
    for term in en_terms_list:
        if re.search(rf"\b{re.escape(term)}\b", response, re.IGNORECASE):
            en_terms_found.append(term)
    claims["english_terms"] = set(en_terms_found)

    # 3. Ilac/madde adlari (yaygin TR vet ilaclari)
    drug_list = [
        "oksitetrasiklin", "amoksisilin", "seftiofur", "florfenikol", "penisilin",
        "oksitosin", "prostaglandin", "deksametazon", "flunixin", "meloksikem",
        "kalsiyum boroglükonat", "kalsiyum glukonat", "propilen glikol",
        "magnezyum sulfat", "iyodür", "vitamin", "elektrolit",
        "povidon iyot", "rivanol",
    ]
    for d in drug_list:
        if re.search(rf"\b{re.escape(d)}\b", response, re.IGNORECASE):
            claims["drug_names"].add(d)

    # 4. Spesifik teknik terimler
    specific_list = [
        "1,25-dihidroksivitamin", "1,25-dihydroxyvitamin", "calcitriol",
        "subkütan", "intravenöz", "intramusküler",
        "rolling", "toggle pin", "trokar",
        "blackleg", "kara hastalik", "tetanoz",
    ]
    for s in specific_list:
        if re.search(rf"\b{re.escape(s)}\b", response, re.IGNORECASE):
            claims["specific_terms"].add(s)

    return claims


def check_in_chunks(claim, chunks_text):
    """Claim'in chunks icinde gecip gecmedigini kontrol et."""
    claim_lower = claim.lower()
    chunks_lower = chunks_text.lower()
    # Direkt arama
    if claim_lower in chunks_lower:
        return True, "exact"
    # Sayi varsa, sayi etrafindaki rakami ayri ara
    nums = re.findall(r"[\d.,]+", claim)
    if nums:
        # En az 1 sayi chunks'ta gecmeli (yakin baglamda)
        for num in nums:
            if num and len(num) >= 2 and num in chunks_lower:
                return True, f"partial(num={num})"
    return False, None


def main():
    if len(sys.argv) < 2:
        print("Kullanim: python scripts/grounding_check.py <case_id> [report_json]")
        sys.exit(1)

    case_id = sys.argv[1]
    report_path = (
        sys.argv[2] if len(sys.argv) > 2
        else "eval/reports/20260521_102532__phase2_full50.json"
    )

    data = json.load(open(report_path, encoding="utf-8"))
    case = next((c for c in data["results"] if c["id"] == case_id), None)
    if not case:
        print(f"Case {case_id} bulunamadi.")
        sys.exit(1)

    question = case["question"]
    response = case["response"]

    print(f"=== CASE: {case_id} ===")
    print(f"Question: {_ascii(question)}")
    print(f"Response length: {len(response)} char")
    print(f"\n=== TOP-3 CHUNKS (retriever + reranker yeniden calistirildi) ===\n")

    chunks, enriched = get_chunks_for_query(question, top_k=3)
    chunks_text = ""
    for i, c in enumerate(chunks, 1):
        meta = c.get("metadata", {})
        print(f"[Chunk {i}] dense={c.get('score', 0):.3f}  "
              f"rerank_logit={c.get('rerank_logit', 0):.3f}  "
              f"sigmoid={c.get('rerank_score', 0):.3f}")
        print(f"  source: {meta.get('source_title', '?')}")
        print(f"  {_ascii(c.get('text', '')[:300])}...")
        chunks_text += " " + c.get("text", "")
        print()

    print(f"Chunks toplam karakter: {len(chunks_text)}\n")

    # Claim extraction
    claims = extract_claims(response)

    print("=" * 70)
    print("YANIT'TAN CIKARLAN SPESIFIK CLAIM'LER vs CHUNKS")
    print("=" * 70)

    grounded = 0
    ungrounded = 0
    suspicious = []

    for cat, items in claims.items():
        if not items:
            continue
        print(f"\n--- {cat} ({len(items)} adet) ---")
        for claim in sorted(items):
            found, mode = check_in_chunks(claim, chunks_text)
            mark = "OK   " if found else "MISS "
            mode_str = f"[{mode}]" if mode else ""
            print(f"  {mark} {_ascii(claim):40} {mode_str}")
            if found:
                grounded += 1
            else:
                ungrounded += 1
                suspicious.append((cat, claim))

    print("\n" + "=" * 70)
    print(f"OZET: {grounded} grounded, {ungrounded} ungrounded (halusinasyon adayi)")
    print(f"Groundedness rate: {100*grounded/(grounded+ungrounded):.1f}%" if (grounded+ungrounded) > 0 else "N/A")
    print("=" * 70)
    if suspicious:
        print("\nHALUSINASYON ADAYLARI (chunks'ta bulunamadi):")
        for cat, claim in suspicious:
            print(f"  [{cat}] {_ascii(claim)}")


if __name__ == "__main__":
    main()
