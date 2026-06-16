"""
PaytarAI — Multi-turn Query Composition

Clarification akisinda kullanici onceki sorunu netlestiren bir cevap yaziyor:
    Tur 1 user:  "inegim saman yedi ve hastalandi neden olabilir"
    Tur 1 asst:  [clarification: takip sorulari + olasi nedenler]
    Tur 2 user:  "5 yasinda, dun basladi, kanli diski var ateş 39.8"

Retriever ve scope_check sadece SON user mesajini gormesi durumunda ikinci sorgu
("5 yasinda...") tek basına çok geniş olur → rerank skoru duşer, sistem yine
clarification'a gider veya yanlış chunk gösterir.

Bu helper, son user mesajını ÖNCEKİ ilgili clarification-zincirindeki user
mesajlarıyla birleştirir. Birlesik sorgu hem scope_check analyzer'ina daha iyi
HyDE üretmesi için yardim eder, hem de retriever'ın embed sorgusu zenginleşir.

Algoritma:
  - messages listesini sondan basa tara.
  - Son user mesajini al.
  - Bir oncesi assistant mesaji ise:
      * kind=clarification ise → onun ONCESINDEKI user mesajini da topla,
        loop devam et (clarification zinciri)
      * Aksi halde dur (farkli konu basladi).
  - Toplanan user mesajlarini ters cevirip iki yeni satirla birlestir.
"""

from __future__ import annotations


def compose_user_query(messages: list[dict]) -> str:
    """Multi-turn clarification ile birlesik sorgu uret.

    Args:
        messages: AgentState["messages"] — chronological order.

    Returns:
        Birlesik sorgu metni. Clarification yoksa son user mesajini olduğu gibi
        doner. Liste bossa "".
    """
    if not messages:
        return ""

    collected: list[str] = []
    i = len(messages) - 1
    expect_user = True  # son eleman user beklenir

    while i >= 0:
        m = messages[i]
        if not isinstance(m, dict):
            i -= 1
            continue
        role = m.get("role")
        content = m.get("content", "")

        if expect_user:
            if role == "user" and content:
                collected.append(content)
                expect_user = False  # bir oncesi assistant beklenir
            else:
                # User beklenirken assistant geldi (tutarsizlik) — bırak
                break
        else:
            if role == "assistant" and m.get("kind") == "clarification":
                # Clarification zinciri devam ediyor — bir oncesindeki user'i da al
                expect_user = True
            else:
                # Farkli konu / cevap turu — dur
                break
        i -= 1

    if not collected:
        return ""

    # Toplananlar SON→ESKİ siralı, cevirip eski→yeni yapalim
    collected.reverse()
    if len(collected) == 1:
        return collected[0]
    # Birden fazla user msg birleştir — newlines ile, "→" ile aralarına işaret koy
    return "\n\n".join(collected)
