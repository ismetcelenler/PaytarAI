"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { BookOpen, HelpCircle, X } from "lucide-react";
import { PaytarMark } from "./brand";
import { notYetImplemented } from "@/lib/paytar";
import { findEvidenceRange } from "@/lib/highlight";
import type {
  UIMessage,
  Source,
  ChunkFull,
  SentenceCitation,
} from "@/types/chat";

export function UserBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex justify-end mb-6">
      <div className="max-w-[85%] px-4 py-3 bg-paytar-surface2 border border-paytar-line rounded-[16px_16px_4px_16px] font-sans text-[14.5px] leading-relaxed text-paytar-ink whitespace-pre-wrap">
        {children}
      </div>
    </div>
  );
}

interface AssistantBubbleProps {
  message: UIMessage;
  showActions?: boolean;
}

export function AssistantBubble({
  message,
  showActions = true,
}: AssistantBubbleProps) {
  // Clarification mesajlari ayri component'le render edilir (LLM atif yok,
  // strukturli sorular var).
  if (message.kind === "clarification" && message.clarification) {
    return <ClarificationBubble message={message} />;
  }

  // Modal: tikladigi [Kaynak N] icin acilan chunk
  const [openChunkId, setOpenChunkId] = useState<number | null>(null);
  const [openSentenceText, setOpenSentenceText] = useState<string | null>(null);
  const [openEvidence, setOpenEvidence] = useState<string | null>(null);

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

  // Her chunk_id icin desteklenen claim cumlelerinin SIRALI listesi.
  // [Kaynak N] etiketinin K'inci geciside listenin K'inci cumlesi gosterilir.
  const claimsByChunk = buildClaimsByChunk(message.sentenceCitations);

  return (
    <div className="mb-6">
      {/* meta header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-[22px] h-[22px] rounded bg-paytar-accent flex items-center justify-center text-paytar-surface">
          <PaytarMark size={14} />
        </div>
        <span className="font-mono text-[10px] text-paytar-muted tracking-widest uppercase">
          paytar · yanıt
        </span>
        {message.criticAttempts !== undefined && message.criticAttempts > 0 && (
          <span className="font-mono text-[10px] text-paytar-muted tracking-wider uppercase">
            · {message.criticAttempts} critic retry
          </span>
        )}
      </div>

      {/* body — [Kaynak N] etiketleri tiklanabilir buton olarak render edilir.
          Counter object hangi chunk_id'nin kacinci geciside oldugumuzu tutar. */}
      <div className="font-sans text-[15.5px] leading-[1.62] text-paytar-ink paytar-prose">
        {(() => {
          const counter: Record<number, number> = {};
          return (
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p>{renderWithCitations(children, message, openChunk, claimsByChunk, counter)}</p>
                ),
                li: ({ children }) => (
                  <li>{renderWithCitations(children, message, openChunk, claimsByChunk, counter)}</li>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          );
        })()}
      </div>

      {/* sources */}
      {message.sources && message.sources.length > 0 && (
        <div className="mt-4 space-y-1.5">
          <div className="font-mono text-[10px] text-paytar-muted tracking-widest uppercase mb-2">
            Kaynaklar · {message.sources.length}
          </div>
          {message.sources.map((src, i) => (
            <SourceRow
              key={i}
              index={i + 1}
              source={src}
              onClick={
                message.chunks && message.chunks[i]
                  ? () => openChunk(i + 1)
                  : undefined
              }
            />
          ))}
        </div>
      )}

      {/* actions */}
      {showActions && (
        <div className="flex flex-wrap gap-1.5 mt-4 pt-3 border-t border-dashed border-paytar-line">
          {[
            { label: "Vakaya kaydet", todo: "Vakaya kaydetme" },
            { label: "Devam ettir", todo: "Yanıtı devam ettirme" },
            { label: "Kopyala", todo: null as string | null },
          ].map(({ label, todo }) => (
            <button
              key={label}
              onClick={() => {
                if (todo) return notYetImplemented(todo);
                navigator.clipboard?.writeText(message.content);
              }}
              className="px-3 py-1.5 bg-transparent border border-paytar-line rounded-full font-sans text-[12.5px] text-paytar-ink2 hover:bg-paytar-surface transition-colors"
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {openChunkId !== null && (
        <ChunkModal
          chunk={message.chunks?.[openChunkId - 1]}
          chunkId={openChunkId}
          highlightSentence={openSentenceText}
          evidence={openEvidence}
          onClose={closeChunk}
        />
      )}
    </div>
  );
}

/** chunk_id → o chunk'a baglanan claim cumlelerinin SIRALI listesi. */
function buildClaimsByChunk(
  citations: SentenceCitation[] | undefined,
): Map<number, SentenceCitation[]> {
  const map = new Map<number, SentenceCitation[]>();
  if (!citations) return map;
  for (const c of citations) {
    if (c.type !== "claim" || !c.supported || c.chunk_id == null) continue;
    if (!map.has(c.chunk_id)) map.set(c.chunk_id, []);
    map.get(c.chunk_id)!.push(c);
  }
  return map;
}

/* ─────────────────────────────────────────────────────────── */
/*  Citation rendering — [Kaynak N] -> clickable button         */
/* ─────────────────────────────────────────────────────────── */

type OpenChunkFn = (id: number, sentenceText?: string, evidence?: string) => void;

const CITATION_RE = /\[Kaynak\s+(\d+)\]/g;

/**
 * ReactMarkdown'in p/li icine yerlestirdigi children'i traverse ederek
 * string node'larindaki "[Kaynak N]" desenlerini tiklanabilir butonlara cevirir.
 * counter: chunk_id basina kacinci geciste oldugumuzu tutar — buton
 * acildiginda dogru cumleyi ve evidence'i secebilmek icin.
 */
function renderWithCitations(
  children: React.ReactNode,
  message: UIMessage,
  openChunk: OpenChunkFn,
  claimsByChunk: Map<number, SentenceCitation[]>,
  counter: Record<number, number>,
): React.ReactNode {
  const transform = (node: React.ReactNode, idx: number): React.ReactNode => {
    if (typeof node === "string") {
      return splitStringWithCitations(node, message, openChunk, claimsByChunk, counter, `s${idx}`);
    }
    if (Array.isArray(node)) {
      return node.map((c, i) => transform(c, i));
    }
    if (
      typeof node === "object" &&
      node !== null &&
      "props" in node &&
      // @ts-expect-error — runtime kontrol
      node.props?.children !== undefined
    ) {
      // @ts-expect-error
      const newChildren = transform(node.props.children, idx);
      return { ...node, props: { ...node.props, children: newChildren } };
    }
    return node;
  };
  return transform(children, 0);
}

function splitStringWithCitations(
  text: string,
  message: UIMessage,
  openChunk: OpenChunkFn,
  claimsByChunk: Map<number, SentenceCitation[]>,
  counter: Record<number, number>,
  keyPrefix: string,
): React.ReactNode {
  const out: React.ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  let n = 0;
  const re = new RegExp(CITATION_RE.source, "g");
  while ((match = re.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    const chunkId = parseInt(match[1], 10);
    if (start > cursor) out.push(text.slice(cursor, start));
    // chunkId icin kacinci geciste oldugumuzu bul → o sirali claim'i sec
    const occurrenceIdx = counter[chunkId] ?? 0;
    counter[chunkId] = occurrenceIdx + 1;
    const claimList = claimsByChunk.get(chunkId) ?? [];
    const matchedClaim = claimList[occurrenceIdx];
    out.push(
      <CitationPill
        key={`${keyPrefix}-${n++}`}
        chunkId={chunkId}
        sentenceText={matchedClaim?.text}
        evidence={matchedClaim?.evidence ?? undefined}
        disabled={!message.chunks || !message.chunks[chunkId - 1]}
        onClick={openChunk}
      />,
    );
    cursor = end;
  }
  if (cursor < text.length) out.push(text.slice(cursor));
  return out;
}

function CitationPill({
  chunkId, sentenceText, evidence, disabled, onClick,
}: {
  chunkId: number;
  sentenceText?: string;
  evidence?: string;
  disabled: boolean;
  onClick: OpenChunkFn;
}) {
  if (disabled) {
    return (
      <span className="font-mono text-[11px] mx-0.5 px-1 py-0.5 rounded bg-paytar-surface2 text-paytar-muted align-baseline">
        [Kaynak {chunkId}]
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onClick(chunkId, sentenceText, evidence)}
      className="font-mono text-[11px] mx-0.5 px-1.5 py-0.5 rounded bg-paytar-accent-soft text-paytar-accent-ink hover:bg-paytar-accent hover:text-paytar-surface transition-colors align-baseline cursor-pointer"
      title={`Kaynak ${chunkId} metnini aç`}
    >
      [Kaynak {chunkId}]
    </button>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  Chunk modal — tam metin + sentence highlight                */
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
          <p className="text-sm text-paytar-muted">Kaynak metni bulunamadı.</p>
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
                Atıf yapılan cümle: <span className="text-paytar-ink2 italic">&quot;{highlightSentence.slice(0, 140)}{highlightSentence.length > 140 ? "..." : ""}&quot;</span>
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
          <button onClick={onClose} className="text-paytar-accent-ink hover:underline">Kapat</button>
        </div>
      </div>
    </div>
  );
}

function ChunkBody({
  text, highlight, evidence,
}: { text: string; highlight: string | null; evidence: string | null }) {
  // Once evidence (judge'in birebir alintisi) ile dene — chunkta gercekten gecmesi yuksek.
  // Yoksa cumlenin kendisiyle dene (strict matcher; parafraz cumle eslesmezse
  // null doner, yanlis yesil olusturmaz). Hicbiri yoksa highlight yok.
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

function SourceRow({
  index, source, onClick,
}: {
  index: number;
  source: Source;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={() => {
        if (onClick) onClick();
        else notYetImplemented(`Kaynak detayı: ${source.title}`);
      }}
      className="flex items-start gap-2.5 w-full p-2.5 rounded-lg bg-paytar-surface2 border border-paytar-line hover:border-paytar-accent/40 transition-colors text-left"
    >
      <div className="flex items-center justify-center w-5 h-5 rounded bg-paytar-accent-soft text-paytar-accent-ink font-mono text-[10px] font-medium flex-shrink-0 mt-0.5">
        {index}
      </div>
      <BookOpen className="w-3.5 h-3.5 text-paytar-muted mt-1 flex-shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="font-sans text-[13px] text-paytar-ink truncate">
          {source.title}
        </div>
        <div className="font-sans text-[12px] text-paytar-muted line-clamp-2 mt-0.5 leading-snug">
          {source.snippet}
        </div>
      </div>
      <div className="font-mono text-[10px] text-paytar-muted tracking-wider flex-shrink-0 mt-1">
        {source.score.toFixed(2)}
      </div>
    </button>
  );
}

/* ─────────────────────────────────────────────────────────── */
/*  CLARIFICATION BUBBLE — sarı accent, takip sorusu UI         */
/* ─────────────────────────────────────────────────────────── */

function ClarificationBubble({ message }: { message: UIMessage }) {
  const c = message.clarification;
  if (!c) {
    // Fallback: kind=clarification ama payload yoksa düz metin
    return (
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-[22px] h-[22px] rounded bg-amber-500 flex items-center justify-center text-white">
            <HelpCircle className="w-3.5 h-3.5" />
          </div>
          <span className="font-mono text-[10px] text-amber-700 tracking-widest uppercase">
            paytar · takip sorusu
          </span>
        </div>
        <div className="font-sans text-[15px] leading-relaxed whitespace-pre-wrap text-paytar-ink2 bg-amber-50/40 border border-amber-300/40 rounded-2xl px-4 py-3">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-[22px] h-[22px] rounded bg-amber-500 flex items-center justify-center text-white">
          <HelpCircle className="w-3.5 h-3.5" />
        </div>
        <span className="font-mono text-[10px] text-amber-700 tracking-widest uppercase">
          paytar · takip sorusu
        </span>
        <span className="font-mono text-[10px] text-amber-700 tracking-wider uppercase px-2 py-0.5 bg-amber-100 border border-amber-300/50 rounded-sm">
          biraz daha bilgi gerek
        </span>
      </div>

      <div className="bg-amber-50/40 border border-amber-300/40 rounded-2xl overflow-hidden">
        {/* Intro */}
        <div className="px-4 py-3 border-b border-amber-300/30 font-sans text-[15px] text-paytar-ink leading-relaxed">
          {c.intro}
        </div>

        {/* Differentials */}
        {c.differentials.length > 0 && (
          <div className="px-4 py-3 border-b border-amber-300/30">
            <div className="font-mono text-[10px] tracking-wider uppercase text-amber-700 mb-2">
              Olası nedenler
            </div>
            <div className="flex flex-wrap gap-1.5">
              {c.differentials.map((d, i) => (
                <span
                  key={i}
                  className="font-sans text-[13px] px-2.5 py-1 bg-white border border-amber-300/50 rounded-full text-paytar-ink2"
                >
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Follow-up questions */}
        {c.follow_up_questions.length > 0 && (
          <div className="px-4 py-3">
            <div className="font-mono text-[10px] tracking-wider uppercase text-amber-700 mb-2">
              Daha doğru cevap için söyler misin
            </div>
            <ol className="space-y-1.5">
              {c.follow_up_questions.map((q, i) => (
                <li
                  key={i}
                  className="font-sans text-[14px] text-paytar-ink flex gap-2"
                >
                  <span className="font-mono text-amber-700 tabular-nums flex-shrink-0">
                    {i + 1}.
                  </span>
                  <span>{q}</span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      <div className="mt-2 font-mono text-[10px] tracking-wider text-paytar-muted px-1">
        Yanıtın doğru cevabı yakalamamıza yardım edecek. Aşağıdan yaz.
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 mb-6 text-paytar-muted">
      <div className="w-[22px] h-[22px] rounded bg-paytar-accent flex items-center justify-center text-paytar-surface">
        <PaytarMark size={14} />
      </div>
      <span className="font-mono text-[10px] text-paytar-accent-ink tracking-wider uppercase px-2 py-0.5 bg-paytar-accent-soft rounded-sm">
        yazıyor
      </span>
      <span className="flex gap-1 ml-1">
        <span
          className="w-1.5 h-1.5 rounded-full bg-paytar-accent animate-bounce"
          style={{ animationDelay: "0s" }}
        />
        <span
          className="w-1.5 h-1.5 rounded-full bg-paytar-accent animate-bounce"
          style={{ animationDelay: "0.15s" }}
        />
        <span
          className="w-1.5 h-1.5 rounded-full bg-paytar-accent animate-bounce"
          style={{ animationDelay: "0.3s" }}
        />
      </span>
    </div>
  );
}
