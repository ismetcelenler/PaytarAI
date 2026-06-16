"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { ArrowUp, Mic, Plus } from "lucide-react";
import { notYetImplemented } from "@/lib/paytar";
import type { ResponseLength } from "@/types/chat";

interface PaytarComposerProps {
  placeholder?: string;
  disabled?: boolean;
  /** Submit edildiğinde çağırılır, returnde mesajı temizler. */
  onSend: (text: string, opts: { responseLength: ResponseLength }) => void;
  /** Sayfa-dışı bağlanan (örn. semptom seçimi) bir input'u dışarıdan setlemek için. */
  externalValue?: string;
  hint?: string;
  /** Baslangic uzunluk tercihi. Default "medium". */
  defaultLength?: ResponseLength;
  /** Length degisirse haberdar edilmek istenen parent (opsiyonel). */
  onLengthChange?: (length: ResponseLength) => void;
}

const LENGTH_OPTIONS: Array<{ value: ResponseLength; label: string; hint: string }> = [
  { value: "short", label: "Kısa", hint: "2-3 cümle, tek paragraf" },
  { value: "medium", label: "Orta", hint: "2-3 paragraf veya 4-6 madde" },
  { value: "long", label: "Uzun", hint: "4-6 paragraf veya 8-12 madde" },
];

export function PaytarComposer({
  placeholder = "Vakayı yaz, foto ekle, ya da kılavuza sor…",
  disabled = false,
  onSend,
  externalValue,
  hint = "↵ GÖNDER · ⇧↵ YENİ SATIR",
  defaultLength = "medium",
  onLengthChange,
}: PaytarComposerProps) {
  const [text, setText] = useState("");
  const [length, setLength] = useState<ResponseLength>(defaultLength);
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

  // Spam koruma esikleri — backend ile ayni. Frontend disable + tooltip ile ipucu.
  const MIN_CHARS = 12;
  const MIN_WORDS = 3;
  const wordCount = (text.trim().match(/[A-Za-zĞÜŞİÖÇğüşıöç0-9]{2,}/g) ?? []).length;
  const isTooShort =
    text.trim().length > 0 && (text.trim().length < MIN_CHARS || wordCount < MIN_WORDS);

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled || isTooShort) return;
    onSend(trimmed, { responseLength: length });
    setText("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const changeLength = (v: ResponseLength) => {
    setLength(v);
    onLengthChange?.(v);
  };

  return (
    <div className="px-4 md:px-6 pt-3 pb-5 md:pb-6 bg-paytar-bg flex-shrink-0">
      <div className="max-w-[720px] mx-auto">
        {/* Length toggle — composer üstünde küçük segmented control */}
        <div className="flex items-center gap-2 mb-2 px-1.5">
          <span className="font-mono text-[10px] tracking-wider uppercase text-paytar-muted">
            Yanıt
          </span>
          <div
            role="radiogroup"
            aria-label="Yanıt uzunluğu"
            className="inline-flex border border-paytar-line rounded-full bg-paytar-surface overflow-hidden"
          >
            {LENGTH_OPTIONS.map((opt) => {
              const active = length === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => changeLength(opt.value)}
                  title={opt.hint}
                  className={`px-2.5 py-1 font-mono text-[10px] tracking-wider uppercase transition-colors ${
                    active
                      ? "bg-paytar-accent text-paytar-surface"
                      : "text-paytar-muted hover:text-paytar-ink hover:bg-paytar-surface2"
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

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
            disabled={disabled || !text.trim() || isTooShort}
            aria-label="Gönder"
            type="button"
            title={isTooShort ? `En az ${MIN_CHARS} karakter / ${MIN_WORDS} kelime gerek` : "Gönder"}
            className="w-8 h-8 rounded-full bg-paytar-accent text-paytar-surface flex items-center justify-center flex-shrink-0 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>

        <div className="flex justify-between items-center mt-2 px-1.5 font-mono text-[10px] text-paytar-muted tracking-wider">
          <span className={isTooShort ? "text-amber-700" : ""}>
            {isTooShort
              ? `Biraz daha yaz (en az ${MIN_CHARS} karakter / ${MIN_WORDS} kelime)`
              : hint}
          </span>
          <span className="hidden sm:inline">
            Yanıtlar saha verisi + mevzuat ile doğrulanır
          </span>
        </div>
      </div>
    </div>
  );
}
