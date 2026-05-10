"""
PaytarAI — Deterministic Dosage Calculator

AI-PROMPT.md Section 4.4: LLM ASLA matematik yapmaz.
Tum hesaplamalar Python Decimal modulu ile yapilir.
Float kullanmak YASAKTIR.
"""

from decimal import Decimal, ROUND_HALF_UP


def calculate_dosage(
    weight: Decimal,
    target_dose: Decimal,
    concentration: Decimal,
) -> Decimal:
    """
    Deterministik dozaj hesabi.

    Args:
        weight: Hayvan agirligi (kg)
        target_dose: Hedef doz (mg/kg)
        concentration: Ilac konsantrasyonu (mg/ml)

    Returns:
        Hesaplanan hacim (ml), 2 ondalik basamak

    Raises:
        ValueError: Gecersiz girdi degerleri icin
    """
    if weight <= 0:
        raise ValueError(f"Agirlik pozitif olmalidir: {weight}")
    if target_dose <= 0:
        raise ValueError(f"Hedef doz pozitif olmalidir: {target_dose}")
    if concentration <= 0:
        raise ValueError(f"Konsantrasyon pozitif olmalidir: {concentration}")

    result = (weight * target_dose) / concentration
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def safe_decimal(value: float | int | str) -> Decimal:
    """
    Degeri guvenli sekilde Decimal'e donusturur.
    Float precision hatasini onlemek icin her zaman string uzerinden cast yapar.
    """
    return Decimal(str(value))
