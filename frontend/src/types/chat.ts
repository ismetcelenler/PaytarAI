/**
 * PaytarAI Chat Types
 *
 * Backend (backend/app/api/v1/chat.py) ChatRequest/ChatResponse ile birebir uyumlu.
 * Backend dict ile dondugu icin Source field'i da backend gercek formatini takip eder.
 */

export type UserRole = "producer" | "veterinarian";
export type InputSource = "text" | "voice";
export type EvidenceConfidence = "high" | "medium" | "low" | "insufficient";

/** POST /api/v1/chat — request body */
export interface ChatRequest {
  message: string;
  user_role: UserRole;
  thread_id?: string;
  animal_weight_kg?: number;
  input_source?: InputSource;
}

/** Backend gercek source formati (backend/app/api/v1/chat.py:78-84) */
export interface Source {
  title: string;
  score: number;
  snippet: string;
}

/** POST /api/v1/chat — response body */
export interface ChatResponse {
  response: string; // markdown
  thread_id: string;
  evidence_confidence: EvidenceConfidence;
  sources: Source[];
  critic_attempts: number;
  audit_entry_count?: number;
  audit_log?: unknown[];
}

/** UI-side message representation */
export interface UIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  confidence?: EvidenceConfidence;
  criticAttempts?: number;
  createdAt: number;
}
