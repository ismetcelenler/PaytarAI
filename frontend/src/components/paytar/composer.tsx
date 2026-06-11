"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { ArrowUp, Mic, Plus } from "lucide-react";
import { notYetImplemented } from "@/lib/paytar";

interface PaytarComposerProps {
  placeholder?: string;
  disabled?: boolean;
  /** Submit edildiğinde çağırılır, returnde mesajı temizler. */
  onSend: (text: string) => void;
  /** Sayfa-dışı bağlanan (örn. semptom seçimi) bir input'u dışarıdan setlemek için. */
  externalValue?: string;
  hint?: string;
}

export function PaytarComposer({
  placeholder = "Vakayı yaz, foto ekle, ya da kılavuza sor…",
  disabled = false,
  onSend,
  externalValue,
  hint = "↵ GÖNDER · ⇧↵ YENİ SATIR",
}: PaytarComposerProps) {
  const [text, setText] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (externalValue !== undefined) setText(externalValue);
  }, [externalValue]);

  // auto-grow
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [text]);

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="px-4 md:px-6 pt-3 pb-5 md:pb-6 bg-paytar-bg flex-shrink-0">
      <div className="max-w-[720px] mx-auto">
        <div className="flex items-end gap-2 pl-4 pr-2.5 py-2.5 bg-paytar-surface border border-paytar-line rounded-[22px] shadow-[0_2px_0_var(--cayir-line),0_12px_24px_-16px_rgba(45,42,36,0.18)]">
          <button
            onClick={() => notYetImplemented("Dosya / fotoğraf ekleme")}
            aria-label="Ek ekle"
            className="w-8 h-8 rounded-full bg-paytar-surface2 text-paytar-muted hover:text-paytar-ink flex items-center justify-center flex-shrink-0 transition-colors"
            type="button"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>

          <textarea
            ref={taRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKey}
            disabled={disabled}
            placeholder={placeholder}
            className="flex-1 bg-transparent border-0 outline-none resize-none font-sans text-[14.5px] text-paytar-ink placeholder:text-paytar-muted py-1.5 leading-relaxed disabled:opacity-60"
          />

          <button
            onClick={() => notYetImplemented("Sesli komut")}
            aria-label="Sesli komut"
            type="button"
            className="w-8 h-8 rounded-full text-paytar-muted hover:text-paytar-accent flex items-center justify-center flex-shrink-0 transition-colors"
          >
            <Mic className="w-4 h-4" />
          </button>

          <button
            onClick={submit}
            disabled={disabled || !text.trim()}
            aria-label="Gönder"
            type="button"
            className="w-8 h-8 rounded-full bg-paytar-accent text-paytar-surface flex items-center justify-center flex-shrink-0 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>

        <div className="flex justify-between items-center mt-2 px-1.5 font-mono text-[10px] text-paytar-muted tracking-wider">
          <span>{hint}</span>
          <span className="hidden sm:inline">
            Yanıtlar saha verisi + mevzuat ile doğrulanır
          </span>
        </div>
      </div>
    </div>
  );
}
