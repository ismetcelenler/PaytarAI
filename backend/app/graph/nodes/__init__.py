"""PaytarAI — LangGraph Nodes Package.

v5 mimari (Faz C): LettuceDetect (sentence_grounding) kaldirildi.
  - Yerine `claim_attribution`: Llama-3.3-70B judge ile her cumleyi
    "claim" / "filler" siniflandirir, claim ise chunk_id'ye baglar.
  - Cumle hicbir chunk'a baglanmiyorsa drop edilir.
  - Korunan claim'lerin sonuna inline `[Kaynak N]` etiketi konur.

Gerekce (research/eval_report_2026-06-13.md):
  LettuceDetect 5 soruda 13/13 drop yanlis verdi, %0 precision.
  Token-level classifier disclaimer, atif satiri, liste maddesi, tehlike
  esiklerini halusinasyon saniyordu.

critic.py ve sentence_grounding.py gelecekte yeniden devreye almak icin
korunuyor, ama workflow'a baglanmiyor.
"""

from app.graph.nodes.scope_check import scope_check_node
from app.graph.nodes.compress import compress_node
from app.graph.nodes.retriever import retriever_node
from app.graph.nodes.generator import generator_node
from app.graph.nodes.claim_attribution import claim_attribution_node
from app.graph.nodes.clarification import clarification_node
from app.graph.nodes.confidence import confidence_node

__all__ = [
    "scope_check_node",
    "compress_node",
    "retriever_node",
    "generator_node",
    "claim_attribution_node",
    "clarification_node",
    "confidence_node",
]
