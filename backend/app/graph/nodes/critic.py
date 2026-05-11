"""
PaytarAI — Critic Node

Taslak yaniti 5 boyutta dogrular, uyumsuzluk varsa reddeder.
AI-PROMPT.md Section 4.5: Critic max 2 kez reddedebilir.
"""

from app.graph.audit import audit_log


# Critic kontrol fonksiyonlari

def _check_source_citation(draft: str, docs: list[dict]) -> str | None:
    """Yanit en az bir kaynak referansi icermeli."""
    citation_markers = ["kaynak:", "kaynak :", "source:", "referans:", "sayfa"]
    has_citation = any(marker in draft.lower() for marker in citation_markers)

    if not has_citation and docs:
        return "Yanit hicbir kaynak referansi icermiyor. Her klinik bilginin sonuna kaynak ekle."
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
        # Uretici modunda receteli ilac adi veya dozaj olmamali
        prescription_markers = ["mg/kg", "ml/kg", "iv ", "i.v.", "intramuscular", "subcutaneous"]
        violations = [m for m in prescription_markers if m in draft.lower()]
        if violations:
            return f"Uretici modunda teknik dozaj/uygulama bilgisi kullanildi: {violations}. Sade dilde yeniden yaz."

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
    draft = state.get("draft_response", "")
    docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")
    attempts = state.get("critic_attempts", 0)

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
        _check_source_citation(draft, docs),
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
