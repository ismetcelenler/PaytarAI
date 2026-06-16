"use client";

/**
 * usePaytarChat — multi-turn chat hook
 *
 * Backend SSE stream. Her send() çağrısı:
 *  - User mesajını UI'ya ekler.
 *  - TÜM thread history'yi backend'e gönderir (clarification için birlesik baglam).
 *  - Stream sırasında step event'leri PipelineProgress için biriktirir.
 *  - Result event geldiğinde clarification varsa "kind=clarification" ile bubble ekler.
 *
 * Short message guard: send() en az 12 karakter VE 3 anlamlı kelime gerektirir.
 * Backend zaten 422 ile reddeder; client-side guard ekstra latency tasarrufu.
 */
import { useCallback, useRef, useState } from "react";
import { sendChatStream, PaytarApiError } from "@/lib/paytar";
import type {
  UIMessage,
  UserRole,
  ResponseLength,
  ChatResponse,
  BackendMessage,
} from "@/types/chat";
import type { PipelineStepEvent } from "@/components/paytar/pipeline-progress";

interface SendOptions {
  animalWeightKg?: number;
  responseLength?: ResponseLength;
}

export interface UsePaytarChatReturn {
  messages: UIMessage[];
  threadId: string | undefined;
  pending: boolean;
  error: string | null;
  streamSteps: PipelineStepEvent[];
  streamStartedAt: number | null;
  send: (text: string, opts?: SendOptions) => Promise<void>;
  reset: () => void;
}

// Spam koruma — backend ile ayni esikler. Yararsiz cevaplari pipeline'a sokmaz.
const MIN_CHARS = 12;
const MIN_WORDS = 3;
const _WORD_RE = /[A-Za-zĞÜŞİÖÇğüşıöç0-9]{2,}/g;

function validateMessage(text: string): string | null {
  const stripped = text.trim();
  if (stripped.length < MIN_CHARS) {
    return (
      `Mesaj çok kısa (en az ${MIN_CHARS} karakter). Sorunu biraz daha detaylı yaz; ` +
      "belirtiler, yaş, süre ekle."
    );
  }
  const words = stripped.match(_WORD_RE) ?? [];
  if (words.length < MIN_WORDS) {
    return (
      `Mesaj çok kısa (en az ${MIN_WORDS} kelime). ` +
      "Ne gördün, ne zamandan beri, hangi hayvanlarda — biraz tarif et."
    );
  }
  return null;
}

function uiMessagesToBackend(msgs: UIMessage[]): BackendMessage[] {
  return msgs.map((m) => ({
    role: m.role,
    content: m.content,
    kind: m.kind,
  }));
}

export function usePaytarChat(role: UserRole): UsePaytarChatReturn {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [threadId, setThreadId] = useState<string | undefined>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamSteps, setStreamSteps] = useState<PipelineStepEvent[]>([]);
  const [streamStartedAt, setStreamStartedAt] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (text: string, opts?: SendOptions) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;

      // Client-side guard — backend zaten 422 doner ama UX icin burada da kestir
      const validationError = validateMessage(trimmed);
      if (validationError) {
        setError(validationError);
        return;
      }

      const userMsg: UIMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        createdAt: Date.now(),
      };
      // History snapshot: yeni user msg + eski tum thread
      const historySnapshot: UIMessage[] = [...messages, userMsg];

      setMessages(historySnapshot);
      setPending(true);
      setError(null);
      setStreamSteps([]);
      setStreamStartedAt(Date.now());

      const controller = new AbortController();
      abortRef.current = controller;

      let finalResult: ChatResponse | null = null;
      let receivedThreadId: string | undefined = undefined;

      try {
        await sendChatStream(
          {
            message: trimmed,
            user_role: role,
            thread_id: threadId,
            animal_weight_kg: opts?.animalWeightKg,
            input_source: "text",
            response_length: opts?.responseLength,
            // Multi-turn: tum history'i backend'e ver (clarification icin)
            messages: uiMessagesToBackend(historySnapshot),
          },
          (ev) => {
            switch (ev.type) {
              case "start":
                receivedThreadId = ev.data.thread_id;
                break;
              case "step":
                setStreamSteps((prev) => [...prev, {
                  node: ev.data.node,
                  ms_since_start: ev.data.ms_since_start,
                  step_index: ev.data.step_index,
                }]);
                break;
              case "result":
                finalResult = ev.data;
                break;
              case "error":
                throw new PaytarApiError(500, ev.data.detail);
            }
          },
          { signal: controller.signal },
        );

        if (!finalResult) {
          throw new Error("Stream sona erdi ama final yanıt gelmedi.");
        }

        const r = finalResult as ChatResponse;
        if (receivedThreadId) setThreadId(receivedThreadId);

        // Asistan mesajinin tipini belirle:
        //   clarification_needed → kind=clarification (sari accent UI)
        //   clarification_exhausted / insufficient_evidence / fallback → kind=fallback
        //   ok → kind=answer (normal UI)
        const kind: UIMessage["kind"] =
          r.response_status === "clarification_needed"
            ? "clarification"
            : r.response_status === "clarification_exhausted" ||
              r.response_status === "insufficient_evidence" ||
              r.response_status === "out_of_scope" ||
              r.response_status === "fallback"
            ? "fallback"
            : "answer";

        setMessages((m) => [
          ...m,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: r.response,
            kind,
            clarification: r.clarification ?? null,
            sources: r.sources,
            chunks: r.chunks,
            sentenceCitations: r.sentence_citations,
            confidence: r.evidence_confidence,
            criticAttempts: r.critic_attempts,
            createdAt: Date.now(),
          },
        ]);
      } catch (err) {
        if (controller.signal.aborted) {
          // Kullanici iptal — sessiz
        } else {
          // 422 (short message) backend hatasi pretty error mesaji icerir
          const msg =
            err instanceof PaytarApiError
              ? err.message.replace(/^PaytarAI \d+:\s*/, "")
              : err instanceof Error
              ? err.message
              : "Bağlantı hatası. Backend çalışıyor mu?";
          setError(msg);
          // Hatali user mesajini geri al (UI'da gozukmesin)
          setMessages((m) => m.filter((x) => x.id !== userMsg.id));
        }
      } finally {
        setPending(false);
        setStreamStartedAt(null);
        abortRef.current = null;
      }
    },
    [role, threadId, pending, messages]
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setThreadId(undefined);
    setError(null);
    setStreamSteps([]);
    setStreamStartedAt(null);
  }, []);

  return {
    messages,
    threadId,
    pending,
    error,
    streamSteps,
    streamStartedAt,
    send,
    reset,
  };
}
