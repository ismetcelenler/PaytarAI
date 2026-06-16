"use client";

/**
 * PipelineProgress — Backend stream sirasinda canli adim gostergesi.
 *
 * SSE'den gelen "step" event'lerini tuketir. Her node bir UI adimina karsilik
 * gelir. Bitenler check, mevcut spinner ile gosterilir; bekleyenler muted.
 *
 * Pre-defined steps (LangGraph node sirasiyla):
 *   scope_check      → "Sorun analiz ediliyor"
 *   compress         → (kisa, gostermeye degmez; scope ile birlikte)
 *   retriever        → "Kaynaklarda taranıyor"
 *   generator        → "Yanıt yazılıyor"
 *   claim_attribution→ "Atıflar doğrulanıyor"
 *   confidence       → "Son kontrol"
 *
 * "Bilinmeyen" node geldiğinde son adıma fold ederiz.
 */

import { useMemo } from "react";
import { Check, Loader2 } from "lucide-react";
import { PaytarMark } from "./brand";

export interface PipelineStepEvent {
  node: string;
  ms_since_start: number;
  step_index: number;
}

interface PipelineStep {
  key: string;
  /** Bu UI adımını tetikleyen backend node adlari (birden fazla olabilir,
   *  herhangi biri görülünce bu adım "in progress" sayılır). */
  nodes: string[];
  label: string;
}

const STEPS: PipelineStep[] = [
  { key: "analyze", nodes: ["scope_check", "compress"], label: "Soru analiz ediliyor" },
  { key: "retrieve", nodes: ["retriever"], label: "Kaynaklarda taranıyor" },
  { key: "generate", nodes: ["generator"], label: "Yanıt yazılıyor" },
  { key: "attribute", nodes: ["claim_attribution"], label: "Atıflar doğrulanıyor" },
  { key: "finalize", nodes: ["confidence"], label: "Son kontrol yapılıyor" },
];

interface PipelineProgressProps {
  /** Backend'den gelen tamamlanmis step event'lar (kronolojik sırada). */
  steps: PipelineStepEvent[];
  /** Pipeline son adımdan sonra hala devam ediyorsa true. */
  isStreaming: boolean;
  /** Toplam elapsed (ms) — başlık çubuğunda gösterilir. */
  elapsedMs: number;
}

export function PipelineProgress({
  steps,
  isStreaming,
  elapsedMs,
}: PipelineProgressProps) {
  // Her UI adımı için durumu hesapla:
  //   "done"     → bu adımın node'larından en az biri "completed" event'i geldi
  //   "active"   → henüz completed gelmedi ama önceki adım tamamlandı
  //   "pending"  → daha sırası gelmedi
  const stepStates = useMemo(() => {
    // backend'in tamamladigi node setini cikar
    const doneNodes = new Set(steps.map((s) => s.node));

    // Her UI adımının tamamlanma sırası — bu adımın node'larından herhangi biri
    // doneNodes'ta varsa adım tamamlanmış sayılır.
    const completed: boolean[] = STEPS.map((ui) =>
      ui.nodes.some((n) => doneNodes.has(n))
    );

    // İlk tamamlanmayan adım "active" (eğer hala streaming ise), sonrası pending
    const firstPendingIdx = completed.findIndex((d) => !d);
    const activeIdx = isStreaming && firstPendingIdx !== -1 ? firstPendingIdx : -1;

    return STEPS.map((_, i) => {
      if (completed[i]) return "done" as const;
      if (i === activeIdx) return "active" as const;
      return "pending" as const;
    });
  }, [steps, isStreaming]);

  // Her UI adımı için ms latency'sini topla (gosterim icin)
  const stepLatency = useMemo(() => {
    // Adım [i] için: bu adımı tetikleyen node'lardan birinin ms_since_start'i alınır,
    // önceki adımın bittiği ms'den çıkartılır.
    const result: (number | null)[] = STEPS.map(() => null);
    let prevMs = 0;
    for (let i = 0; i < STEPS.length; i++) {
      const myStepEv = steps.find((s) => STEPS[i].nodes.includes(s.node));
      if (myStepEv) {
        result[i] = myStepEv.ms_since_start - prevMs;
        prevMs = myStepEv.ms_since_start;
      }
    }
    return result;
  }, [steps]);

  return (
    <div className="mb-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-[22px] h-[22px] rounded bg-paytar-accent flex items-center justify-center text-paytar-surface">
          <PaytarMark size={14} />
        </div>
        <span className="font-mono text-[10px] text-paytar-muted tracking-widest uppercase">
          paytar · işleniyor
        </span>
        <span className="font-mono text-[10px] text-paytar-accent-ink tracking-wider uppercase px-2 py-0.5 bg-paytar-accent-soft rounded-sm tabular-nums">
          {(elapsedMs / 1000).toFixed(1)}s
        </span>
      </div>

      {/* Step list */}
      <div className="border border-paytar-line rounded-2xl bg-paytar-surface overflow-hidden">
        {STEPS.map((step, i) => {
          const state = stepStates[i];
          const latency = stepLatency[i];
          return (
            <StepRow
              key={step.key}
              label={step.label}
              state={state}
              latencyMs={latency}
              isLast={i === STEPS.length - 1}
            />
          );
        })}
      </div>
    </div>
  );
}

function StepRow({
  label, state, latencyMs, isLast,
}: {
  label: string;
  state: "done" | "active" | "pending";
  latencyMs: number | null;
  isLast: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-3 px-4 py-2.5 ${
        isLast ? "" : "border-b border-paytar-line"
      } ${state === "active" ? "bg-paytar-accent-soft/50" : ""}`}
    >
      <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
        {state === "done" ? (
          <div className="w-5 h-5 rounded-full bg-paytar-accent text-paytar-surface flex items-center justify-center">
            <Check className="w-3 h-3" strokeWidth={3} />
          </div>
        ) : state === "active" ? (
          <Loader2 className="w-4 h-4 text-paytar-accent-ink animate-spin" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-paytar-muted/30" />
        )}
      </div>
      <span
        className={`font-sans text-[13.5px] flex-1 ${
          state === "done"
            ? "text-paytar-ink2"
            : state === "active"
            ? "text-paytar-accent-ink font-medium"
            : "text-paytar-muted"
        }`}
      >
        {label}
      </span>
      {latencyMs !== null && state === "done" && (
        <span className="font-mono text-[10px] text-paytar-muted tracking-wider tabular-nums">
          {(latencyMs / 1000).toFixed(1)}s
        </span>
      )}
    </div>
  );
}
