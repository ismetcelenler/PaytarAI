/**
 * PaytarAI Backend Client
 *
 * .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
 */
import type { ChatRequest, ChatResponse } from "@/types/chat";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class PaytarApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "PaytarApiError";
  }
}

export async function sendChat(body: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      input_source: "text",
      ...body,
    }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new PaytarApiError(res.status, `PaytarAI ${res.status}: ${text}`);
  }
  return res.json();
}

/** Debug paneli icin: tum pipeline trace + tam chunk metinleri ile cagri. */
export async function sendChatDebug(body: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      input_source: "text",
      ...body,
      debug: true,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new PaytarApiError(res.status, `PaytarAI ${res.status}: ${text}`);
  }
  return res.json();
}

// ────────────────────────────────────────────────────────────────
// SSE STREAMING — /chat/stream
// Backend her node bitince "step" event'i, sonunda "result" yayar.
// Native EventSource sadece GET destekledigi icin fetch + ReadableStream.
// ────────────────────────────────────────────────────────────────

export type StreamStartEvent = {
  type: "start";
  data: { thread_id: string; request_id: string; ts: number };
};

export type StreamStepEvent = {
  type: "step";
  data: { node: string; ms_since_start: number; step_index: number };
};

export type StreamResultEvent = {
  type: "result";
  data: ChatResponse & { _total_ms?: number; _nodes_visited?: string[] };
};

export type StreamErrorEvent = {
  type: "error";
  data: { detail: string };
};

export type StreamEvent =
  | StreamStartEvent
  | StreamStepEvent
  | StreamResultEvent
  | StreamErrorEvent;

/** SSE stream cagirisi. onEvent her event icin senkron tetiklenir.
 *  AbortSignal verilirse client tarafindan iptal edilebilir. */
export async function sendChatStream(
  body: ChatRequest,
  onEvent: (ev: StreamEvent) => void,
  opts?: { debug?: boolean; signal?: AbortSignal },
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ input_source: "text", debug: !!opts?.debug, ...body }),
    signal: opts?.signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new PaytarApiError(res.status, `PaytarAI ${res.status}: ${text}`);
  }
  if (!res.body) {
    throw new PaytarApiError(0, "Yanıt body'si boş — stream başlatılamadı.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE event delimiter: \n\n. Her event "event: name\ndata: ...\n\n"
      let sepIdx;
      while ((sepIdx = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, sepIdx);
        buffer = buffer.slice(sepIdx + 2);
        const parsed = parseSSEBlock(raw);
        if (parsed) onEvent(parsed);
      }
    }
  } finally {
    try { reader.releaseLock(); } catch { /* noop */ }
  }
}

function parseSSEBlock(raw: string): StreamEvent | null {
  let eventName = "message";
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    // diger SSE field'larini gormezden geliyoruz (id:, retry:)
  }
  if (dataLines.length === 0) return null;
  let data: unknown;
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    return null;
  }
  switch (eventName) {
    case "start":
    case "step":
    case "result":
    case "error":
      return { type: eventName, data } as StreamEvent;
    default:
      return null;
  }
}

/** Backend root ping — connectivity sanity check */
export async function pingBackend(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

/** Henuz backend'de yok — TODO toast helper */
export function notYetImplemented(featureName: string): void {
  console.warn(`[PaytarAI TODO] ${featureName} backend'e baglanmadi`);
  if (typeof window !== "undefined") {
    // shadcn toast yerine basit alert — sonra sonner/toast'a baglanir
    window.alert(`"${featureName}" ozelligi yakında aktif olacak.`);
  }
}
