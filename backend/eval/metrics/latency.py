"""Latency olcumu — sorgu basina toplam sure."""

import time
from contextlib import contextmanager


@contextmanager
def latency_seconds():
    """Context manager — `with latency_seconds() as t:` kullan, t['seconds'] sonucu verir."""
    result = {"seconds": 0.0}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["seconds"] = round(time.perf_counter() - start, 3)
