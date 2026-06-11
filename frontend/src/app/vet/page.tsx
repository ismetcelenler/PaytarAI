"use client";

import { useEffect, useRef } from "react";
import { usePaytarChat } from "@/hooks/use-paytar-chat";
import { PaytarSidebar } from "@/components/paytar/sidebar";
import { PaytarTopBar } from "@/components/paytar/topbar";
import { PaytarEmptyState } from "@/components/paytar/empty-state";
import { PaytarComposer } from "@/components/paytar/composer";
import {
  AssistantBubble,
  TypingIndicator,
  UserBubble,
} from "@/components/paytar/message";

const SUGGESTED = [
  { tag: "Mastitis", q: "Holstein'da klinik mastitis nasıl ayırt edilir?" },
  { tag: "Buzağı", q: "Buzağı ishali — sıvı tedavi protokolü" },
  { tag: "Aşılama", q: "Sürü aşılama takvimi 2026 — Türkiye" },
  { tag: "Verim", q: "Süt veriminde ani düşüş — olası nedenler" },
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
  const { messages, pending, error, send, reset } = usePaytarChat("veterinarian");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, pending]);

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
              {pending && <TypingIndicator />}
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
          onSend={(text) => send(text)}
        />
      </div>
    </div>
  );
}
