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
  audit_log?: AuditEntry[];
  /** debug=true istegi ile gelen detayli pipeline trace */
  debug_trace?: TraceEntry[];
  grounding_action?: string | null;
  retrieval_similarity_score?: number;
  rerank_top_score?: number;
}

export interface AuditEntry {
  timestamp?: string;
  action: string;
  reason?: string | string[];
  source_ids?: string[];
  model_used?: string;
  evidence_confidence?: string;
}

/**
 * Detayli debug trace — her pipeline node'unun input/output dump'i.
 * Backend debug_trace.py'den geliyor.
 */
export interface TraceEntry {
  node: "scope_check" | "retriever" | "generator" | "sentence_grounding" | "critic";
  ts: number;
  latency_ms?: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

export interface HallucinationSpan {
  text: string;
  confidence: number;
  relative_start: number;
  relative_end: number;
}

export interface GroundedSentence {
  text: string;
  type: "specific" | "generic";
  chunk: number | null;
  supported: boolean;
  /** LettuceDetect v3: tum cumledeki halluc char orani */
  hallucination_ratio?: number;
  /** LettuceDetect v3: bu cumledeki spesifik halluc span'lar */
  hallucination_spans?: HallucinationSpan[];
  /** Faz A legacy — atomic claim decomposition LLM-based */
  atomic_claims?: Array<{ claim: string; chunk: number | null; supported: boolean }>;
}

export interface ChunkSnapshot {
  title: string;
  score?: number;
  dense_score?: number;
  rerank_logit?: number;
  rerank_sigmoid?: number;
  text_preview?: string;
  text_full?: string;
  text_len?: number;
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
