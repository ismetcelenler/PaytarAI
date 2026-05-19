"""Fact coverage — yanit beklenen anahtar gerceklerden kacini iceriyor?"""

import re


def _normalize(text: str) -> str:
    """Kucuk harf, asksizlik, fazla bosluk temizle."""
    t = text.lower()
    t = t.replace("ı", "i").replace("İ", "i")
    t = t.replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ğ", "g").replace("ç", "c")
    t = re.sub(r"\s+", " ", t)
    return t


def fact_coverage(response: str, expected_facts: list[str]) -> dict:
    """
    Yanit metninde beklenen her gercegin gecip gecmedigini kontrol eder.

    Bir gercek string'i icinde "|" ile birden cok varyant verilebilir:
    "süt humması|hipokalsemi|kalsiyum düşüklüğü" — biri eslessin yeter.

    Returns:
        {
            "matched": ["fact1", ...],
            "missed": ["fact3", ...],
            "score": 0.66,
        }
    """
    if not expected_facts:
        return {"matched": [], "missed": [], "score": 1.0}

    norm_response = _normalize(response)
    matched: list[str] = []
    missed: list[str] = []

    for fact in expected_facts:
        variants = [v.strip() for v in fact.split("|")]
        found = any(_normalize(v) in norm_response for v in variants if v)
        if found:
            matched.append(fact)
        else:
            missed.append(fact)

    score = len(matched) / len(expected_facts) if expected_facts else 1.0
    return {"matched": matched, "missed": missed, "score": round(score, 3)}
