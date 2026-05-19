"""
PaytarAI — Critic Node

Taslak yaniti 5 boyutta dogrular, uyumsuzluk varsa reddeder.
AI-PROMPT.md Section 4.5: Critic max 2 kez reddedebilir.
"""

import re

from app.graph.audit import audit_log


# ---------------------------------------------------------------
# SANITIZE — kozmetik sorunlari LLM cagirmadan temizler
# ---------------------------------------------------------------

_INLINE_CITATION_PATTERNS = [
    r"【\s*Kaynak\s*\d+\s*】",
    r"\[\s*Kaynak\s*\d+\s*\]",
    r"\(\s*Kaynak\s*\d+\s*\)",
    r"【\s*Referans\s*\d+\s*】",
    r"\[\s*Referans\s*\d+\s*\]",
]

_META_PHRASES = [
    "kaynakta doğrudan tedavi önerisi yoktur, sadece tanısal ilişki verilmiştir",
    "kaynakta doğrudan tedavi önerisi yoktur",
    "kaynakta yalnızca tanısal ilişki verilmiştir",
    "kaynaklarda detay yok",
    "kaynakta detay yok",
    "tabloda görüldüğü gibi",
    "tabloda görüldüğü üzere",
    "kaynakta belirtilmemiş",
]


def _sanitize_draft(draft: str, user_role: str) -> str:
    """Kozmetik sorunlari LLM olmadan duzeltir."""
    cleaned = draft

    # 1. Inline [Kaynak N] / 【Kaynak N】 etiketlerini sil (her iki rol icin)
    for pat in _INLINE_CITATION_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # 2. Meta-yorum cumlelerini sil (vet & uretici)
    for phrase in _META_PHRASES:
        cleaned = re.sub(re.escape(phrase) + r"[.,;]?\s*", "", cleaned, flags=re.IGNORECASE)

    # 3. Uretici modunda kaynak satirini ve "Rebhun's" gibi kitap adlarini sil
    if user_role == "producer":
        # "Kaynak: ..." satirini tamamen sil
        cleaned = re.sub(r"(?im)^\s*Kaynak\s*[:：].*$", "", cleaned)
        cleaned = re.sub(r"(?im)^\s*Referans\s*[:：].*$", "", cleaned)
        # Cumle icinde gecen kitap adlarini sil
        cleaned = re.sub(r"Rebhun'?s?[^,.\n]*", "", cleaned, flags=re.IGNORECASE)

    # 4. Cift bosluklari ve fazla bos satirlari topla
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    return cleaned


# Critic kontrol fonksiyonlari

def _check_source_citation(draft: str, docs: list[dict], user_role: str = "veterinarian") -> str | None:
    """Vet: sonda kaynak atfi gereklidir. Uretici: bu kontrol gecerli degil (sanitize halleder)."""
    if user_role == "producer":
        return None

    # Vet — sondaki kaynak satiri gereklidir; inline/meta sanitize'da temizlendi
    citation_markers = ["kaynak:", "kaynak :", "source:", "referans:"]
    has_citation = any(marker in draft.lower() for marker in citation_markers)
    if not has_citation and docs:
        return "Yanitin sonunda kaynak atfi yok. Sonuna tek satir 'Kaynak: [Kitap Adi], bolum' ekle."
    return None


def _check_hallucination(draft: str, docs: list[dict]) -> str | None:
    """
    Halusinasyon kontrolu — normalize edilmis sayisal deger karsilastirmasi.
    Format farki (500-mL vs 500 ml) gormezden gelinir.
    Gercek hatalar (22 mg/kg vs 220 mg/kg) yakalanir.
    """
    import re

    def extract_numbers(text: str) -> set[float]:
        """Metinden tum sayisal degerleri cikar (birim yok say)."""
        raw = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
        numbers = set()
        for r in raw:
            try:
                val = float(r)
                # Cok kucuk (0, 1, 2) veya cok buyuk sayfalar/yillar filtrele
                if 0.01 <= val <= 5000 and val not in {15, 2025, 2026}:
                    numbers.add(val)
            except ValueError:
                pass
        return numbers

    if not docs:
        return None

    # Yanittaki ve kaynaklardaki sayilari cikar
    draft_nums = extract_numbers(draft)
    source_text = " ".join(d["text"] for d in docs)
    source_nums = extract_numbers(source_text)

    if not draft_nums:
        return None

    # Yanittaki her sayi icin kaynakta yakin deger var mi kontrol et
    suspicious = []
    for num in draft_nums:
        # Kaynakta birebir veya %10 toleransla eslesme ara
        found = False
        for src_num in source_nums:
            if src_num == 0:
                continue
            ratio = abs(num - src_num) / src_num
            if ratio < 0.10:  # %10 tolerans
                found = True
                break
        if not found:
            suspicious.append(str(num))

    # 3'ten fazla eslesmeyen sayi varsa reddet (1-2 tane normal olabilir)
    if len(suspicious) > 3:
        return f"Yanittaki {len(suspicious)} sayisal deger kaynaklarda dogrulanamadi. Kaynakta olmayan deger kullanma."

    return None


def _check_role_compliance(draft: str, user_role: str) -> str | None:
    """Rol bazli uyumluluk kontrolu."""
    if user_role == "producer":
        # Uretici modunda receteli ilac, dozaj veya teknik terim olmamali
        prescription_markers = [
            # Dozaj birimleri
            "mg/kg", "ml/kg", "mg/ml", "iu/kg", "mg/gün", "ml/gün",
            # Uygulama yollari (EN)
            "iv ", "i.v.", "intramuscular", "subcutaneous", "intravenous", "intramammary",
            # Uygulama yollari (TR)
            "intravenöz", "intramüsküler", "subkütan", "kas içi enjeksiyon", "damar içi enjeksiyon",
            # Receteli ilac adlari
            "penisilin", "penicillin", "oksitetrasiklin", "oxytetracycline",
            "ampisilin", "ampicillin", "deksametazon", "dexamethasone",
            "flunixin", "meloksikem", "meloxicam",
            # Karmasik tibbi terimler / Latince
            "peritonitis", "endometritis", "septisemi", "septik şok",
            "musculoskeletal", "polyarthritis", "hipokalsemi", "hipomagnezemi",
            "recumbency", "palpasyon", "primiparous", "multiparous",
            "anoreksi", "subinvolüsyon", "ruminal tympani", "asidoz", "ketozis",
        ]
        violations = [m for m in prescription_markers if m in draft.lower()]
        if violations:
            return f"Uretici modunda teknik dozaj/uygulama/ilac/tibbi terim kullanildi: {violations}. Sade Turkce ile yeniden yaz, tibbi terim parantez icinde bile yazma."

        # Tablo (markdown) yasak — uretici tablo gormez
        # En az 2 satir | ile basliyorsa veya | ... | --- ... --- | kalibi varsa tablo say
        lines_with_pipe = [ln for ln in draft.splitlines() if ln.strip().startswith("|") and "|" in ln.strip()[1:]]
        if len(lines_with_pipe) >= 2:
            return "Uretici yanitinda tablo kullanildi. Tablo yerine 2-3 cumlelik sade aciklama yaz."

    elif user_role == "veterinarian":
        # Veteriner modunda cok basit dil kontrolu (istege bagli)
        pass

    return None


def _check_emergency_flag(draft: str, docs: list[dict]) -> str | None:
    """Acil durumlar icin uyari kontrolu."""
    # Sadece gercekten hayati tehlike belirten terimler
    emergency_keywords = [
        "fatal", "death", "emergency", "life-threatening",
    ]

    source_text = " ".join(d["text"] for d in docs).lower()
    source_has_emergency = any(kw in source_text for kw in emergency_keywords)

    # Yanittaki acil uyari varyantlari
    draft_lower = draft.lower()
    warning_markers = ["acil", "hemen veteriner", "hayati tehlike", "tehlike", "uyarı"]
    draft_has_warning = any(m in draft_lower for m in warning_markers)

    if source_has_emergency and not draft_has_warning:
        return "Kaynaklar acil/tehlikeli durum belirtiyor ancak yanit acil uyari icermiyor. ACİL uyarisi ekle."

    return None


def _check_disclaimer(draft: str, user_role: str) -> str | None:
    """Uretici modunda zorunlu disclaimer kontrolu."""
    if user_role == "producer":
        disclaimer_markers = ["karar destegi", "veteriner hekime danisin", "veteriner", "disclaimer"]
        has_disclaimer = any(m in draft.lower() for m in disclaimer_markers)
        if not has_disclaimer:
            return "Uretici modunda zorunlu disclaimer eksik. Yanitinin sonuna uyari ekle."
    return None


def critic_node(state: dict) -> dict:
    """
    Critic node — taslak yaniti 5 boyutta dogrular.

    Max 2 reddetme hakki vardir. 3. denemede fallback yanit kullanilir.
    """
    raw_draft = state.get("draft_response", "")
    docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")
    attempts = state.get("critic_attempts", 0)

    # SANITIZE: kozmetik sorunlari LLM cagirmadan temizle
    draft = _sanitize_draft(raw_draft, user_role)
    state["draft_response"] = draft  # generator retry alirsa temizlenmis halini gormesin diye

    # Max 2 red — 3. denemede kabul et
    if attempts >= 2:
        state["final_response"] = draft
        state["response_status"] = "accepted_after_max_retries"
        audit_log(state, "critic_max_retries", reason="2 red sonrasi kabul edildi")
        return state

    # Fallback yaniti (LLM hatasi, rate limit vs.) ise critic atla
    if state.get("response_status") == "fallback":
        state["final_response"] = draft
        state["response_status"] = "accepted"
        audit_log(state, "critic_skip_fallback", reason="Generator fallback — critic atlanir")
        return state

    # 5 kontrol calistir
    rejections = []

    checks = [
        _check_source_citation(draft, docs, user_role),
        _check_hallucination(draft, docs),
        _check_role_compliance(draft, user_role),
        _check_emergency_flag(draft, docs),
        _check_disclaimer(draft, user_role),
    ]

    rejections = [r for r in checks if r is not None]

    if rejections:
        state["critic_rejection_reasons"] = rejections
        state["critic_attempts"] = attempts + 1
        state["response_status"] = "rejected"

        audit_log(
            state,
            "critic_rejected",
            reason=rejections,
        )
    else:
        state["final_response"] = draft
        state["critic_rejection_reasons"] = []
        state["response_status"] = "accepted"

        audit_log(state, "critic_accepted")

    return state
