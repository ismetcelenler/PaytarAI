"use client";

/**
 * usePaytarChat — minimal state + sendChat() wrapper.
 *
 * Backend non-streaming JSON dondurdugu icin AI SDK useChat KULLANMIYORUZ.
 * Custom state + fetch yeterli.
 */
import { useCallback, useState } from "react";
import { sendChat, PaytarApiError } from "@/lib/paytar";
import type { UIMessage, UserRole } from "@/types/chat";

interface SendOptions {
  animalWeightKg?: number;
}

export interface UsePaytarChatReturn {
  messages: UIMessage[];
  threadId: string | undefined;
  pending: boolean;
  error: string | null;
  send: (text: string, opts?: SendOptions) => Promise<void>;
  reset: () => void;
}

export function usePaytarChat(role: UserRole): UsePaytarChatReturn {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [threadId, setThreadId] = useState<string | undefined>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (text: string, opts?: SendOptions) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;

      const userMsg: UIMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        createdAt: Date.now(),
      };
      setMessages((m) => [...m, userMsg]);
      setPending(true);
      setError(null);

      try {
        const r = await sendChat({
          message: trimmed,
          user_role: role,
          thread_id: threadId,
          animal_weight_kg: opts?.animalWeightKg,
          input_source: "text",
        });
        setThreadId(r.thread_id);
        setMessages((m) => [
          ...m,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: r.response,
            sources: r.sources,
            confidence: r.evidence_confidence,
            criticAttempts: r.critic_attempts,
            createdAt: Date.now(),
          },
        ]);
      } catch (err) {
        const msg =
          err instanceof PaytarApiError
            ? `Backend hatası (${err.status})`
            : "Bağlantı hatası. Backend çalışıyor mu?";
        setError(msg);
        // Hatalı kullanıcı mesajını koru, sadece assistant cevabı eklenmedi
      } finally {
        setPending(false);
      }
    },
    [role, threadId, pending]
  );

  const reset = useCallback(() => {
    setMessages([]);
    setThreadId(undefined);
    setError(null);
  }, []);

  return { messages, threadId, pending, error, send, reset };
}
