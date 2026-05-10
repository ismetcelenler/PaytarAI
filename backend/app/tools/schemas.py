"""
PaytarAI — Tool Output Schemas

AI-PROMPT.md Section 4.4: DosageToolOutput Pydantic modeli.
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class DosageToolOutput(BaseModel):
    """Dozaj araci ciktisi. Critic ve UI tarafindan dogrulanir."""

    ingredient: str
    dose_mg_per_kg: Decimal
    calculated_volume_ml: Decimal
    administration_route: str
    contraindications: list[str]
    withdrawal_period_milk: str | None = None
    withdrawal_period_meat: str | None = None
    source_title: str
    source_page: int
    evidence_confidence: Literal["high", "medium", "low", "insufficient"]

    class Config:
        json_encoders = {Decimal: str}
