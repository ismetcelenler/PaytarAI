"""PaytarAI — LangGraph Nodes Package.

v4 mimari: critic_node kaldirildi. Gerekceler:
  - `grounded`        -> sentence_grounding (LettuceDetect token-level) yapiyor
  - `answer_relevant` -> retrieval rerank skoru zaten gosteriyor
  - `disclaimer`      -> generator prompt'unda hard rule
  - `emergency`       -> generator prompt'unda hard rule
  - `lay_language`    -> generator prompt'unda hard rule (producer modu)

critic.py dosyasi gelecekte (rule-only safety check vb.) yeniden devreye almak
icin korunuyor, ama mevcut workflow'a baglanmiyor.
"""

from app.graph.nodes.scope_check import scope_check_node
from app.graph.nodes.compress import compress_node
from app.graph.nodes.retriever import retriever_node
from app.graph.nodes.generator import generator_node
from app.graph.nodes.sentence_grounding import sentence_grounding_node
from app.graph.nodes.confidence import confidence_node

__all__ = [
    "scope_check_node",
    "compress_node",
    "retriever_node",
    "generator_node",
    "sentence_grounding_node",
    "confidence_node",
]
