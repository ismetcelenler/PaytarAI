"""
LLM-as-judge metric — semantik fact coverage olcumu.

String match yerine bir LLM'e sorar: "Bu yanit su kavrami iceriyor mu (paraphrase
ve sinonim dahil)?". Boylece "memede iltihap" ile "meme iltihabi" anlamca eslesir.

Kullanim:
    from eval.metrics.llm_judge import fact_coverage_llm
    result = fact_coverage_llm(response, expected_facts, question)
"""

import sys
from pathlib import Path

# backend/ sys.path'te olmali
_BACKEND = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from langchain_openai import ChatOpenAI  # noqa: E402

from app.config import settings  # noqa: E402


JUDGE_PROMPT = """Sen bir Turk veteriner asistani yanitini degerlendiriyorsun.

Kullanici sorusu: {question}

Yanitin, beklenen kavrami (paraphrase, sinonim, halk dili karsiligi dahil) iceriyor mu?

Beklenen kavram: {fact}

Yanit:
\"\"\"
{response}
\"\"\"

Tek kelimelik cevap ver: EVET veya HAYIR.
- EVET: Yanit kavrami acik veya orta acik olarak iceriyor / ele aliyor (paraphrase OK)
- HAYIR: Yanit kavrami hic ele almiyor

Cevap:"""


_judge_llm: ChatOpenAI | None = None


def _get_judge() -> ChatOpenAI:
    global _judge_llm
    if _judge_llm is None:
        _judge_llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=10,
        )
    return _judge_llm


def _judge_single(question: str, fact: str, response_text: str) -> bool:
    """Bir fact icin LLM'e sor, evet/hayir don."""
    if not response_text.strip():
        return False

    # "|" ile ayrilan varyantlar OR mantigi — herhangi biri yakalanirsa OK
    # Tum varyantlari tek prompt'a koy ki LLM en uygununu degerlendirsin
    variants = [v.strip() for v in fact.split("|") if v.strip()]
    fact_display = " VEYA ".join(variants) if len(variants) > 1 else fact

    prompt = JUDGE_PROMPT.format(
        question=question,
        fact=fact_display,
        response=response_text[:2000],  # cok uzun yanitlari kirpsin
    )

    try:
        result = _get_judge().invoke(prompt)
        text = str(result.content).strip().upper()
        return text.startswith("EVET") or text.startswith("YES")
    except Exception as e:
        print(f"[llm_judge] hata: {e}")
        return False


def fact_coverage_llm(response_text: str, expected_facts: list[str], question: str = "") -> dict:
    """
    LLM-as-judge ile fact coverage.

    Returns:
        {
            "matched": [...],
            "missed": [...],
            "score": 0.66,
            "method": "llm_judge",
        }
    """
    if not expected_facts:
        return {"matched": [], "missed": [], "score": 1.0, "method": "llm_judge"}

    matched: list[str] = []
    missed: list[str] = []
    for fact in expected_facts:
        ok = _judge_single(question, fact, response_text)
        (matched if ok else missed).append(fact)

    score = len(matched) / len(expected_facts)
    return {
        "matched": matched,
        "missed": missed,
        "score": round(score, 3),
        "method": "llm_judge",
    }
