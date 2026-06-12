"""
PaytarAI — OpenRouter smoke test

openai/gpt-oss-120b:free modeliyle baglantiyi dogrular.
Hem standart non-stream hem JSON output testi yapar.
"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from langchain_openai import ChatOpenAI
from app.config import settings


def main():
    if not settings.openrouter_api_key:
        print("[FAIL] OPENROUTER_API_KEY .env'de yok")
        return 1

    print("=" * 70)
    print("  OpenRouter Sanity Test — openai/gpt-oss-120b:free")
    print("=" * 70)
    print()

    llm = ChatOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-oss-120b:free",
        temperature=0,
        max_tokens=300,
        # OpenRouter'in "models" gerektirdigi extra header'lar (opsiyonel, gosterim icin)
        default_headers={
            "HTTP-Referer": "https://github.com/paytar-ai",
            "X-Title": "PaytarAI Smoke Test",
        },
    )

    # Test 1: basit prompt
    print("[1] Basit prompt testi (Turkce):")
    try:
        resp = llm.invoke("Buyukbas hayvanlarda kolostrum nedir, 2 cumlede ozetle.")
        content = str(resp.content).strip()
        print(f"  Cevap ({len(content)} char):")
        print(f"  {content[:500]}")
        # usage_metadata varsa goster (token sayilari)
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            print(f"  Tokens: {resp.usage_metadata}")
        if hasattr(resp, "response_metadata") and resp.response_metadata:
            rm = resp.response_metadata
            usage = rm.get("token_usage") or rm.get("usage")
            if usage:
                print(f"  Token usage: {usage}")
        print()
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")
        return 1

    # Test 2: JSON output (sentence_grounding gibi)
    print("[2] JSON output testi (sentence grounding patterne benzer):")
    prompt = """Asagidaki yaniti cumlelere bol ve her cumle icin SADECE JSON cevap ver.

YANIT: "Buzagida ishal gorulur. E. coli yaygin etkendir. Veterinerinize danisin."

CIKTI: SADECE JSON, baska metin yazma.
Format:
{
  "sentences": [
    {"text": "...", "type": "specific|generic"}
  ]
}"""
    try:
        resp = llm.invoke(prompt)
        raw = str(resp.content).strip()
        print(f"  Raw ({len(raw)} char): {raw[:400]}")
        # JSON parse dene
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            data = json.loads(m.group())
            print(f"  Parse OK: {len(data.get('sentences', []))} cumle")
        else:
            print(f"  [WARN] JSON bulunamadi raw'da")
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")
        return 1

    print()
    print("=" * 70)
    print("  ✓ OpenRouter calisiyor — gpt-oss-120b:free erisilebilir")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
