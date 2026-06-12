# Research — karar destek dokümanları

Bu klasör PaytarAI'nın mimari kararlarını destekleyen araştırma materyalini tutar.
Kod değil, **karar girdisi**: deep search raporları, akademik makale PDF'leri,
benchmark notları, vendor karşılaştırmaları.

## Yapı

```
research/
├── deepsearch/   # ChatGPT/Claude/Gemini deep search raporları (.md tercih edilir)
├── papers/       # arXiv ve benzeri PDF'ler (10+ sayfa ise dosya adında sayfa range belirtin)
└── README.md
```

## İsim verme konvansiyonu

```
YYYY-MM-DD_konu_kisa-baslik.md
```

Örnekler:
- `2026-06-12_reranker_cross-lingual-bias.md`
- `2026-06-12_grounding_lettucedetect-vs-veriCite.md`
- `2026-06-13_critic_remove-vs-keep.md`

## Format tercihi (Claude'un okuma kalitesi)

| Format | Notu |
|---|---|
| `.md` | 🟢 İdeal — başlıklar/link/kod blokları korunur |
| `.txt` | 🟢 Düz okunur ama yapı belirsiz |
| `.pdf` | 🟡 Okunur ama tablo/footer bazen bozulur |
| `.docx` | 🔴 Native okunmaz, convert gerekir |

## İçerik şablonu (deep search raporları için)

```markdown
# [Başlık]

**Tarih**: YYYY-MM-DD
**Soru**: Aslında neyi araştırdığın
**Kaynak**: ChatGPT Deep Research / Claude / Perplexity / Gemini

---

## Özet
[Raporun ana bulguları, 3-5 madde]

## Detay
[Raporun tam metni — markdown olduğu gibi]

## Kaynaklar
- [Link 1]
- [Link 2]
```

## Bu klasör commit'lenir mi?

Evet — kararlara dayanak oldukları için git'te durmaları faydalı. Sadece
private veri (API key, kişisel notlar) eklemeyin.
