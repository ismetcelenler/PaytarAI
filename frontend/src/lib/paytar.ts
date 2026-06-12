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
