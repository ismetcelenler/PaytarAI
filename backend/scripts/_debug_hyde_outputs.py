"""
fixed_mini.yaml 12 case icin HyDE ciktilarini goster.

Her case icin:
  - Original soru
  - HyDE'nin urettigi hayali cevap
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import yaml
from app.rag.hyde import generate_hyde


DATASET = BACKEND_DIR / "eval/datasets/fixed_mini.yaml"


def get_user_question(case: dict) -> str:
    if "messages" in case and case["messages"]:
        for m in reversed(case["messages"]):
            if m.get("role") == "user":
                return m["content"]
    return case.get("question", "")


def main():
    with DATASET.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("cases", [])
    print(f"Toplam {len(cases)} case\n")
    print("=" * 100)

    for i, case in enumerate(cases, 1):
        q = get_user_question(case)
        print(f"\n[{i}/{len(cases)}] {case['id']} ({case.get('category', '')}, {case.get('writing_style', '')})")
        print(f"SORU:\n  {q}")
        print(f"\nHyDE CIKTISI:")
        hyde = generate_hyde(q)
        if hyde:
            for line in hyde.split("\n"):
                print(f"  {line}")
        else:
            print("  (None — uretilemedi)")
        print("-" * 100)


if __name__ == "__main__":
    main()
