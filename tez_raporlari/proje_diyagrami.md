# PaytarAI — Sistem Diyagramları

**Tarih:** 2026-05-21
**Faz:** Phase 2 (BGE-reranker entegre)

Mermaid bloklarını VS Code'da "Markdown Preview" ile veya GitHub üzerinde açarsan render olur.

---

## 1. Üst Düzey Sistem Mimarisi

```mermaid
flowchart LR
    subgraph Client["İstemci Katmanı"]
        UI["Web UI<br/>(Vite + React)<br/>:5173"]
        Voice["Sesli Giriş<br/>(Whisper local)"]
    end

    subgraph API["API Katmanı"]
        FastAPI["FastAPI Backend<br/>:8000<br/>/api/v1/chat<br/>/api/v1/voice<br/>/api/v1/ingest"]
    end

    subgraph Workflow["LangGraph Workflow"]
        WF["State Machine<br/>6 node<br/>+ early gate"]
    end

    subgraph Storage["Veri Katmanı"]
        Qdrant[("Qdrant<br/>Vektör DB<br/>17506 chunk<br/>parent-child")]
    end

    subgraph External["Harici Servisler"]
        Cerebras["Cerebras API<br/>gpt-oss-120b"]
        Groq["Groq API<br/>llama-3.3-70b"]
        OpenAI["OpenAI API<br/>gpt-4o-mini<br/>(sadece eval)"]
    end

    subgraph Local["Yerel GPU Modelleri"]
        BGEM3["BGE-M3<br/>1024d embedding<br/>multilingual"]
        BGERER["BGE-reranker-v2-m3<br/>568M cross-encoder<br/>FP32"]
        Whisper["Whisper-small<br/>TR ses tanıma"]
    end

    UI -->|HTTP| FastAPI
    Voice -->|audio| FastAPI
    FastAPI -->|invoke| WF
    WF -->|search top-30| Qdrant
    WF -->|generation| Cerebras
    WF -->|compress| Groq
    WF -->|embed| BGEM3
    WF -->|rerank| BGERER
    Voice -.->|transcribe| Whisper
    OpenAI -.->|judge<br/>sadece eval| WF
```

---

## 2. LangGraph Workflow — Node Akışı

```mermaid
flowchart TD
    Start([Kullanıcı Sorgusu]) --> SC[scope_check<br/>gpt-oss-120b low<br/>max_tokens=50]

    SC -->|out_of_scope| OOS[/Template Fallback:<br/>"Yalnızca büyükbaş..."/]
    OOS --> Conf
    SC -->|in_scope| CP[compress<br/>llama-3.3-70b<br/>max_tokens=500<br/>sadece >6000 token]

    CP --> RT[retriever<br/>Phase 2 detay aşağıda]

    RT -->|top_sim < 0.60| EG{Early Gate<br/>insufficient evidence}
    EG --> Conf
    RT -->|top_sim >= 0.60| GN[generator<br/>gpt-oss-120b medium<br/>max_tokens=3000<br/>system_prompt + sources]

    GN --> CR[critic<br/>Hibrit:<br/>Regex hard rules<br/>+ LLM judge<br/>gpt-oss-120b low<br/>max_tokens=200]

    CR -->|accepted| Conf[confidence<br/>top_sim & rerank_score<br/>karar: high/medium/low]
    CR -->|rejected, retry < 2| GN
    CR -->|rejected, max retry| Conf

    Conf --> Final([Final Response])

    style SC fill:#ffe6cc
    style CP fill:#ffe6cc
    style RT fill:#cce5ff
    style GN fill:#ffe6cc
    style CR fill:#ffe6cc
    style Conf fill:#d5e8d4
    style EG fill:#fff2cc
```

**Renk kodu:**
- 🟧 Turuncu = LLM çağrısı (Cerebras/Groq)
- 🟦 Mavi = Retrieval/Rerank (Lokal GPU)
- 🟨 Sarı = Karar noktası (kod, LLM yok)
- 🟩 Yeşil = Skorlama/sonlandırma

---

## 3. Retriever Node Detayı (Phase 2)

```mermaid
flowchart TD
    Q[Kullanıcı Sorgusu<br/>orijinal Türkçe] --> EQ[enrich_query<br/>gpt-oss-120b low<br/>max_tokens=2000]
    Q --> EM1[BGE-M3 embed<br/>orijinal sorgu]

    EQ -->|TR+EN keywords<br/>virgülle| EM2[BGE-M3 embed<br/>enriched]

    EM1 -->|1024d vektör| DS1[Qdrant search<br/>top-30<br/>score >= 0.25]
    EM2 -->|1024d vektör| DS2[Qdrant search<br/>top-30<br/>score >= 0.25]

    DS1 --> MG[Birleştir<br/>dedup ilk 100 char<br/>score >= 0.30 filtre<br/>top-30]
    DS2 --> MG

    MG -->|30 aday + EN+TR query<br/>BGE-reranker'a| RR[BGE-reranker-v2-m3<br/>Cross-encoder<br/>FP32 logit hesabı]

    RR -->|raw logit ile sırala<br/>sigmoid sadece skor için| TOP[top-3 chunk]

    TOP --> ST{State'e yaz}
    ST --> RD[retrieved_docs<br/>top-3 chunk]
    ST --> CS[retrieval_similarity_score<br/>dense COSINE top<br/>confidence gate icin]
    ST --> RS[rerank_top_score<br/>cross-encoder sigmoid<br/>audit/log icin]

    style EQ fill:#ffe6cc
    style EM1 fill:#cce5ff
    style EM2 fill:#cce5ff
    style DS1 fill:#cce5ff
    style DS2 fill:#cce5ff
    style RR fill:#cce5ff
    style MG fill:#fff2cc
```

**Phase 2 vs Phase 1 farkı:**

| Aşama | Phase 1 | Phase 2 |
|---|---|---|
| enrich_query | KIRIK (reasoning=medium + 800 tokens → content boş) | DÜZGÜN (low + 2000) |
| Dense top-K | 5 | **30** |
| Reranker | yok | **BGE-reranker-v2-m3** ✨ |
| Generator'a giden | 5 chunk | **3 chunk (rerank top-3)** |

---

## 4. Critic Node — Hibrit Kontrol Detayı

```mermaid
flowchart TD
    DR[draft_response] --> HR[Hard Rules<br/>Python regex/keyword<br/>Anında deterministic]

    HR --> H1{Dozaj triplet?<br/>etken+doz+yol<br/>kontrolü}
    HR --> H2{Hayvan türü?<br/>kedi/köpek/at<br/>scope sızdı mı}
    HR --> H3{Producer'da<br/>reçeteli ilaç adı<br/>geçti mi}

    H1 -->|FAIL| Rej[REJECT<br/>+ rejection_reasons]
    H2 -->|FAIL| Rej
    H3 -->|FAIL| Rej

    H1 -->|OK| LJ[LLM Judge<br/>gpt-oss-120b low<br/>max_tokens=200<br/>SADECE STIL]
    H2 -->|OK| LJ
    H3 -->|OK| LJ

    LJ --> J1{disclaimer_present?<br/>producer'da<br/>veteriner yönlendirme}
    LJ --> J2{emergency_appropriate?<br/>producer + acil sinyal<br/>= 🚨 var mı}
    LJ --> J3{lay_language_ok?<br/>producer'da<br/>çıplak Latince yok}

    J1 -->|FAIL| Rej
    J2 -->|FAIL| Rej
    J3 -->|FAIL| Rej

    J1 -->|OK| Acc[ACCEPT]
    J2 -->|OK| Acc
    J3 -->|OK| Acc

    Rej -->|attempts < 2| RE[Generator'a geri dön<br/>rejection_reasons ile]
    Rej -->|attempts >= 2| ACMR[accepted_after_max_retries]

    style HR fill:#fff2cc
    style LJ fill:#ffe6cc
    style Rej fill:#f8cecc
    style Acc fill:#d5e8d4
    style ACMR fill:#dae8fc
```

**Critic'in 3 katmanı:**
1. **Hard rules** (Python kodu, anında): Halüsinasyon önleme (dozaj, scope, ilaç adı)
2. **LLM judge** (Cerebras, ~0.5s): Stil kontrolü (disclaimer, acil işareti, sade dil)
3. **Retry loop** (max 2x): Generator'a rejection_reasons ile geri

---

## 5. State Şeması (LangGraph AgentState)

```mermaid
classDiagram
    class AgentState {
        +list[dict] messages
        +list[dict] retrieved_docs
        +dict tool_outputs
        +dict thread_memory
        +int critic_attempts
        +str compression_summary
        +str response_status
        +Literal user_role
        +Literal input_source
        +Literal evidence_confidence
        +list[dict] audit_log
        +str draft_response
        +list[str] critic_rejection_reasons
        +str final_response
        +str request_id
        +str active_model
        +float retrieval_similarity_score
        +float rerank_top_score
        +bool source_agreement
        +bool dosage_triplet_validated
        +int source_trust_level
    }

    class StatusValues {
        <<enumeration>>
        ok
        fallback
        error
        rejected
        accepted
        accepted_after_max_retries
        out_of_scope
        insufficient_evidence
    }

    class ConfidenceValues {
        <<enumeration>>
        high
        medium
        low
        insufficient
    }

    AgentState --> StatusValues : response_status
    AgentState --> ConfidenceValues : evidence_confidence
```

**Tip işlevleri:**
- `messages`: konuşma geçmişi
- `retrieved_docs`: reranker'dan gelen top-3
- `critic_attempts`: kaç kez critic reddetti (max 2)
- `retrieval_similarity_score`: DENSE cosine (confidence gate için)
- `rerank_top_score`: cross-encoder sigmoid (audit için)
- `audit_log`: her node'un kararı zaman damgalı

---

## 6. Eval Altyapısı

```mermaid
flowchart LR
    YAML[eval_set_v2.yaml<br/>50 case<br/>8 kategori] --> Runner[run_eval.py]

    Runner -->|her case için| WF[Workflow.invoke]
    WF -->|response| Metrics

    subgraph Metrics["Metrik Hesaplama"]
        FC[fact_coverage<br/>string match<br/>LOKAL]
        FJ[fact_coverage_llm<br/>gpt-4o-mini<br/>OPENAI]
        FB[forbidden<br/>must_not_contain<br/>LOKAL]
        RT[retrieval_precision<br/>source/threshold<br/>LOKAL]
    end

    Metrics --> AGG[aggregate<br/>kategori + stil kırılım]

    AGG --> JSON[eval/reports/<br/>tag.json]
    AGG --> MD[eval/reports/<br/>tag.md]

    style FJ fill:#fce4d6
    style FC fill:#d5e8d4
    style FB fill:#d5e8d4
    style RT fill:#d5e8d4
```

**Önemli ayrım:**
- 🟩 Yeşil metrikler: deterministik (lokal kod), varyans yok
- 🟧 Turuncu metrik: LLM judge, **varyansa açık** — Phase 2'de bu varyans yanıltıcı puanlar verdi

---

## 7. 50-case Eval Set Dağılımı

```mermaid
pie title eval_set_v2.yaml — 50 case
    "producer_natural" : 12
    "vet_technical" : 10
    "emergency" : 8
    "edge_cases" : 5
    "management" : 5
    "out_of_scope" : 5
    "stress_test" : 3
    "multi_turn" : 2
```

**Yazım stili dağılımı:**
```mermaid
pie title Writing Style
    "clean (düzgün)" : 20
    "broken (imla bozuk)" : 16
    "mid (orta)" : 14
```

---

## 8. Phase 0 → Phase 2 Evrim Tablosu

```mermaid
gitGraph
    commit id: "Baseline" tag: "v0"
    commit id: "Pre-BGE retrieval" tag: "Phase 0"
    branch phase1
    checkout phase1
    commit id: "BGE-M3 embedder" tag: "Phase 1"
    commit id: "Hybrid critic"
    commit id: "Calibration"
    checkout main
    merge phase1 tag: "v2 baseline 82%"
    branch phase2
    checkout phase2
    commit id: "Fix 1+2 (critic emergency_appropriate / lay_language)"
    commit id: "Reranker entegre"
    commit id: "enrich_query bug fix"
    checkout main
    merge phase2 tag: "Phase 2 76%"
    branch phase3
    checkout phase3
    commit id: "Citation enforcement" type: HIGHLIGHT
```

---

## 9. Model Bağımlılık Matrisi

| Node | Provider | Model | reasoning | Token | Latency | Maliyet |
|---|---|---|---|---|---|---|
| scope_check | Cerebras | gpt-oss-120b | low | max 50 | ~0.5s | $ |
| compress | Groq | llama-3.3-70b | n/a | max 500 | ~1s | $ (sadece >6k token) |
| enrich_query | Cerebras | gpt-oss-120b | low | max 2000 | ~1s | $ |
| **Retriever embed** | **Lokal** | **BGE-M3** | **n/a** | **n/a** | **~0.1s** | **GPU only** |
| **Retriever rerank** | **Lokal** | **BGE-reranker-v2-m3** | **n/a** | **n/a** | **~2-3s** | **GPU only** |
| generator | Cerebras | gpt-oss-120b | **medium** | max 3000 | **~30-50s** ⚠️ | $$$$ |
| critic LLM judge | Cerebras | gpt-oss-120b | low | max 200 | ~0.5s | $ |
| (eval) fact_llm | **OpenAI** | **gpt-4o-mini** | n/a | max 10 | ~0.3s | $ |

**En pahalı:** Generator (medium reasoning = uzun süre + yüksek token). Tipik query ~45s sürer, generator bunun %90'ı.

---

## 10. Veri Akışı — Tek Bir Query Örneği

```mermaid
sequenceDiagram
    actor U as Kullanıcı
    participant API as FastAPI
    participant WF as LangGraph
    participant SC as scope_check
    participant RT as retriever
    participant Q as Qdrant
    participant BGE as BGE-M3
    participant RR as BGE-reranker
    participant GN as generator
    participant CR as critic
    participant Conf as confidence

    U->>API: POST /chat<br/>"süt humması nedir"
    API->>WF: invoke(state)
    WF->>SC: scope check
    SC->>SC: Cerebras: EVET/HAYIR
    SC-->>WF: in_scope

    WF->>RT: retrieve
    RT->>RT: enrich_query (Cerebras)
    RT->>BGE: embed original + enriched
    BGE-->>RT: 1024d vektörler
    RT->>Q: search top-30 (x2)
    Q-->>RT: 30 + 30 chunk
    RT->>RT: merge, dedup, threshold
    RT->>RR: rerank 30 → 3
    RR-->>RT: top-3 + logitler
    RT-->>WF: retrieved_docs

    WF->>WF: top_sim >= 0.60?
    WF->>GN: generate
    GN->>GN: Cerebras: yanıt
    GN-->>WF: draft_response

    WF->>CR: critic check
    CR->>CR: hard rules + LLM judge
    CR-->>WF: accepted

    WF->>Conf: confidence score
    Conf-->>WF: high
    WF-->>API: final_response
    API-->>U: yanıt + confidence
```

---

## 11. Phase 2 Pass Rate — Mevcut Durum (Doğru Eşik 0.66)

```mermaid
xychart-beta
    title "Production Pass Rate — Kategori Bazlı"
    x-axis ["producer", "vet", "edge", "stress", "emergency", "management", "OOS", "multi"]
    y-axis "Pass Rate %" 0 --> 100
    bar [75, 70, 80, 67, 100, 100, 100, 50]
    bar [92, 50, 40, 33, 100, 100, 100, 50]
```

**Mavi = v2 baseline, Turuncu = Phase 2 (renkler MD viewer'a bağlı)**

Producer kategoride **+17%** kazanç (enrich_query + reranker etkili), vet/edge/stress kategorilerinde kayıp.

---

## Notlar

- Bu diyagram dosyası **mermaid** kullanıyor — VS Code "Markdown Preview Mermaid Support" eklentisi ile veya GitHub'da otomatik render olur.
- PNG export için: VS Code'da preview aç → ekran görüntüsü, veya `mmdc` CLI ile (mermaid-cli) komut satırından SVG/PNG'ye çevir.
- Tez için: diyagramlardan birinden başlayabilirsin (#2 Workflow veya #3 Retriever) — bunlar projenin **çekirdek katkısı** olan iki katmanı görselleştiriyor.
