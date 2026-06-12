"""
Turk-LettuceDetect benchmark — gercek inference time + label kalitesi.

3 senaryo:
  1) Turkce "bloat" ornegi (user'in bizzat paylastigi):
     Cumle 4: "5 ayirici tani sayilmis" — chunk'ta sadece 1'i var → asagi 4'u hallucination
     Cumle 5: "yonca + sol bogur + hizli sisme" → chunk'ta destekleniyor

  2) Ingilizce kisa hallucination ornegi: tarih supported, kisi adi/yukseklik hallucination

  3) Tum yanit-supported (sanity check)
"""

from __future__ import annotations
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

print("=" * 90)
print("  Turk-LettuceDetect Benchmark — newmindai/lettucedect-210m-eurobert-tr-v1")
print("=" * 90)

print("\n[1/3] Model yukleniyor...")
t0 = time.perf_counter()

from lettucedetect.models.inference import HallucinationDetector

detector = HallucinationDetector(
    method="transformer",
    model_path="newmindai/lettucedect-210m-eurobert-tr-v1",
    device="cuda",
)

load_time = time.perf_counter() - t0
print(f"      Model yuklendi: {load_time:.2f}s")

# ─────────────────────────────────────────────────────────────────
# CASE 1: Turkce bloat ornegi
# ─────────────────────────────────────────────────────────────────
TURKISH_CONTEXT = """Boylece ortaya cikan duragan kopuk iskembe girisini "maskeler" ve hayvanin gegirmesine engel olur. Iskembe buyuk hizla siser, diyaframa baski yapar, akcigerleri, kalbi, ana damarlari sikistirir ve boylece hayvanin bogulmasina ve kalp-damar yetmezligine yol acar. Sigir yere yatar ve olur. Sebep olan besinlerin turune gore, akut kopuklu sindirim bozuklugu (AKSB), mevsime bagli ozellikler gostererek, merada veya ahir ortaminda ortaya cikabilir. Vakalar tek tuk gorulebildigi gibi birden fazla sigir ayni anda rahatsizlanabilir. Genc sigirlar kadar yetiskinlerde de gorulebilir. En belirgin belirtisi iskembenin sirt pozisyonunda hizla genislemesi ve hayvanin once sol bogrunun, sonra sag bogrunun sismesidir. Karin bolgesindeki siskinlik ciddi boyutta ise, hayvanin solumasi hizlanir. Yonca bakimindan zengin bir merada birkac saat otladiktan sonra, sut verme doneminin basindaki bu inegin sol bogru gaz birikmesiyle sismis, hayvan nefes almakta zorlaniyor."""

TURKISH_QUESTION = "Sigirlarda karin siskinliginin nedenleri nelerdir?"

TURKISH_ANSWER = """Karin siskinliginin en sik karsilasilan nedenleri arasinda akut kopuklu sindirim bozuklugu (kopuk bloat), iskembe asidozu, retikuloperitonit, yabanci cisim nedeniyle olusan peritonit ve kronik hazimsizlik yer alir. Ozellikle yonca bakimindan zengin otlanma sonrasi hizli sisme ve sol bogrun sismesi, kopuklu sindirim bozuklugunu dusundurur."""

print("\n[2/3] Turkce 'bloat' ornegi test ediliyor...")
print(f"      Context: {len(TURKISH_CONTEXT)} char")
print(f"      Question: {TURKISH_QUESTION}")
print(f"      Answer:   {TURKISH_ANSWER[:120]}...")

t0 = time.perf_counter()
predictions_tr = detector.predict(
    context=[TURKISH_CONTEXT],
    question=TURKISH_QUESTION,
    answer=TURKISH_ANSWER,
    output_format="spans",
)
tr_time = (time.perf_counter() - t0) * 1000
print(f"\n      Inference: {tr_time:.0f}ms")
print(f"      Predictions: {predictions_tr}")

# ─────────────────────────────────────────────────────────────────
# CASE 2: Ingilizce hallucination
# ─────────────────────────────────────────────────────────────────
EN_CONTEXT = "The Eiffel Tower is located in Paris, France. It was built in 1889."
EN_QUESTION = "When was the Eiffel Tower built?"
EN_ANSWER = "The Eiffel Tower was built in 1889 by Gustave Eiffel for the World's Fair in Paris, standing at 324 meters tall."

print("\n[3/3] Ingilizce hallucination ornegi (multilingual sanity check)...")
print(f"      Context: {EN_CONTEXT}")
print(f"      Answer:  {EN_ANSWER}")
print(f"      Beklenen: '1889' destekleniyor, 'Gustave Eiffel'/'World's Fair'/'324 meters' hallucination")

t0 = time.perf_counter()
predictions_en = detector.predict(
    context=[EN_CONTEXT],
    question=EN_QUESTION,
    answer=EN_ANSWER,
    output_format="spans",
)
en_time = (time.perf_counter() - t0) * 1000
print(f"\n      Inference: {en_time:.0f}ms")
print(f"      Predictions: {predictions_en}")

# ─────────────────────────────────────────────────────────────────
# OZET
# ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("  OZET")
print("=" * 90)
print(f"  Model yuklenme:   {load_time:.2f}s (sadece bir kere)")
print(f"  Turkce inference: {tr_time:.0f}ms (yanit {len(TURKISH_ANSWER)} char)")
print(f"  Ingilizce inf:    {en_time:.0f}ms (yanit {len(EN_ANSWER)} char)")
print(f"  Mevcut LLM grounding: 35,000-128,000ms (Llama-3.3-70B OpenRouter)")
print(f"  Hizlanma faktoru: ~{128000 / max(tr_time, 1):.0f}x")
print("=" * 90)
