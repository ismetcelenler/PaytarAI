"""
PaytarAI — Debug Trace Helper

Her node'un detayli input/output kaydini debug_trace listesine ekler.
audit_log'tan farkli: kisa+kararsal degil, FULL icerik (prompt'lar, raw LLM
cevaplari, chunk metinleri). UI panelinde gostermek icin.

Kullanim:
    from app.graph.debug_trace import trace_node
    trace_node(state, "scope_check", input={...}, output={...})
"""

import time
from typing import Any


def trace_node(
    state: dict,
    node: str,
    input: dict[str, Any] | None = None,
    output: dict[str, Any] | None = None,
    latency_ms: float | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Bir node'un detayli izini state['debug_trace']'e ekler."""
    if "debug_trace" not in state or state["debug_trace"] is None:
        state["debug_trace"] = []

    entry = {
        "node": node,
        "ts": time.time(),
        "input": input or {},
        "output": output or {},
    }
    if latency_ms is not None:
        entry["latency_ms"] = round(latency_ms, 1)
    if meta:
        entry["meta"] = meta
    state["debug_trace"].append(entry)


def trim_text(s: Any, limit: int = 1500) -> str:
    """LLM prompt/cevap gibi uzun stringler icin guvenli truncate."""
    if not isinstance(s, str):
        s = str(s)
    if len(s) <= limit:
        return s
    return s[:limit] + f"... [+{len(s) - limit} char]"
