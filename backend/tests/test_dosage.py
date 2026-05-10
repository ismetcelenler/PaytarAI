"""
PaytarAI — Dosage Calculator Unit Tests

AI-PROMPT.md Section 8: Float precision hatasi Decimal ile onlenir.
Adversarial precision testleri dahil.
"""

from decimal import Decimal

import pytest

from app.tools.dosage_calculator import calculate_dosage, safe_decimal


class TestCalculateDosage:
    """Deterministik dozaj hesaplama testleri."""

    def test_basic_calculation(self):
        """Temel dozaj hesabi: 450kg * 22mg/kg / 200mg/ml = 49.50ml"""
        result = calculate_dosage(
            weight=Decimal("450"),
            target_dose=Decimal("22"),
            concentration=Decimal("200"),
        )
        assert result == Decimal("49.50")

    def test_rounding(self):
        """Yarim yukariya yuvarlama: ROUND_HALF_UP"""
        result = calculate_dosage(
            weight=Decimal("333"),
            target_dose=Decimal("10"),
            concentration=Decimal("100"),
        )
        assert result == Decimal("33.30")

    def test_small_dose(self):
        """Kucuk doz hesabi."""
        result = calculate_dosage(
            weight=Decimal("50"),
            target_dose=Decimal("0.5"),
            concentration=Decimal("100"),
        )
        assert result == Decimal("0.25")

    def test_precision_no_float_error(self):
        """Float precision hatasi olmamali: 0.1 + 0.2 != 0.3 problemi."""
        # float ile: (0.1 + 0.2) * 100 / 1 = 30.000000000000004
        # Decimal ile: 30.00
        weight = Decimal("100")
        dose = Decimal("0.1") + Decimal("0.2")  # 0.3 exact
        conc = Decimal("1")
        result = calculate_dosage(weight, dose, conc)
        assert result == Decimal("30.00")

    def test_zero_weight_raises(self):
        """Sifir agirlik hata vermeli."""
        with pytest.raises(ValueError, match="pozitif"):
            calculate_dosage(Decimal("0"), Decimal("10"), Decimal("100"))

    def test_negative_dose_raises(self):
        """Negatif doz hata vermeli."""
        with pytest.raises(ValueError, match="pozitif"):
            calculate_dosage(Decimal("450"), Decimal("-5"), Decimal("100"))

    def test_zero_concentration_raises(self):
        """Sifir konsantrasyon hata vermeli."""
        with pytest.raises(ValueError, match="pozitif"):
            calculate_dosage(Decimal("450"), Decimal("10"), Decimal("0"))


class TestSafeDecimal:
    """safe_decimal donusum testleri."""

    def test_from_float(self):
        result = safe_decimal(0.1)
        assert result == Decimal("0.1")

    def test_from_int(self):
        result = safe_decimal(450)
        assert result == Decimal("450")

    def test_from_string(self):
        result = safe_decimal("22.5")
        assert result == Decimal("22.5")
