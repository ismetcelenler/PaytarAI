"""
Retrieval kalitesi olcumu.

Iki mod:
1. expected_sources DOLU ise -> source title eslesmesi (eski mantik)
2. expected_sources BOS ise   -> top_score >= threshold yeterli (kaynaktan bagimsiz)

Out-of-scope sorgular icin retrieval'in zayif olmasi BEKLENIR — bunu eval YAML'inda
`expect_retrieval_fail: true` flag'i ile belirtiriz.
"""

SIMILARITY_OK_THRESHOLD = 0.45


def retrieval_precision(
    retrieved_docs: list[dict],
    expected_sources: list[str],
    top_k: int = 3,
    expect_retrieval_fail: bool = False,
    similarity_threshold: float = SIMILARITY_OK_THRESHOLD,
) -> dict:
    """
    Getirilen dokumlarin kalitesini olc.

    - expected_sources varsa: hangi sourcelar top-K icinde, ne kadari kapsanmis
    - expected_sources yoksa: top_score >= threshold mi
    - expect_retrieval_fail True ise: tersi (out-of-scope sorgular icin)

    Returns:
        {
            "mode": "source_match" | "threshold" | "expect_fail",
            "top_k": 3,
            "found_sources": [...],     # sadece source_match modunda anlamli
            "missing_sources": [...],
            "score": 1.0,
            "top_score": 0.62,
        }
    """
    top_docs = retrieved_docs[:top_k]
    top_score = float(top_docs[0].get("score", 0.0)) if top_docs else 0.0

    if expect_retrieval_fail:
        # Out-of-scope — retrieval BASARILI olmamali (sistem "bilmiyorum" demeli)
        score = 1.0 if top_score < similarity_threshold else 0.0
        return {
            "mode": "expect_fail",
            "top_k": top_k,
            "found_sources": [],
            "missing_sources": [],
            "score": score,
            "top_score": round(top_score, 3),
        }

    if expected_sources:
        # Spesifik kaynak bekleniyor
        retrieved_titles = [
            str(d.get("metadata", {}).get("source_title", "")).lower() for d in top_docs
        ]
        found: list[str] = []
        missing: list[str] = []
        for src in expected_sources:
            src_lower = src.lower()
            if any(src_lower in title for title in retrieved_titles):
                found.append(src)
            else:
                missing.append(src)
        score = len(found) / len(expected_sources)
        return {
            "mode": "source_match",
            "top_k": top_k,
            "found_sources": found,
            "missing_sources": missing,
            "score": round(score, 3),
            "top_score": round(top_score, 3),
        }

    # Genel mod — sadece top_score yeterli mi
    score = 1.0 if top_score >= similarity_threshold else 0.0
    return {
        "mode": "threshold",
        "top_k": top_k,
        "found_sources": [],
        "missing_sources": [],
        "score": score,
        "top_score": round(top_score, 3),
    }
