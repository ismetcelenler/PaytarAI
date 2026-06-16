"use client";

import { useEffect, useRef, useState } from "react";
import { usePaytarChat } from "@/hooks/use-paytar-chat";
import { PaytarSidebar } from "@/components/paytar/sidebar";
import { PaytarTopBar } from "@/components/paytar/topbar";
import { PaytarEmptyState } from "@/components/paytar/empty-state";
import { PaytarComposer } from "@/components/paytar/composer";
import { PipelineProgress } from "@/components/paytar/pipeline-progress";
import {
  AssistantBubble,
  UserBubble,
} from "@/components/paytar/message";

const SUGGESTED = [
  { tag: "Buzağı ishali", q: "Yenidoğan buzağıda ishal: etiyoloji ve sıvı-elektrolit tedavisi" },
  { tag: "Süt humması", q: "Süt ineğinde doğum sonrası hipokalsemi (süt humması) tedavisi nedir?" },
  { tag: "Mastitis", q: "Holstein'da klinik mastitisin ayırıcı tanısı nasıl yapılır?" },
  { tag: "Ketozis", q: "Subklinik ketozisin klinik bulguları ve tanı kriterleri" },
  { tag: "Abomasum", q: "Sol abomasum deplasmanı (LDA) tanısı ve sağaltımı" },
  { tag: "Metritis", q: "Doğum sonrası akut metritiste tedavi yaklaşımı" },
  { tag: "Koksidiyoz", q: "Buzağılarda koksidiyozun belirtileri ve tedavisi" },
  { tag: "Listeriozis", q: "Sığırda listeriozisin nörolojik bulguları nelerdir?" },
  { tag: "Hardware", q: "Travmatik retikuloperitonit (hardware disease) tanısı" },
  { tag: "Kolostrum", q: "Buzağıda pasif bağışıklık için kolostrum yönetimi" },
];

const HISTORY = [
  { id: "h1", title: "Neonatal buzağı ishali — vaka #234", when: "Bugün" },
  { id: "h2", title: "Aşılama takvimi · Holstein sürüsü", when: "Bugün" },
  { id: "h3", title: "Topallık skoru ve dijital dermatit", when: "Dün" },
  { id: "h4", title: "Subklinik ketozis — taramada NEFA", when: "Dün" },
  { id: "h5", title: "Çiğ süt SCC sınırları, TR yönetmelik", when: "2 gün" },
  { id: "h6", title: "Doğum sonrası metritis — protokol", when: "Geçen hafta" },
];

export default function VetDashboard() {
  const {
    messages, pending, error, send, reset,
    streamSteps, streamStartedAt,
  } = usePaytarChat("veterinarian");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Live elapsed counter — 100ms tick while streaming
  const [elapsedMs, setElapsedMs] = useState(0);
  useEffect(() => {
    if (!streamStartedAt) {
      setElapsedMs(0);
      return;
    }
    const t = setInterval(() => setElapsedMs(Date.now() - streamStartedAt), 100);
    return () => clearInterval(t);
  }, [streamStartedAt]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, pending, streamSteps.length]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex w-full h-screen bg-paytar-bg text-paytar-ink font-sans">
      <PaytarSidebar
        subtitle="VETERİNER · 2026.Q1"
        userName="Dr. Demir"
        userInitial="D"
        userMeta="SAHA · ÇORLU"
        history={HISTORY}
        activeId={isEmpty ? undefined : "current"}
        onNewChat={reset}
      />

      <div className="flex-1 min-w-0 h-full flex flex-col">
        <PaytarTopBar
          title={isEmpty ? "Yeni sohbet" : "Vaka · klinik karar destek"}
          meta={
            isEmpty
              ? "Boş tuval · soru ile başla"
              : "AKTİF VAKA · veteriner modu"
          }
        />

        <div ref={scrollRef} className="flex-1 overflow-y-auto py-7">
          {isEmpty ? (
            <PaytarEmptyState
              greetingName="Dr. Demir"
              description="Sahaya çıkmadan, vakaya başlamadan sor. Saha verisi + güncel mevzuat ile yanıtlıyorum."
              suggested={SUGGESTED}
              onPick={(q) => send(q)}
            />
          ) : (
            <div className="max-w-[720px] mx-auto px-5">
              {messages.map((m) =>
                m.role === "user" ? (
                  <UserBubble key={m.id}>{m.content}</UserBubble>
                ) : (
                  <AssistantBubble key={m.id} message={m} />
                )
              )}
              {pending && (
                <PipelineProgress
                  steps={streamSteps}
                  isStreaming={pending}
                  elapsedMs={elapsedMs}
                />
              )}
              {error && (
                <div className="font-mono text-[11px] text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2 mt-2">
                  {error}
                </div>
              )}
            </div>
          )}
        </div>

        <PaytarComposer
          placeholder="Klinik bulgular, ilaç adı veya doz sorusu yaz…"
          disabled={pending}
          onSend={(text, opts) => send(text, { responseLength: opts.responseLength })}
        />
      </div>
    </div>
  );
}
