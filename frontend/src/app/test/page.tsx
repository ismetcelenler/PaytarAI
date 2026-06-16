"use client";

/**
 * PaytarAI — Debug Test Panel
 *
 * Bir sorgu icin TUM pipeline'in input/output'larini gosterir:
 *   - scope_check: analyzer ham cikti + HyDE + keywords
 *   - retriever: her kanalin top chunk'lari + reranked top-3 (full text)
 *   - generator: system prompt + context msg + raw response
 *   - claim_attribution: her cumlenin chunk-id eslemesi (claim/filler + drop)
 *   - confidence: skor + threshold
 *
 * v5 (Faz C): sentence_grounding (LettuceDetect) yerine claim_attribution.
 * Final response icinde [Kaynak N] etiketleri tiklanabilir, modal'da tam chunk acilir.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, HelpCircle, Loader2, RotateCcw, Send, User, X } from "lucide-react";
import { sendChatStream } from "@/lib/paytar";
import { findEvidenceRange } from "@/lib/highlight";
import { PipelineProgress, type PipelineStepEvent } from "@/components/paytar/pipeline-progress";
import type {
  ChatResponse,
  TraceEntry,
  UserRole,
  ChunkSnapshot,
  ChunkFull,
  SentenceCitation,
  ResponseLength,
  BackendMessage,
} from "@/types/chat";

/** Bir tur = (kullanici sorusu, backend yaniti, pipeline metrikleri). Test panelinde
 *  multi-turn destegi icin tutuyoruz; her tur kendi TraceView'i ile gosterilir. */
interface TestTurn {
  id: string;
  userMessage: string;
  resp: ChatResponse;
  elapsedSec: number;
  steps: PipelineStepEvent[];
}

const EXAMPLE_QUERIES: Array<{ label: string; q: string; role: UserRole }> = [
  { label: "VET — buzağı ishali ayırıcı", role: "veterinarian", q: "Yenidoğan buzağılarda ishal yapan başlıca etkenler nelerdir, ayırt edici özellikleri nedir?" },
  { label: "VET — süt humması patogenezi", role: "veterinarian", q: "süt humması patogenezi nedir kalsiyum homeostazı mekanizması doğum öncesi sonrası nasıl değişiyor" },
  { label: "Üretici — postpartum halsiz", role: "producer", q: "ineğim doğurdu 5 gün oldu sallak gibi yürüyor sütü de az ne yapayım" },
  { label: "Üretici — buzağı aşı takvimi", role: "producer", q: "buzağılarımı kaç günlükken aşılatmalıyım hangi aşılar gerekli" },
  { label: "Acil — timpani", role: "producer", q: "ineğim aniden çok şişti karın bölgesi balon gibi ne yapayım acil mi" },
];

const LENGTH_OPTIONS: Array<{ value: ResponseLength; label: string }> = [
  { value: "short", label: "Kısa" },
  { value: "medium", label: "Orta" },
  { value: "long", label: "Uzun" },
];

export default function TestPanelPage() {
  const [role, setRole] = useState<UserRole>("veterinarian");
  const [length, setLength] = useState<ResponseLength>("medium");
  const [question, setQuestion] = useState("");
  // Multi-turn: her gönderim turlar listesine eklenir, history backend'e iletilir.
  const [turns, setTurns] = useState<TestTurn[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [openChunkId, setOpenChunkId] = useState<number | null>(null);
  const [openSentenceText, setOpenSentenceText] = useState<string | null>(null);
  const [openEvidence, setOpenEvidence] = useState<string | null>(null);
  const [streamSteps, setStreamSteps] = useState<PipelineStepEvent[]>([]);
  const [streamStartedAt, setStreamStartedAt] = useState<number | null>(null);

  const [liveMs, setLiveMs] = useState(0);
  useEffect(() => {
    if (!streamStartedAt) {
      setLiveMs(0);
      return;
    }
    const t = setInterval(() => setLiveMs(Date.now() - streamStartedAt), 100);
    return () => clearInterval(t);
  }, [streamStartedAt]);

  const lastTurn = turns.length > 0 ? turns[turns.length - 1] : null;
  const inClarificationFlow =
    lastTurn?.resp.response_status === "clarification_needed";

  // History'yi backend formatina cevir — clarification turlarini "kind=clarification"
  // olarak isaretle (backend clarification_attempts'i geri hesapliyor).
  const buildHistory = (newUserMsg: string): BackendMessage[] => {
    const msgs: BackendMessage[] = [];
    for (const t of turns) {
      msgs.push({ role: "user", content: t.userMessage });
      const kind: BackendMessage["kind"] =
        t.resp.response_status === "clarification_needed"
          ? "clarification"
          : t.resp.response_status === "clarification_exhausted" ||
            t.resp.response_status === "insufficient_evidence" ||
            t.resp.response_status === "out_of_scope" ||
            t.resp.response_status === "fallback"
          ? "fallback"
          : "answer";
      msgs.push({ role: "assistant", content: t.resp.response, kind });
    }
    msgs.push({ role: "user", content: newUserMsg });
    return msgs;
  };

  const submit = async () => {
    const trimmed = question.trim();
    if (!trimmed || pending) return;

    setPending(true);
    setError(null);
    setStreamSteps([]);
    setStreamStartedAt(Date.now());
    const t0 = performance.now();
    const tick = window.setInterval(() => setElapsed((performance.now() - t0) / 1000), 200);

    const history = buildHistory(trimmed);

    try {
      let result: ChatResponse | null = null;
      const collectedSteps: PipelineStepEvent[] = [];
      await sendChatStream(
        {
          message: trimmed,
          user_role: role,
          response_length: length,
          messages: history,
        },
        (ev) => {
          if (ev.type === "step") {
            const step = {
              node: ev.data.node,
              ms_since_start: ev.data.ms_since_start,
              step_index: ev.data.step_index,
            };
            collectedSteps.push(step);
            setStreamSteps((prev) => [...prev, step]);
          } else if (ev.type === "result") {
            result = ev.data;
          } else if (ev.type === "error") {
            throw new Error(ev.data.detail);
          }
        },
        { debug: true },
      );
      if (!result) throw new Error("Stream bitti ama result event'i gelmedi.");

      const finalSec = (performance.now() - t0) / 1000;
      setElapsed(finalSec);

      // Yeni turu listeye ekle
      setTurns((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          userMessage: trimmed,
          resp: result as ChatResponse,
          elapsedSec: finalSec,
          steps: collectedSteps,
        },
      ]);
      setQuestion("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bilinmeyen hata");
    } finally {
      window.clearInterval(tick);
      setPending(false);
      setStreamStartedAt(null);
    }
  };

  const resetSession = () => {
    setTurns([]);
    setQuestion("");
    setError(null);
    setStreamSteps([]);
  };

  const openChunk = (id: number, sentenceText?: string, evidence?: string) => {
    setOpenChunkId(id);
    setOpenSentenceText(sentenceText ?? null);
    setOpenEvidence(evidence ?? null);
  };

  const closeChunk = () => {
    setOpenChunkId(null);
    setOpenSentenceText(null);
    setOpenEvidence(null);
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
              v6 · multi-turn · clarification gate · tıklanabilir atıflar
            </p>
          </div>
          {turns.length > 0 && (
            <button
              onClick={resetSession}
              disabled={pending}
              className="ml-auto flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase text-paytar-muted hover:text-paytar-ink px-2 py-1 rounded hover:bg-paytar-surface2 transition-colors disabled:opacity-40"
              title="Tüm turları sıfırla, yeni oturum başlat"
            >
              <RotateCcw className="w-3 h-3" />
              Yeni oturum
            </button>
          )}
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
            <div className="inline-flex border border-paytar-line rounded-md overflow-hidden self-stretch">
              {LENGTH_OPTIONS.map((opt) => {
                const active = length === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setLength(opt.value)}
                    disabled={pending}
                    className={`px-3 font-mono text-[10px] tracking-wider uppercase transition-colors ${
                      active
                        ? "bg-paytar-accent text-paytar-surface"
                        : "bg-paytar-bg text-paytar-muted hover:text-paytar-ink hover:bg-paytar-surface2"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  submit();
                }
              }}
              placeholder={
                inClarificationFlow
                  ? "Takip sorularını cevapla (örn: 5 yaşında, dün başladı, kanlı dışkı var)..."
                  : "Soruyu yaz... (Ctrl+Enter: gönder)"
              }
              rows={2}
              disabled={pending}
              className={`flex-1 px-3 py-2 rounded-md border bg-paytar-bg text-sm resize-none ${
                inClarificationFlow ? "border-amber-400/60" : "border-paytar-line"
              }`}
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

        {/* Multi-turn — her turu sırasıyla bas */}
        {turns.map((turn, i) => (
          <TurnPanel
            key={turn.id}
            turn={turn}
            turnIndex={i + 1}
            totalTurns={turns.length}
            openChunk={openChunk}
          />
        ))}

        {pending && (
          <section className="bg-paytar-surface border border-paytar-line rounded-2xl p-5">
            <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-muted mb-3">
              Tur {turns.length + 1} işleniyor
            </div>
            <PipelineProgress
              steps={streamSteps}
              isStreaming={pending}
              elapsedMs={liveMs}
            />
          </section>
        )}
      </main>

      {lastTurn && openChunkId !== null && (
        <ChunkModal
          chunk={lastTurn.resp.chunks?.[openChunkId - 1]}
          chunkId={openChunkId}
          highlightSentence={openSentenceText}
          evidence={openEvidence}
          onClose={closeChunk}
        />
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  TURN PANEL — bir kullanici sorusu + cevap + pipeline trace  */
/* ─────────────────────────────────────────────────────────── */

function TurnPanel({
  turn, turnIndex, totalTurns, openChunk,
}: {
  turn: TestTurn;
  turnIndex: number;
  totalTurns: number;
  openChunk: OpenChunkFn;
}) {
  const status = turn.resp.response_status ?? "ok";
  const isClarification = status === "clarification_needed";
  const isExhausted = status === "clarification_exhausted";
  const rerankTop = turn.resp.rerank_top_score ?? 0;
  const denseTop = turn.resp.retrieval_similarity_score ?? 0;

  const statusBadge = isClarification ? (
    <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-amber-100 text-amber-800">
      <HelpCircle className="w-3 h-3" />
      Takip sorusu
    </span>
  ) : isExhausted ? (
    <span className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-destructive/15 text-destructive">
      Tur limiti aşıldı
    </span>
  ) : status === "out_of_scope" ? (
    <span className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-paytar-surface2 text-paytar-muted">
      Kapsam dışı
    </span>
  ) : (
    <span className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-paytar-accent-soft text-paytar-accent-ink">
      Cevap
    </span>
  );

  return (
    <div className="space-y-3">
      {/* Tur basligi + kullanici sorusu */}
      <section className="bg-paytar-surface2 border border-paytar-line rounded-2xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-mono text-[10px] tracking-wider uppercase text-paytar-muted">
            Tur {turnIndex} / {totalTurns}
          </span>
          {statusBadge}
          <span className="font-mono text-[10px] text-paytar-muted ml-auto tabular-nums">
            {turn.elapsedSec.toFixed(1)}s · dense={denseTop.toFixed(3)} · rerank={rerankTop.toFixed(3)}
          </span>
        </div>
        <div className="flex items-start gap-3">
          <div className="w-6 h-6 rounded-full bg-paytar-accent flex items-center justify-center text-paytar-surface flex-shrink-0">
            <User className="w-3 h-3" />
          </div>
          <div className="flex-1 font-sans text-[14px] text-paytar-ink leading-relaxed">
            {turn.userMessage}
          </div>
        </div>
      </section>

      {/* Bu turun pipeline trace'i */}
      <TraceView
        resp={turn.resp}
        totalElapsed={turn.elapsedSec}
        openChunk={openChunk}
      />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  TRACE VIEW — root komponent                                  */
/* ─────────────────────────────────────────────────────────── */

type OpenChunkFn = (id: number, sentenceText?: string, evidence?: string) => void;

function TraceView({
  resp, totalElapsed, openChunk,
}: { resp: ChatResponse; totalElapsed: number; openChunk: OpenChunkFn }) {
  const trace = resp.debug_trace ?? [];
  return (
    <>
      <Timeline trace={trace} totalElapsed={totalElapsed} resp={resp} />
      {trace.map((entry, i) => (
        <NodeSection key={i} entry={entry} resp={resp} openChunk={openChunk} />
      ))}
      <FinalResponse resp={resp} openChunk={openChunk} />
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
    case "claim_attribution": {
      if (out.skipped) return `SKIP · ${out.reason ?? ""}`;
      const stats = out.stats as {
        total?: number; claims?: number; filler?: number; kept?: number;
        dropped?: number; drop_ratio?: number;
        verify_reassigned?: number; verify_dropped_evidence_missing?: number;
        verifier_supported?: number; verifier_not_supported?: number;
        verifier_errors?: number; verifier_latency_ms?: number;
      } | undefined;
      const action = out.action ?? "?";
      const verifier =
        (stats?.verifier_supported ?? 0) + (stats?.verifier_not_supported ?? 0) + (stats?.verifier_errors ?? 0) > 0
          ? ` · verifier (Claude Opus 4.8, ${(stats?.verifier_latency_ms ?? 0).toFixed(0)}ms): supp=${stats?.verifier_supported ?? 0}, ¬supp=${stats?.verifier_not_supported ?? 0}, err=${stats?.verifier_errors ?? 0}`
          : "";
      return `${action} · ${stats?.total ?? "?"} cumle (claim=${stats?.claims ?? 0} filler=${stats?.filler ?? 0}) · dropped=${stats?.dropped ?? 0} (${((stats?.drop_ratio ?? 0) * 100).toFixed(0)}%)${verifier}`;
    }
    case "clarification": {
      const action = out.action ?? "?";
      const input = entry.input as Record<string, unknown>;
      const attempt = input.attempt ?? "?";
      const payload = out.payload as { differentials?: unknown[]; follow_up_questions?: unknown[] } | undefined;
      return `${action} · attempt=${attempt} · differentials=${payload?.differentials?.length ?? 0} questions=${payload?.follow_up_questions?.length ?? 0}`;
    }
    case "sentence_grounding": {
      const stats = out.stats as { total?: number; dropped?: number } | undefined;
      const action = out.action ?? out.reason ?? "?";
      if (out.skipped) return `SKIP · ${out.reason ?? ""}`;
      return `${action} · ${stats?.total ?? "?"} cumle · dropped=${stats?.dropped ?? 0}`;
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

function NodeSection({
  entry, resp, openChunk,
}: { entry: TraceEntry; resp: ChatResponse; openChunk: OpenChunkFn }) {
  const [open, setOpen] = useState(
    entry.node === "claim_attribution" || entry.node === "retriever"
  );
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
          {entry.node === "claim_attribution"
            ? <ClaimAttributionDetail entry={entry} resp={resp} openChunk={openChunk} />
            : entry.node === "retriever"
            ? <RetrieverDetail entry={entry} />
            : entry.node === "generator"
            ? <GeneratorDetail entry={entry} />
            : <ScopeCheckDetail entry={entry} />}
        </div>
      )}
    </section>
  );
}

function nodeLabel(n: TraceEntry["node"]) {
  return ({
    scope_check: "1 · Scope Check",
    compress: "1b · Compress",
    retriever: "2 · Retriever (hybrid + rerank)",
    generator: "3 · Generator (Cerebras gpt-oss-120b)",
    claim_attribution: "4 · Claim Attribution (judge: Llama-3.3-70B + hardcode verify · verifier LLM: disabled)",
    clarification: "3b · Clarification (Llama-3.3-70B takip sorusu)",
    confidence: "5 · Confidence",
    sentence_grounding: "4 · Sentence Grounding (legacy)",
    critic: "5 · Critic (legacy)",
  } as const)[n] ?? n;
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
/*  RETRIEVER detail — kanallar + reranked top-K                */
/* ─────────────────────────────────────────────────────────── */

function RetrieverDetail({ entry }: { entry: TraceEntry }) {
  const inp = entry.input as Record<string, unknown>;
  const out = entry.output as Record<string, unknown>;
  const channels = out.channels as Record<string, ChunkSnapshot[]>;
  const reranked = out.reranked_top_k as ChunkSnapshot[] ?? [];
  const langPools = out.language_pools as {
    tr_pool_size?: number;
    en_pool_size?: number;
    tr_reranked?: ChunkSnapshot[];
    en_reranked?: ChunkSnapshot[];
  } | undefined;

  return (
    <div className="space-y-4 font-sans text-sm">
      <Field label="Original sorgu (TR)" value={inp.user_query as string} />
      <Field label="🌍 EN translated query (EN pool rerank için)" value={(inp.en_translated_query as string) || "(yok — analyzer üretmedi, fallback: orijinal TR sorgu)"} mono accent />
      <Field label="Enriched keywords (BM25/dense kanalları için — rerank query'sinden çıkarıldı)" value={(inp.enriched_keywords as string) || "(yok)"} mono />

      {langPools && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <PoolCard
            title="🇹🇷 TR Pool"
            poolSize={langPools.tr_pool_size ?? 0}
            rerankQuery={(inp.tr_rerank_query as string) || ""}
            reranked={langPools.tr_reranked ?? []}
            accentTone="tr"
          />
          <PoolCard
            title="🇬🇧 EN Pool"
            poolSize={langPools.en_pool_size ?? 0}
            rerankQuery={(inp.en_rerank_query as string) || ""}
            reranked={langPools.en_reranked ?? []}
            accentTone="en"
          />
        </div>
      )}

      <div className="border border-paytar-accent rounded-md p-3 bg-paytar-bg/50">
        <div className="flex items-center justify-between mb-2">
          <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-accent-ink">
            Generator'a giden — TR top-K + EN top-K (concat, re-sort yok)
          </div>
          <CopyChunksButton chunks={reranked} />
        </div>
        <div className="space-y-3">
          {reranked.map((c, i) => (
            <div key={i} className="bg-paytar-surface border border-paytar-line rounded-md p-3">
              <div className="flex justify-between items-baseline gap-3 mb-1.5">
                <div className="font-sans text-sm font-medium">
                  <span className="font-mono text-paytar-accent-ink mr-2">[{i + 1}]</span>
                  {c.language && (
                    <span className={`font-mono text-[9px] mr-1.5 px-1 py-0.5 rounded ${
                      c.language === "en" ? "bg-blue-100 text-blue-800" : "bg-amber-100 text-amber-800"
                    }`}>{c.language.toUpperCase()}</span>
                  )}
                  {c.title}
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

function PoolCard({ title, poolSize, rerankQuery, reranked, accentTone }: {
  title: string;
  poolSize: number;
  rerankQuery: string;
  reranked: ChunkSnapshot[];
  accentTone: "tr" | "en";
}) {
  const bg = accentTone === "tr" ? "bg-amber-50/30 border-amber-300/50" : "bg-blue-50/30 border-blue-300/50";
  return (
    <div className={`border rounded-md p-3 ${bg}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono text-[11px] tracking-wider uppercase text-paytar-ink font-medium">
          {title}
        </div>
        <span className="font-mono text-[10px] text-paytar-muted">
          {poolSize} aday → top-{reranked.length}
        </span>
      </div>
      <div className="text-[10px] font-mono text-paytar-muted mb-2 bg-paytar-bg/60 px-2 py-1 rounded border border-paytar-line/50 break-words">
        rerank q: {rerankQuery || "(boş)"}
      </div>
      <div className="space-y-2">
        {reranked.length === 0 ? (
          <div className="text-[11px] font-mono text-paytar-muted italic px-2">
            Bu dilde aday yok
          </div>
        ) : (
          reranked.map((c, i) => (
            <div key={i} className="bg-paytar-surface border border-paytar-line rounded p-2 text-[11px]">
              <div className="flex justify-between items-baseline gap-2 mb-1">
                <div className="font-sans font-medium truncate">
                  <span className="font-mono text-paytar-accent-ink mr-1">[{i + 1}]</span>
                  {c.title}
                </div>
                <div className="font-mono text-[9px] text-paytar-muted whitespace-nowrap">
                  σ=<b className="text-paytar-ink">{c.rerank_sigmoid?.toFixed(3)}</b>
                </div>
              </div>
              <div className="font-mono text-[9px] text-paytar-muted">
                dense={c.dense_score?.toFixed(3)} · logit={c.rerank_logit?.toFixed(2)} · {c.text_len}ch
              </div>
            </div>
          ))
        )}
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
      title="Chunkları (başlık + skorlar + tam metin) panoya kopyala"
    >
      {copied ? "✓ kopyalandı" : "📋 chunkları kopyala"}
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
      <Collapsible title="Raw LLM response (taslak — claim_attribution'dan önce)" defaultOpen>
        <pre className="text-[12px] whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(out.raw_response)}</pre>
      </Collapsible>
      {Array.isArray(inp.rejection_reasons) && (inp.rejection_reasons as unknown[]).length > 0 && (
        <Field label="Önceki red gerekçeleri" value={(inp.rejection_reasons as string[]).join("; ")} mono />
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  CLAIM ATTRIBUTION — per-cumle karar tablosu + chunk linki   */
/* ─────────────────────────────────────────────────────────── */

function ClaimAttributionDetail({
  entry, openChunk,
}: { entry: TraceEntry; resp: ChatResponse; openChunk: OpenChunkFn }) {
  const inp = entry.input as Record<string, unknown>;
  const out = entry.output as Record<string, unknown>;

  if (out.skipped) {
    return (
      <div className="font-sans text-sm text-paytar-muted">
        Atlandı: <code className="text-paytar-ink">{String(out.reason ?? out.error)}</code>
        {Boolean(out.raw_response) && (
          <Collapsible title="LLM raw response (yine de varsa)" defaultOpen={false}>
            <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[300px] overflow-y-auto">{String(out.raw_response)}</pre>
          </Collapsible>
        )}
      </div>
    );
  }

  const sentences = (out.sentences as SentenceCitation[]) ?? [];
  const stats = out.stats as {
    total: number; claims: number; filler: number; kept: number; dropped: number;
    drop_ratio: number; n_sources: number;
  };
  const action = out.action as string;
  const judge = out.judge as string | undefined;

  return (
    <div className="space-y-4 font-sans text-sm">
      {judge && (
        <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-muted bg-paytar-bg p-2 rounded">
          judge: <span className="text-paytar-accent-ink">{judge}</span>
        </div>
      )}

      <div className="flex flex-wrap gap-3 font-mono text-[11px]">
        <Pill label="action" value={action} tone={action === "passed" ? "ok" : action === "filtered" ? "warn" : "danger"} />
        <Pill label="cümle" value={String(stats?.total ?? "?")} />
        <Pill label="claim" value={String(stats?.claims ?? 0)} />
        <Pill label="filler" value={String(stats?.filler ?? 0)} />
        <Pill label="kept" value={String(stats?.kept ?? 0)} tone="ok" />
        <Pill label="dropped" value={String(stats?.dropped ?? 0)} tone={(stats?.dropped ?? 0) > 0 ? "warn" : "ok"} />
        <Pill label="drop_ratio" value={`${((stats?.drop_ratio ?? 0) * 100).toFixed(0)}%`} tone={(stats?.drop_ratio ?? 0) > 0.4 ? "danger" : "ok"} />
      </div>

      <div className="border border-paytar-line rounded-md bg-paytar-bg/30 overflow-hidden">
        <div className="font-mono text-[10px] tracking-wider uppercase text-paytar-accent-ink px-3 py-2 border-b border-paytar-line bg-paytar-surface2">
          Cümle-bazlı atıf haritası — "Kaynak N" butonu chunk'in tam metnini açar
        </div>
        <div className="divide-y divide-paytar-line">
          {sentences.map((s) => (
            <CitationRow key={s.idx} s={s} openChunk={openChunk} />
          ))}
        </div>
      </div>

      <Collapsible title="LLM judge prompt">
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(inp.prompt ?? "")}</pre>
      </Collapsible>
      <Collapsible title="LLM judge raw response (JSON, asama 1)">
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[300px] overflow-y-auto">{String(out.raw_response ?? "")}</pre>
      </Collapsible>
      <Collapsible title="LLM verifier raw response (JSON, asama 2 — Claude Opus 4.8)">
        <pre className="text-[11px] font-mono whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[300px] overflow-y-auto">{String(out.verifier_raw_response ?? "(yok)")}</pre>
        {Boolean(out.verifier_error) && (
          <div className="mt-2 text-[11px] font-mono text-destructive bg-destructive/10 border border-destructive/30 rounded px-2 py-1">
            Verifier hata: {String(out.verifier_error)}
          </div>
        )}
      </Collapsible>
      <Collapsible title="Draft IN (filtre öncesi — generator'ın ham yanıtı)">
        <pre className="text-[12px] whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(inp.draft_in)}</pre>
      </Collapsible>
      <Collapsible title="Draft OUT (filtre sonrası — inline [Kaynak N] etiketli)" defaultOpen>
        <pre className="text-[12px] whitespace-pre-wrap bg-paytar-bg p-3 rounded-md border border-paytar-line max-h-[400px] overflow-y-auto">{String(out.draft_out)}</pre>
      </Collapsible>
    </div>
  );
}

function CitationRow({
  s, openChunk,
}: { s: SentenceCitation; openChunk: OpenChunkFn }) {
  const dropped = !s.supported;
  const isClaim = s.type === "claim";
  return (
    <div className={`px-3 py-2 ${dropped ? "bg-destructive/5" : ""}`}>
      <div className="flex items-start gap-3">
        <span className="font-mono text-[10px] text-paytar-muted w-6 text-right pt-0.5">{s.idx}</span>
        <div className="flex-1 min-w-0">
          <div className={`text-[13px] leading-relaxed ${dropped ? "opacity-70 line-through" : ""}`}>{s.text}</div>
          {s.missing_from_llm && (
            <div className="mt-1 text-[10px] font-mono text-amber-700">
              ⚠ LLM judge bu cümleyi atladı — güvenli tarafta &quot;claim+null&quot; sayıldı
            </div>
          )}
          {s.verify_reason === "reassigned" && (
            <div className="mt-1 text-[10px] font-mono text-blue-700">
              🔄 Hardcode: Judge &quot;Kaynak {s.chunk_id_judge}&quot; dedi, evidence Kaynak {s.chunk_id_hardcode}&apos;de bulundu
            </div>
          )}
          {s.verify_reason === "not_found" && (
            <div className="mt-1 text-[10px] font-mono text-amber-700">
              ⚠ Hardcode: Judge &quot;Kaynak {s.chunk_id_judge}&quot; dedi ama evidence hiçbir chunkta substring olarak yok
            </div>
          )}
          {s.verifier_status === "supported" && s.chunk_id_judge !== s.chunk_id && s.chunk_id != null && (
            <div className="mt-1 text-[10px] font-mono text-emerald-700">
              ✓ Verifier (Claude Opus 4.8): Kaynak {s.chunk_id} doğru, judge ilk &quot;{s.chunk_id_judge}&quot; demişti → düzeltildi
            </div>
          )}
          {s.verifier_status === "supported" && s.chunk_id_judge === s.chunk_id && (
            <div className="mt-1 text-[10px] font-mono text-emerald-700">
              ✓ Verifier (Claude Opus 4.8): Kaynak {s.chunk_id} onayladı
            </div>
          )}
          {s.verifier_status === "not_supported" && (
            <div className="mt-1 text-[10px] font-mono text-amber-700">
              ✗ Verifier (Claude Opus 4.8): hiçbir kaynakta anlamsal destek yok → drop
            </div>
          )}
          {(s.verifier_status === "llm_error" || s.verifier_status === "parse_error" || s.verifier_status === "missing_from_llm") && (
            <div className="mt-1 text-[10px] font-mono text-paytar-muted">
              ℹ Verifier hata verdi ({s.verifier_status}) — hardcode sonucu kullanılıyor
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {isClaim ? (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-blue-100 text-blue-800 uppercase tracking-wider">claim</span>
          ) : (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-paytar-surface2 text-paytar-muted uppercase tracking-wider">filler</span>
          )}
          {dropped ? (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-destructive/20 text-destructive uppercase tracking-wider">
              ✗ drop
            </span>
          ) : isClaim && s.chunk_id ? (
            <button
              onClick={() => openChunk(s.chunk_id as number, s.text, s.evidence ?? undefined)}
              className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-paytar-accent-soft text-paytar-accent-ink hover:bg-paytar-accent hover:text-paytar-surface transition-colors uppercase tracking-wider"
              title="Kaynak metnini aç"
            >
              Kaynak {s.chunk_id}
            </button>
          ) : (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm bg-paytar-accent-soft text-paytar-accent-ink uppercase tracking-wider">✓ keep</span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  CHUNK MODAL — tam metin + sentence highlight                */
/* ─────────────────────────────────────────────────────────── */

function ChunkModal({
  chunk, chunkId, highlightSentence, evidence, onClose,
}: {
  chunk: ChunkFull | undefined;
  chunkId: number;
  highlightSentence: string | null;
  /** Judge'in chunk'tan birebir aldigi alinti — varsa highlight onunla yapilir. */
  evidence: string | null;
  onClose: () => void;
}) {
  if (!chunk) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
        <div
          className="bg-paytar-surface border border-paytar-line rounded-2xl p-5 max-w-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-serif text-lg">Kaynak {chunkId}</h3>
            <button onClick={onClose} className="text-paytar-muted hover:text-paytar-ink">
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-sm text-paytar-muted">Kaynak metni bulunamadı (chunks listesinde yok).</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-paytar-surface border border-paytar-line rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-paytar-line">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-[11px] tracking-wider uppercase text-paytar-accent-ink">
                Kaynak {chunkId}
              </span>
              {chunk.language && (
                <span className={`font-mono text-[10px] px-1 py-0.5 rounded ${
                  chunk.language === "en" ? "bg-blue-100 text-blue-800" : "bg-amber-100 text-amber-800"
                }`}>{chunk.language.toUpperCase()}</span>
              )}
              <span className="font-mono text-[10px] text-paytar-muted">σ={chunk.score?.toFixed(4)}</span>
            </div>
            <h3 className="font-serif text-lg text-paytar-ink">{chunk.title}</h3>
            {highlightSentence && (
              <div className="mt-2 text-[11px] font-mono text-paytar-muted">
                Aranan cümle: <span className="text-paytar-ink2 italic">&quot;{highlightSentence.slice(0, 120)}{highlightSentence.length > 120 ? "..." : ""}&quot;</span>
              </div>
            )}
            {evidence && (
              <div className="mt-1 text-[11px] font-mono text-paytar-accent-ink">
                Destek alıntısı (judge): <span className="text-paytar-ink2 italic">&quot;{evidence.slice(0, 160)}{evidence.length > 160 ? "..." : ""}&quot;</span>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center text-paytar-muted hover:bg-paytar-surface2"
            aria-label="Kapat"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <ChunkBody text={chunk.text} highlight={highlightSentence} evidence={evidence} />
        </div>

        <div className="px-5 py-3 border-t border-paytar-line font-mono text-[10px] text-paytar-muted flex justify-between">
          <span>{chunk.text.length} char</span>
          <button onClick={onClose} className="text-paytar-accent-ink hover:underline">Kapat (esc)</button>
        </div>
      </div>
    </div>
  );
}

function ChunkBody({
  text, highlight, evidence,
}: { text: string; highlight: string | null; evidence: string | null }) {
  // Once evidence (judge'in birebir alintisi) ile dene; yoksa cumlenin kendisi
  // (strict matcher; parafraz cumle eslesmezse null → yanlis yesil olusmaz).
  const matchedRange =
    (evidence && findEvidenceRange(text, evidence)) ||
    (highlight && findEvidenceRange(text, highlight)) ||
    null;
  if (!matchedRange) {
    return <pre className="font-sans text-[13px] text-paytar-ink whitespace-pre-wrap leading-relaxed">{text}</pre>;
  }
  const [start, end] = matchedRange;
  return (
    <pre className="font-sans text-[13px] text-paytar-ink whitespace-pre-wrap leading-relaxed">
      {text.slice(0, start)}
      <mark className="bg-paytar-accent-soft text-paytar-accent-ink px-0.5 rounded">
        {text.slice(start, end)}
      </mark>
      {text.slice(end)}
    </pre>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  FINAL RESPONSE — inline [Kaynak N] tiklanabilir            */
/* ─────────────────────────────────────────────────────────── */

function FinalResponse({ resp, openChunk }: { resp: ChatResponse; openChunk: OpenChunkFn }) {
  const citations = resp.sentence_citations ?? [];
  return (
    <section className="bg-paytar-surface border border-paytar-accent rounded-2xl p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-serif text-lg text-paytar-ink">Final response</h2>
        <span className="font-mono text-[10px] text-paytar-muted tracking-wider">
          {resp.response.length} char · confidence={resp.evidence_confidence} ·
          {citations.length} cümle (claim={citations.filter((s) => s.type === "claim" && s.supported).length}, filler={citations.filter((s) => s.type === "filler").length}, dropped={citations.filter((s) => !s.supported).length})
        </span>
      </div>
      <div className="font-sans text-sm text-paytar-ink leading-relaxed whitespace-pre-wrap">
        {renderResponseWithCitations(resp.response, openChunk, citations)}
      </div>
    </section>
  );
}

/**
 * Yanit metnindeki "[Kaynak N]" desenlerini tiklanabilir butonlara cevir.
 * Her chunk_id icin K'inci geciste citations listesindeki K'inci claim'i
 * acmaya yollar (per-occurrence eslestirme). Boylece ayni chunk farkli
 * cumlelerden referans alindiginda her tikla dogru cumle/evidence gelir.
 */
function renderResponseWithCitations(
  text: string,
  openChunk: OpenChunkFn,
  citations: SentenceCitation[],
): React.ReactNode {
  const claimsByChunk = new Map<number, SentenceCitation[]>();
  for (const c of citations) {
    if (c.type !== "claim" || !c.supported || c.chunk_id == null) continue;
    if (!claimsByChunk.has(c.chunk_id)) claimsByChunk.set(c.chunk_id, []);
    claimsByChunk.get(c.chunk_id)!.push(c);
  }
  const counter: Record<number, number> = {};

  const pattern = /\[Kaynak\s+(\d+)\]/g;
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  let keyN = 0;

  while ((match = pattern.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    const chunkId = parseInt(match[1], 10);
    if (start > cursor) {
      parts.push(<span key={`t${keyN++}`}>{text.slice(cursor, start)}</span>);
    }
    const occ = counter[chunkId] ?? 0;
    counter[chunkId] = occ + 1;
    const matchingClaim = claimsByChunk.get(chunkId)?.[occ];
    parts.push(
      <button
        key={`c${keyN++}`}
        onClick={() => openChunk(chunkId, matchingClaim?.text, matchingClaim?.evidence ?? undefined)}
        className="font-mono text-[10px] mx-0.5 px-1.5 py-0.5 rounded bg-paytar-accent-soft text-paytar-accent-ink hover:bg-paytar-accent hover:text-paytar-surface transition-colors align-baseline"
        title={`Kaynak ${chunkId} metnini aç`}
      >
        Kaynak {chunkId}
      </button>,
    );
    cursor = end;
  }
  if (cursor < text.length) {
    parts.push(<span key={`t${keyN++}`}>{text.slice(cursor)}</span>);
  }
  return parts;
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
