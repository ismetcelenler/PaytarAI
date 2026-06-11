"use client";

import ReactMarkdown from "react-markdown";
import { BookOpen, ShieldCheck } from "lucide-react";
import { PaytarMark } from "./brand";
import { notYetImplemented } from "@/lib/paytar";
import type {
  UIMessage,
  EvidenceConfidence,
  Source,
} from "@/types/chat";

const CONFIDENCE_LABEL: Record<EvidenceConfidence, string> = {
  high: "Yüksek güven",
  medium: "Orta güven",
  low: "Düşük güven",
  insufficient: "Yetersiz kanıt",
};

const CONFIDENCE_DOT: Record<EvidenceConfidence, string> = {
  high: "bg-emerald-500",
  medium: "bg-amber-500",
  low: "bg-orange-500",
  insufficient: "bg-red-500",
};

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
        {message.confidence && (
          <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-paytar-accent-ink tracking-wider uppercase px-2 py-0.5 bg-paytar-accent-soft rounded-sm">
            <ShieldCheck className="w-3 h-3" />
            {CONFIDENCE_LABEL[message.confidence]}
          </span>
        )}
        {message.criticAttempts !== undefined && message.criticAttempts > 0 && (
          <span className="font-mono text-[10px] text-paytar-muted tracking-wider uppercase">
            · {message.criticAttempts} critic retry
          </span>
        )}
      </div>

      {/* body */}
      <div className="font-sans text-[15.5px] leading-[1.62] text-paytar-ink paytar-prose">
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      {/* sources */}
      {message.sources && message.sources.length > 0 && (
        <div className="mt-4 space-y-1.5">
          <div className="font-mono text-[10px] text-paytar-muted tracking-widest uppercase mb-2">
            Kaynaklar · {message.sources.length}
          </div>
          {message.sources.map((src, i) => (
            <SourceRow key={i} index={i + 1} source={src} />
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
    </div>
  );
}

function SourceRow({ index, source }: { index: number; source: Source }) {
  return (
    <button
      onClick={() => notYetImplemented(`Kaynak detayı: ${source.title}`)}
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
