"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { usePaytarChat } from "@/hooks/use-paytar-chat";
import { PaytarMark, PaytarWordmark } from "@/components/paytar/brand";
import { PaytarComposer } from "@/components/paytar/composer";
import {
  AssistantBubble,
  TypingIndicator,
  UserBubble,
} from "@/components/paytar/message";

interface SymptomCat {
  id: string;
  label: string;
  icon: string;
  examples: string[];
}

const SYMPTOM_CATEGORIES: SymptomCat[] = [
  { id: "digestive", label: "Sindirim", icon: "🥣", examples: ["Şişkinlik", "İshal", "Yemek yememe"] },
  { id: "respiratory", label: "Solunum", icon: "💨", examples: ["Öksürük", "Burun akıntısı", "Nefes darlığı"] },
  { id: "limb", label: "Ayak / Hareket", icon: "🦵", examples: ["Topallama", "Şişlik", "Yürüyememe"] },
  { id: "skin", label: "Deri / Yara", icon: "🩹", examples: ["Yara", "Şişlik", "Döküntü"] },
  { id: "milk", label: "Süt", icon: "🥛", examples: ["Süt azaldı", "Süt rengi değişti", "Meme şişliği"] },
  { id: "birth", label: "Doğum / Yavru", icon: "🐄", examples: ["Doğum zorluğu", "Plasenta atmama", "Yavru emmeme"] },
  { id: "general", label: "Genel Durum", icon: "🌡️", examples: ["Ateş", "Halsizlik", "Sürüden ayrılma"] },
  { id: "eye", label: "Göz", icon: "👁️", examples: ["Göz akıntısı", "Kızarıklık", "Görememe"] },
];

export default function ProducerDashboard() {
  const { messages, pending, error, send } = usePaytarChat("producer");
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, pending]);

  const isEmpty = messages.length === 0;
  const showSymptomScreen = showGuide && isEmpty;

  const sendQuery = (q: string) => {
    setShowGuide(false);
    send(q);
  };

  const pickExample = (catId: string, ex: string) => {
    const cat = SYMPTOM_CATEGORIES.find((c) => c.id === catId);
    const q = `Hayvanımın ${cat?.label.toLowerCase()} sorunu var: ${ex}`;
    sendQuery(q);
  };

  return (
    <div className="flex flex-col h-screen bg-paytar-bg text-paytar-ink font-sans">
      {/* Top bar — sade üretici versiyonu */}
      <header className="flex items-center justify-between px-4 py-3 bg-paytar-sidebar border-b border-paytar-line flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            aria-label="Geri"
            className="w-8 h-8 rounded-md flex items-center justify-center text-paytar-muted hover:bg-paytar-surface2"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="w-8 h-8 rounded-lg bg-paytar-accent flex items-center justify-center text-paytar-surface">
            <PaytarMark size={20} />
          </div>
          <PaytarWordmark subtitle="ÜRETİCİ MODU" />
        </div>
        {!showSymptomScreen && (
          <button
            onClick={() => setShowGuide(true)}
            className="font-mono text-[10px] tracking-wider uppercase text-paytar-accent-ink px-2.5 py-1 rounded-md hover:bg-paytar-surface2 transition-colors"
          >
            Semptom Rehberi
          </button>
        )}
      </header>

      {/* Main */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {showSymptomScreen ? (
          <div className="flex-1 overflow-y-auto py-8 px-5">
            <div className="max-w-lg mx-auto">
              <h2 className="font-serif text-3xl text-paytar-ink tracking-tight mb-1.5">
                Hayvanında ne <span className="italic text-paytar-accent-ink">görüyorsun</span>?
              </h2>
              <p className="font-sans text-sm text-paytar-muted mb-6 leading-relaxed">
                Bir kategori seç, sonra hangi belirti olduğunu seç. Paytar sana sade Türkçe ile cevap verecek.
              </p>

              <div className="grid grid-cols-2 gap-2.5">
                {SYMPTOM_CATEGORIES.map((cat) => {
                  const active = selectedCat === cat.id;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => setSelectedCat(active ? null : cat.id)}
                      className={`min-h-[64px] p-3 rounded-xl border text-left transition-all ${
                        active
                          ? "border-paytar-accent bg-paytar-accent-soft"
                          : "border-paytar-line bg-paytar-surface hover:border-paytar-accent/40"
                      }`}
                    >
                      <span className="text-2xl block">{cat.icon}</span>
                      <span className="block font-sans text-sm font-medium text-paytar-ink mt-1">
                        {cat.label}
                      </span>
                      <span className="block font-sans text-[11.5px] text-paytar-muted mt-0.5 leading-snug">
                        {cat.examples.join(" · ")}
                      </span>
                    </button>
                  );
                })}
              </div>

              {selectedCat && (
                <div className="mt-6 p-4 bg-paytar-accent-soft rounded-xl border border-paytar-accent/30">
                  <p className="font-sans text-sm font-medium text-paytar-accent-ink mb-3">
                    Hangi belirtiyi görüyorsun?
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SYMPTOM_CATEGORIES.find((c) => c.id === selectedCat)?.examples.map(
                      (ex) => (
                        <button
                          key={ex}
                          onClick={() => pickExample(selectedCat, ex)}
                          className="px-3.5 py-2 rounded-full bg-paytar-surface border border-paytar-accent/40 font-sans text-sm text-paytar-ink hover:bg-paytar-accent hover:text-paytar-surface hover:border-paytar-accent transition-colors"
                        >
                          {ex}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div ref={scrollRef} className="flex-1 overflow-y-auto py-6 px-5">
            <div className="max-w-lg mx-auto">
              {messages.map((m) =>
                m.role === "user" ? (
                  <UserBubble key={m.id}>{m.content}</UserBubble>
                ) : (
                  <AssistantBubble key={m.id} message={m} showActions={false} />
                )
              )}
              {pending && <TypingIndicator />}
              {error && (
                <div className="font-mono text-[11px] text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2 mt-2">
                  {error}
                </div>
              )}
            </div>
          </div>
        )}

        <PaytarComposer
          placeholder="Sorununu yaz (örn: ineğim yem yemiyor, halsiz)…"
          disabled={pending}
          onSend={(text) => sendQuery(text)}
          hint="↵ GÖNDER · ⇧↵ YENİ SATIR"
        />
      </div>
    </div>
  );
}
