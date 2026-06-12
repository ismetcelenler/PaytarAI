"use client";

/**
 * PaytarAI — Debug Test Panel
 *
 * Bir sorgu icin TUM pipeline'in input/output'larini gosterir:
 *   - scope_check: analyzer ham cikti + HyDE + keywords
 *   - retriever: her kanalin top chunk'lari + reranked top-3 (full text)
 *   - generator: system prompt + context msg + raw response
 *   - sentence_grounding: her cumlenin chunk-id eslemesi (supported/dropped)
 *   - critic: judge prompt + raw JSON + decision
 */

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, Send } from "lucide-react";
import { sendChatDebug } from "@/lib/paytar";
import type {
  ChatResponse,
  TraceEntry,
  UserRole,
  GroundedSentence,
  HallucinationSpan,
  ChunkSnapshot,
} from "@/types/chat";

const EXAMPLE_QUERIES: Array<{ label: string; q: string; role: UserRole }> = [
  { label: "VET — buzağı ishali ayırıcı", role: "veterinarian", q: "Yenidoğan buzağılarda ishal yapan başlıca etkenler nelerdir, ayırt edici özellikleri nedir?" },
  { label: "VET — süt humması patogenezi", role: "veterinarian", q: "süt humması patogenezi nedir kalsiyum homeostazı mekanizması doğum öncesi sonrası nasıl değişiyor" },
  { label: "Üretici — postpartum halsiz", role: "producer", q: "ineğim doğurdu 5 gün oldu sallak gibi yürüyor sütü de az ne yapayım" },
  { label: "Üretici — buzağı aşı takvimi", role: "producer", q: "buzağılarımı kaç günlükken aşılatmalıyım hangi aşılar gerekli" },
  { label: "Acil — timpani", role: "producer", q: "ineğim aniden çok şişti karın bölgesi balon gibi ne yapayım acil mi" },
];

export default function TestPanelPage() {
  const [role, setRole] = useState<UserRole>("veterinarian");
  const [question, setQuestion] = useState("");
  const [resp, setResp] = useState<ChatResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const submit = async () => {
    if (!question.trim() || pending) return;
    setPending(true);
    setError(null);
    setResp(null);
    const t0 = performance.now();
    const tick = window.setInterval(() => setElapsed((performance.now() - t0) / 1000), 200);
    try {
      const data = await sendChatDebug({ message: question.trim(), user_role: role });
      setResp(data);
      setElapsed((performance.now() - t0) / 1000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bilinmeyen hata");
    } finally {
      window.clearInterval(tick);
      setPending(false);
    }
  };

  return (
    <div className="min-h-screen bg-paytar-bg text-paytar-ink font-sans">
      <header className="border-b border-paytar-line bg-paytar-sidebar">
        <div className="max-w-7xl mx-auto px-5 py-3 flex items-center gap-3">
          <Link href="/" aria-label="Geri" className="w-8 h-8 rounded-md flex items-center justify-center text-paytar-muted hover:bg-paytar-surface2">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="font-serif text-xl text-paytar-ink tracking-tight">
              paytar<span className="italic text-paytar-accent-ink">AI</span>
              <span className="ml-2 font-mono text-[11px] text-paytar-muted">/ DEBUG TEST PANEL</span>
            </h1>
            <p className="font-mono text-[10px] text-paytar-muted tracking-wider mt-0.5">
              Tüm pipeline'ın input/output'larını gör · Sentence-chunk eşleşmeleri · Halüsinasyon teşhisi
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-5 py-6 space-y-6">
        {/* Query form */}
        <section className="bg-paytar-surface border border-paytar-line rounded-2xl p-5">
          <div className="flex gap-3 mb-3">
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              disabled={pending}
              className="px-3 py-2 rounded-md border border-paytar-line bg-paytar-bg text-sm"
            >
              <option value="veterinarian">VET (veteriner)</option>
              <option value="producer">Üretici</option>
            </select>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  submit();
                }
              }}
              placeholder="Soruyu yaz... (Ctrl+Enter: gönder)"
              rows={2}
              disabled={pending}
              className="flex-1 px-3 py-2 rounded-md border border-paytar-line bg-paytar-bg text-sm resize-none"
            />
            <button
              onClick={submit}
              disabled={pending || !question.trim()}
              className="px-5 rounded-md bg-paytar-accent text-paytar-surface flex items-center gap-2 disabled:opacity-50 hover:opacity-95 transition-opacity"
            >
              {pending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span className="font-sans text-sm">{pending ? `${elapsed.toFixed(1)}s…` : "Gönder"}</span>
            </button>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_QUERIES.map((ex, i) => (
              <button
                key={i}
                onClick={() => { setRole(ex.role); setQuestion(ex.q); }}
                disabled={pending}
                className="font-mono text-[10px] tracking-wider uppercase px-2.5 py-1 rounded-full border border-paytar-line text-paytar-accent-ink hover:bg-paytar-surface2 transition-colors"
              >
                {ex.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="mt-3 font-mono text-[11px] text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2">
              {error}
            </div>
          )}
        </section>

        {resp && <TraceView resp={resp} totalElapsed={elapsed} />}
      </main>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  TRACE VIEW — root komponent                                  */
/* ─────────────────────────────────────────────────────────── */

function TraceView({ resp, totalElapsed }: { resp: ChatResponse; totalElapsed: number }) {
  const trace = resp.debug_trace ?? [];
  return (
    <>
      <Timeline trace={trace} totalElapsed={totalElapsed} resp={resp} />
      {trace.map((entry, i) => (
        <NodeSection key={i} entry={entry} resp={resp} />
      ))}
      <FinalResponse resp={resp} />
    </>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  TIMELINE — ust ozet                                          */
/* ─────────────────────────────────────────────────────────── */

function Timeline({ trace, totalElapsed, resp }: { trace: TraceEntry[]; totalElapsed: number; resp: ChatResponse }) {
  return (
    <section className="bg-paytar-surface border border-paytar-line rounded-2xl p-5">
      <h2 className="font-serif text-lg text-paytar-ink mb-3">Pipeline Timeline</h2>
      <div className="space-y-1.5">
        {trace.map((entry, i) => {
          const status = nodeSummary(entry);
          return (
            <div key={i} className="flex items-center gap-3 font-mono text-xs">
              <span className="w-5 text-paytar-muted text-right">{i + 1}.</span>
              <span className="w-44 text-paytar-ink">{entry.node}</span>
              <span className="w-20 text-paytar-muted text-right">{(entry.latency_ms ?? 0).toFixed(0)}ms</span>
              <span className="text-paytar-accent-ink truncate">{status}</span>
            </div>
          );
        })}
        <div className="flex items-center gap-3 font-mono text-xs pt-2 border-t border-paytar-line">
          <span className="w-5"></span>
          <span className="w-44 text-paytar-accent-ink uppercase tracking-wider">TOTAL</span>
          <span className="w-20 text-paytar-accent-ink text-right">{totalElapsed.toFixed(1)}s</span>
          <span className="text-paytar-muted">
            confidence=<b>{resp.evidence_confidence}</b> · attempts={resp.critic_attempts} ·
            grounding={resp.grounding_action ?? "-"} ·
            dense_top={(resp.retrieval_similarity_score ?? 0).toFixed(3)} ·
            rerank_top={(resp.rerank_top_score ?? 0).toFixed(4)}
          </span>
        </div>
      </div>
    </section>
  );
}

function nodeSummary(entry: TraceEntry): string {
  const out = entry.output as Record<string, unknown>;
  switch (entry.node) {
    case "scope_check":
      return `${out.decision} · hyde=${(out.hyde_variants as unknown[])?.length ?? 0} · kw=${(out.enriched_keywords as string)?.length ?? 0}ch`;
    case "retriever": {
      const scores = out.scores as { dense_top?: number; rerank_top?: number };
      const reranked = (out.reranked_top_k as unknown[])?.length ?? 0;
      return `dense=${scores?.dense_top?.toFixed(3)} rerank=${scores?.rerank_top?.toFixed(4)} top-${reranked}`;
    }
    case "generator":
      return `${out.char_count ?? 0}ch · ${out.model ?? ""}`;
    case "sentence_grounding": {
      const stats = out.stats as { total?: number; specific?: number; generic?: number; dropped?: number; drop_ratio?: number } | undefined;
      const action = out.action ?? out.reason ?? "?";
      if (out.skipped) return `SKIP · ${out.reason ?? ""}`;
      return `${action} · ${stats?.total ?? "?"} cumle (specific=${stats?.specific ?? 0} generic=${stats?.generic ?? 0}) · dropped=${stats?.dropped ?? 0} (${((stats?.drop_ratio ?? 0) * 100).toFixed(0)}%)`;
    }
    case "critic":
      return `${out.decision} · judge_ok=${out.judge_ok ?? "?"}`;
    default:
      return "";
  }
}

/* ─────────────────────────────────────────────────────────── */
/*  NODE SECTION — her node icin detayli card                   */
/* ─────────────────────────────────────────────────────────── */

function NodeSection({ entry, resp }: { entry: TraceEntry; resp: ChatResponse }) {
  const [open, setOpen] = useState(entry.node === "sentence_grounding" || entry.node === "retriever");
  return (
    <section className="bg-paytar-surface border border-paytar-line rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-paytar-surface2 transition-colors text-left"
      >
        <div>
          <h3 className="font-serif text-base text-paytar-ink">{nodeLabel(entry.node)}</h3>
          <div className="font-mono text-[10px] text-paytar-muted tracking-wider mt-0.5">
            {entry.latency_ms?.toFixed(0)}ms · {nodeSummary(entry)}
          </div>
        </div>
        <span className="font-mono text-paytar-muted">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="border-t border-paytar-line p-5 space-y-4">
          {entry.node === "sentence_grounding"
            ? <GroundingDetail entry={entry} resp={resp} />
            : entry.node === "retriever"
            ? <RetrieverDetail entry={entry} />
            : entry.node === "generator"
            ? <GeneratorDetail entry={entry} />
            : entry.node === "critic"
            ? <CriticDetail entry={entry} />
            : <ScopeCheckDetail entry={entry} />}
        </div>
      )}
    </section>
  );
}

function nodeLabel(n: TraceEntry["node"]) {
  return ({
    scope_check: "1 · Scope Check",
    retriever: "2 · Retriever (hybrid + rerank)",
    generator: "3 · Generator (Cerebras gpt-oss-120b)",
    sentence_grounding: "4 · Sentence Grounding (Turk-LettuceDetect)",
    critic: "5 · Critic (LLM-judge)",
  } as const)[n];
}

/* ─────────────────────────────────────────────────────────── */
/*  SCOPE CHECK detail                                          */
/* ─────────────────────────────────────────────────────────── */

function ScopeCheckDetail({ entry }: { entry: TraceEntry }) {
  const o = entry.output as Record<string, unknown>;
  return (
    <div className="space-y-3 font-sans text-sm">
      <Field label="Soru" value={entry.input.user_message as string} />
      <Field label="Karar" value={String(o.decision)} accent />
      <Field label="Enriched keywords" value={String(o.enriched_keywords ?? "")} mono />
      <div>
        <div className="font-mono text-[10px] tracking-wider text-paytar-muted uppercase mb-1">HyDE varyantlar ({(o.hyde_variants as unknown[])?.length ?? 0})</div>
        <div className="space-y-1.5">
          {(o.hyde_variants as string[] ?? []).map((v, i) => (
            <div key={i} className="text-[13px] bg-paytar-bg p-2.5 rounded-md border border-paytar-line">
              <span className="font-mono text-[10px] text-paytar-accent-ink mr-2">#{i + 1}</span>{v}
            </div>
          ))}
        </div>
      </div>
      <Collapsible title="Raw analyzer output" defaultOpen={false}>
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line">{String(o.raw_analyzer)}</pre>
      </Collapsible>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  RETRIEVER detail — kanallar + reranked top-3                */
/* ─────────────────────────────────────────────────────────── */

function RetrieverDetail({ entry }: { entry: TraceEntry }) {
  const inp = entry.input as Record<string, unknown>;
  const out = entry.output as Record<string, unknown>;
  const channels = out.channels as Record<string, ChunkSnapshot[]>;
  const reranked = out.reranked_top_k as ChunkSnapshot[] ?? [];

  return (
    <div className="space-y-4 font-sans text-sm">
      <Field label="Original sorgu" value={inp.user_query as string} />
      <Field label="Rerank sorgusu (orig + enriched)" value={inp.rerank_query as string} mono />
      <Field label="Step-back sorgusu" value={inp.step_back_query as string} mono />

      <div className="border border-paytar-line rounded-md p-3 bg-paytar-bg/50">
        <div className="flex items-center justify-between mb-2">
          <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-accent-ink">
            Reranked Top-3 (Generator'a giden)
          </div>
          <CopyChunksButton chunks={reranked} />
        </div>
        <div className="space-y-3">
          {reranked.map((c, i) => (
            <div key={i} className="bg-paytar-surface border border-paytar-line rounded-md p-3">
              <div className="flex justify-between items-baseline gap-3 mb-1.5">
                <div className="font-sans text-sm font-medium">
                  <span className="font-mono text-paytar-accent-ink mr-2">[{i + 1}]</span>{c.title}
                </div>
                <div className="font-mono text-[10px] text-paytar-muted whitespace-nowrap">
                  dense=<b className="text-paytar-ink">{c.dense_score?.toFixed(3)}</b> ·
                  logit=<b className="text-paytar-ink">{c.rerank_logit?.toFixed(3)}</b> ·
                  σ=<b className="text-paytar-ink">{c.rerank_sigmoid?.toFixed(4)}</b>
                </div>
              </div>
              <pre className="font-sans text-[12px] text-paytar-ink2 leading-relaxed whitespace-pre-wrap max-h-[200px] overflow-y-auto bg-paytar-bg p-2.5 rounded border border-paytar-line">{c.text_full}</pre>
              <div className="font-mono text-[10px] text-paytar-muted mt-1">{c.text_len} char</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-muted mb-2">
          Kanal kanal — rerank ÖNCESİ (top 10 her kanaldan)
        </div>
        <div className="space-y-2">
          {Object.entries(channels ?? {}).map(([name, chunks]) => (
            <ChannelAccordion key={name} name={name} chunks={chunks} />
          ))}
        </div>
        <div className="font-mono text-[10px] text-paytar-muted mt-2">
          Toplam aday: {(out.candidates_count as number) ?? 0}
        </div>
      </div>
    </div>
  );
}

function CopyChunksButton({ chunks }: { chunks: ChunkSnapshot[] }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!chunks.length) return;
    const payload = chunks
      .map((c, i) => {
        const header = `=== Kaynak ${i + 1} ===\nKitap: ${c.title}\nDense: ${c.dense_score?.toFixed(3) ?? "-"} · Rerank logit: ${c.rerank_logit?.toFixed(3) ?? "-"} · σ: ${c.rerank_sigmoid?.toFixed(4) ?? "-"}`;
        return `${header}\nMetin:\n${c.text_full ?? ""}`;
      })
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: textarea
      const ta = document.createElement("textarea");
      ta.value = payload;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="font-mono text-[10px] tracking-wider uppercase px-2.5 py-1 rounded border border-paytar-line text-paytar-accent-ink hover:bg-paytar-surface2 transition-colors flex items-center gap-1.5"
      title="3 chunk'ı (başlık + skorlar + tam metin) panoya kopyala"
    >
      {copied ? "✓ kopyalandı" : "📋 3 chunk'ı kopyala"}
    </button>
  );
}

function ChannelAccordion({ name, chunks }: { name: string; chunks: ChunkSnapshot[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-paytar-line rounded-md bg-paytar-bg/30">
      <button onClick={() => setOpen(!open)} className="w-full px-3 py-2 flex justify-between items-center text-left hover:bg-paytar-surface2">
        <span className="font-mono text-[11px] uppercase tracking-wider text-paytar-ink">
          {name} <span className="text-paytar-muted">({chunks.length})</span>
        </span>
        <span className="font-mono text-paytar-muted">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="border-t border-paytar-line px-3 py-2 space-y-1.5 max-h-[300px] overflow-y-auto">
          {chunks.map((c, i) => (
            <div key={i} className="text-[11px] py-1 border-b border-paytar-line/50 last:border-b-0">
              <div className="flex justify-between gap-2">
                <span className="font-sans font-medium text-paytar-ink truncate">{c.title}</span>
                <span className="font-mono text-paytar-muted whitespace-nowrap">{c.score?.toFixed(3)}</span>
              </div>
              <div className="font-sans text-paytar-muted line-clamp-2 mt-0.5">{c.text_preview}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  GENERATOR detail                                            */
/* ─────────────────────────────────────────────────────────── */

function GeneratorDetail({ entry }: { entry: TraceEntry }) {
  const inp = entry.input as Record<string, unknown>;
  const out = entry.output as Record<string, unknown>;
  return (
    <div className="space-y-3 font-sans text-sm">
      <div className="flex flex-wrap gap-3 font-mono text-[11px] text-paytar-muted">
        <span>model: <b className="text-paytar-ink">{String(out.model)}</b></span>
        <span>temperature: <b className="text-paytar-ink">{String(out.temperature)}</b></span>
        <span>top_p: <b className="text-paytar-ink">{String(out.top_p)}</b></span>
        <span>reasoning: <b className="text-paytar-ink">{String(out.reasoning_effort)}</b></span>
        <span>attempt: <b className="text-paytar-ink">{String(inp.attempt)}</b></span>
        <span>chars: <b className="text-paytar-ink">{String(out.char_count)}</b></span>
      </div>
      <Collapsible title="System prompt">
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(inp.system_prompt)}</pre>
      </Collapsible>
      <Collapsible title="Context message (sources + soru)" defaultOpen>
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(inp.context_msg)}</pre>
      </Collapsible>
      <Collapsible title="Raw LLM response (taslak — grounding'den önce)" defaultOpen>
        <pre className="text-[12px] whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(out.raw_response)}</pre>
      </Collapsible>
      {Array.isArray(inp.rejection_reasons) && (inp.rejection_reasons as unknown[]).length > 0 && (
        <Field label="Önceki red gerekçeleri" value={(inp.rejection_reasons as string[]).join("; ")} mono />
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  SENTENCE GROUNDING — özel cümle-chunk haritası              */
/* ─────────────────────────────────────────────────────────── */

function GroundingDetail({ entry, resp }: { entry: TraceEntry; resp: ChatResponse }) {
  const inp = entry.input as Record<string, unknown>;
  const out = entry.output as Record<string, unknown>;
  if (out.skipped) {
    return (
      <div className="font-sans text-sm text-paytar-muted">
        Atlandı: <code className="text-paytar-ink">{String(out.reason ?? out.parse_error ?? out.error)}</code>
      </div>
    );
  }
  const sentences = (out.sentences as GroundedSentence[]) ?? [];
  const stats = out.stats as {
    total: number; specific: number; generic: number; supported: number; dropped: number; drop_ratio: number;
    answer_halluc_chars?: number; answer_total_chars?: number; answer_halluc_ratio?: number;
    raw_span_count?: number; inference_ms?: number;
  };
  const action = out.action as string;
  const verifier = out.verifier as string | undefined;
  const rawSpans = (out.raw_spans as Array<{ start: number; end: number; text: string; confidence: number }>) ?? [];

  return (
    <div className="space-y-4 font-sans text-sm">
      {verifier && (
        <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-muted bg-paytar-bg p-2 rounded">
          verifier: <span className="text-paytar-accent-ink">{verifier}</span>
          {stats?.inference_ms != null && <> · inference: <b className="text-paytar-ink">{stats.inference_ms.toFixed(0)}ms</b></>}
          {stats?.raw_span_count != null && <> · raw spans: <b className="text-paytar-ink">{stats.raw_span_count}</b></>}
        </div>
      )}

      <div className="flex flex-wrap gap-3 font-mono text-[11px]">
        <Pill label="action" value={action} tone={action === "passed" ? "ok" : action === "filtered" ? "warn" : "danger"} />
        <Pill label="cümle" value={String(stats?.total ?? "?")} />
        <Pill label="halluc'lı" value={String(stats?.specific ?? 0)} />
        <Pill label="temiz" value={String(stats?.generic ?? 0)} />
        <Pill label="dropped" value={String(stats?.dropped ?? 0)} tone={(stats?.dropped ?? 0) > 0 ? "warn" : "ok"} />
        {stats?.answer_halluc_ratio != null && (
          <Pill
            label="yanıt halluc oranı"
            value={`${(stats.answer_halluc_ratio * 100).toFixed(1)}% (${stats.answer_halluc_chars}/${stats.answer_total_chars}ch)`}
            tone={stats.answer_halluc_ratio > 0.4 ? "danger" : stats.answer_halluc_ratio > 0.2 ? "warn" : "ok"}
          />
        )}
      </div>

      <div className="border border-paytar-line rounded-md bg-paytar-bg/30 overflow-hidden">
        <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-accent-ink px-3 py-2 border-b border-paytar-line bg-paytar-surface2">
          Cümle-bazlı halüsinasyon haritası — kırmızı span'lar LettuceDetect'in chunk'larda bulamadığı yerler
        </div>
        <div className="divide-y divide-paytar-line">
          {sentences.map((s, i) => (
            <SentenceRow key={i} idx={i + 1} s={s} sources={resp.sources} />
          ))}
        </div>
      </div>

      {rawSpans.length > 0 && (
        <Collapsible title={`Tüm raw spans (${rawSpans.length}) — LettuceDetect ham çıktısı`}>
          <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
            {rawSpans.map((sp, i) => (
              <div key={i} className="flex items-start gap-3 text-[12px] bg-paytar-bg p-2 rounded border border-paytar-line">
                <span className="font-mono text-[10px] text-paytar-muted whitespace-nowrap pt-0.5">#{i + 1}</span>
                <span className="font-mono text-[10px] text-paytar-muted whitespace-nowrap pt-0.5">
                  [{sp.start}-{sp.end}]
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-paytar-ink break-words">{sp.text}</div>
                </div>
                <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded-sm whitespace-nowrap ${
                  sp.confidence > 0.8 ? "bg-destructive/20 text-destructive" :
                  sp.confidence > 0.5 ? "bg-amber-100 text-amber-800" :
                  "bg-paytar-surface2 text-paytar-muted"
                }`}>
                  {(sp.confidence * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </Collapsible>
      )}

      <Collapsible title="Context block (LettuceDetect'e giden kaynak metni)">
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(inp.context ?? "")}</pre>
      </Collapsible>
      <Collapsible title="Draft IN (filtre öncesi — generator'ın ham yanıtı)">
        <pre className="text-[12px] whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(inp.draft_in)}</pre>
      </Collapsible>
      <Collapsible title="Draft OUT (filtre sonrası — critic'e giden)" defaultOpen>
        <pre className="text-[12px] whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(out.draft_out)}</pre>
      </Collapsible>
    </div>
  );
}

function SentenceRow({ idx, s, sources }: { idx: number; s: GroundedSentence; sources: { title: string; snippet: string }[] }) {
  const [showChunk, setShowChunk] = useState(false);
  const chunkData = s.chunk && sources[s.chunk - 1];
  const dropped = !s.supported;
  const spans = s.hallucination_spans ?? [];
  const ratio = s.hallucination_ratio ?? 0;

  // Build inline highlighted segments — span'ları kırmızıyla işaretle
  const highlighted = renderHighlighted(s.text, spans);

  return (
    <div className={`px-3 py-2 ${dropped ? "bg-destructive/5" : ""}`}>
      <div className="flex items-start gap-3">
        <span className="font-mono text-[10px] text-paytar-muted w-6 text-right pt-0.5">{idx}</span>
        <div className="flex-1 min-w-0">
          <div className={`text-[13px] leading-relaxed ${dropped ? "opacity-70" : ""}`}>{highlighted}</div>
          {spans.length > 0 && (
            <div className="mt-1.5 space-y-0.5">
              {spans.map((sp, i) => (
                <div key={i} className="text-[11px] font-mono text-destructive flex items-center gap-2">
                  <span className="bg-destructive/15 px-1.5 py-0.5 rounded">{(sp.confidence * 100).toFixed(0)}%</span>
                  <span className="text-paytar-muted">halluc:</span>
                  <span className="text-paytar-ink2 truncate">{sp.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {spans.length === 0 ? (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-paytar-accent-soft text-paytar-accent-ink uppercase tracking-wider">✓ temiz</span>
          ) : dropped ? (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-destructive/20 text-destructive uppercase tracking-wider">
              ✗ drop ({(ratio * 100).toFixed(0)}%)
            </span>
          ) : (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-amber-100 text-amber-800 uppercase tracking-wider">
              ⚠ {(ratio * 100).toFixed(0)}% halluc — eşik altı, korundu
            </span>
          )}
          {s.chunk && (
            <button
              onClick={() => setShowChunk(!showChunk)}
              className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-paytar-surface2 text-paytar-ink2 hover:bg-paytar-accent-soft transition-colors"
            >
              Chunk {s.chunk}
            </button>
          )}
        </div>
      </div>
      {showChunk && chunkData && (
        <div className="mt-2 ml-9 p-2.5 bg-paytar-surface2 border border-paytar-line rounded text-[11px] text-paytar-ink2">
          <div className="font-mono text-[10px] text-paytar-accent-ink mb-1">{chunkData.title}</div>
          <div className="whitespace-pre-wrap leading-relaxed">{chunkData.snippet}</div>
        </div>
      )}
    </div>
  );
}

/**
 * Cümlede halüsinasyon span'larını inline kırmızı highlight olarak göster.
 * Sentence text içinde span.relative_start/end aralıklarını işaretler.
 */
function renderHighlighted(text: string, spans: HallucinationSpan[]): React.ReactNode {
  if (!spans.length) return text;
  const sorted = [...spans].sort((a, b) => a.relative_start - b.relative_start);
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  sorted.forEach((sp, i) => {
    const start = Math.max(cursor, sp.relative_start);
    const end = Math.min(text.length, sp.relative_end);
    if (start > cursor) parts.push(<span key={`p${i}`}>{text.slice(cursor, start)}</span>);
    if (end > start) {
      parts.push(
        <span
          key={`h${i}`}
          className="bg-destructive/25 text-destructive font-medium underline decoration-destructive decoration-wavy underline-offset-2"
          title={`Halluc, confidence ${(sp.confidence * 100).toFixed(0)}%`}
        >
          {text.slice(start, end)}
        </span>
      );
    }
    cursor = Math.max(cursor, end);
  });
  if (cursor < text.length) parts.push(<span key="tail">{text.slice(cursor)}</span>);
  return parts;
}

/* ─────────────────────────────────────────────────────────── */
/*  CRITIC detail                                                */
/* ─────────────────────────────────────────────────────────── */

function CriticDetail({ entry }: { entry: TraceEntry }) {
  const inp = entry.input as Record<string, unknown>;
  const out = entry.output as Record<string, unknown>;
  const parsed = out.judge_parsed_json as Record<string, boolean> | undefined;

  return (
    <div className="space-y-3 font-sans text-sm">
      <div className="flex flex-wrap gap-2 font-mono text-[11px]">
        <Pill label="decision" value={String(out.decision)} tone={String(out.decision).includes("accepted") ? "ok" : "danger"} />
        <Pill label="judge_ok" value={String(out.judge_ok)} tone={out.judge_ok ? "ok" : "warn"} />
        <Pill label="attempt_in" value={String(inp.attempts_in)} />
        <Pill label="source_has_emergency" value={String(out.source_has_emergency)} />
      </div>

      {parsed && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {Object.entries(parsed).map(([k, v]) => (
            <Pill key={k} label={k} value={String(v)} tone={v ? "ok" : "danger"} />
          ))}
        </div>
      )}

      {Boolean(out.judge_problems) && (
        <Field label="Judge problems" value={String(out.judge_problems)} mono />
      )}
      {Boolean(out.judge_error) && (
        <Field label="Judge error" value={String(out.judge_error)} mono />
      )}

      <Collapsible title="Judge prompt (Cerebras gpt-oss-120b)">
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(out.judge_prompt)}</pre>
      </Collapsible>
      <Collapsible title="Judge raw response">
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[300px] overflow-y-auto">{String(out.judge_raw_response)}</pre>
      </Collapsible>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  FINAL RESPONSE                                              */
/* ─────────────────────────────────────────────────────────── */

function FinalResponse({ resp }: { resp: ChatResponse }) {
  return (
    <section className="bg-paytar-surface border border-paytar-accent rounded-2xl p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-serif text-lg text-paytar-ink">Final response</h2>
        <span className="font-mono text-[10px] text-paytar-muted tracking-wider">
          {resp.response.length} char · confidence={resp.evidence_confidence}
        </span>
      </div>
      <pre className="font-sans text-sm text-paytar-ink whitespace-pre-wrap leading-relaxed">{resp.response}</pre>
    </section>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  utility components                                          */
/* ─────────────────────────────────────────────────────────── */

function Field({ label, value, mono, accent }: { label: string; value: string; mono?: boolean; accent?: boolean }) {
  return (
    <div>
      <div className="font-mono text-[10px] tracking-wider text-paytar-muted uppercase mb-0.5">{label}</div>
      <div className={`${mono ? "font-mono text-[12px]" : "font-sans text-sm"} ${accent ? "text-paytar-accent-ink font-medium" : "text-paytar-ink"} bg-paytar-bg p-2 rounded-md border border-paytar-line break-words`}>
        {value || <span className="text-paytar-muted">(yok)</span>}
      </div>
    </div>
  );
}

function Pill({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" | "danger" }) {
  const bg = tone === "ok" ? "bg-paytar-accent-soft text-paytar-accent-ink"
    : tone === "warn" ? "bg-amber-100 text-amber-800"
    : tone === "danger" ? "bg-destructive/15 text-destructive"
    : "bg-paytar-surface2 text-paytar-ink2";
  return (
    <span className={`inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider px-2 py-1 rounded ${bg}`}>
      <span className="opacity-70">{label}:</span>
      <b>{value}</b>
    </span>
  );
}

function Collapsible({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between text-left mb-1.5">
        <span className="font-mono text-[10px] tracking-wider uppercase text-paytar-accent-ink">{title}</span>
        <span className="font-mono text-paytar-muted text-xs">{open ? "▾" : "▸"}</span>
      </button>
      {open && <div>{children}</div>}
    </div>
  );
}
