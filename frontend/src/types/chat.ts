/**
 * PaytarAI Chat Types
 *
 * Backend (backend/app/api/v1/chat.py) ChatRequest/ChatResponse ile birebir uyumlu.
 */

export type UserRole = "producer" | "veterinarian";
export type InputSource = "text" | "voice";
export type EvidenceConfidence = "high" | "medium" | "low" | "insufficient";
export type ResponseLength = "short" | "medium" | "long";

/** Backend'e gonderilen kisa mesaj history elemani. */
export interface BackendMessage {
  role: "user" | "assistant";
  content: string;
  /** Asistan mesajinin turu — "clarification" ise backend clarification turunu
   *  geri sayabilir (max attempts gate). */
  kind?: "answer" | "clarification" | "fallback";
}

/** POST /api/v1/chat — request body */
export interface ChatRequest {
  message: string;
  user_role: UserRole;
  thread_id?: string;
  animal_weight_kg?: number;
  input_source?: InputSource;
  /** Generator yanit uzunlugu tercihi. Default: medium. */
  response_length?: ResponseLength;
  /** Multi-turn history — clarification yantlari icin backend birlesik baglam
   *  goruyor. Frontend tum thread'i her isteke ekler. */
  messages?: BackendMessage[];
}

/** Backend gercek source formati (backend/app/api/v1/chat.py) */
export interface Source {
  title: string;
  score: number;
  snippet: string;
  /** Orijinal 1-tabanli kaynak numarasi (retrieved_docs index). Kaynak paneli
   *  rerank < 0.50 olanlari gizler ama numara [Kaynak N] etiketleriyle tutarli
   *  kalsin ve tiklayinca dogru chunk acilsin diye tasinir. */
  chunk_id?: number;
  /** Dense cosine skoru (panelde rerank gosteriliyor; bu ek bilgi). */
  dense_score?: number;
}

/** Backend chunks alani — claim_attribution citation modal'inin gosterdigi tam metin. */
export interface ChunkFull {
  title: string;
  language?: string;
  score: number;
  text: string;
}

/** claim_attribution node'unun her cumle icin urettigi karar.
 *
 * Iki asamali atribut atama:
 *   1) Llama-3.3-70B judge: claim/filler siniflandirma + ilk chunk tahmini
 *   2) Hardcode substring/token verify (tanılayabilirlik için saklanır)
 *   3) Claude Opus 4.8 verifier (NIHAI karar — anlamsal entailment +
 *      verbatim pasaj cikarimi)
 */
export interface SentenceCitation {
  idx: number;
  text: string;
  type: "claim" | "filler";
  /** NIHAI chunk_id — verifier asama 2 sonrasi. null ise drop edildi. */
  chunk_id: number | null;
  /** Asama 1 — LLM judge'in ilk tahmini. */
  chunk_id_judge?: number | null;
  /** Asama 1.5 — hardcode substring verify sonucu. */
  chunk_id_hardcode?: number | null;
  /** Hardcode verify reason: confirmed | reassigned | not_found | no_evidence | skipped */
  verify_reason?: string;
  /** Asama 2 — LLM verifier status: supported | not_supported | llm_error |
   *  parse_error | missing_from_llm */
  verifier_status?: string;
  /** NIHAI evidence — verifier'in chunk'tan birebir cikardigi verbatim pasaj.
   *  Frontend bunu chunk metninde aratip highlight eder. null = yok. */
  evidence?: string | null;
  /** Cumle yanitta korunuyor mu? (filler her zaman true, claim sadece chunk_id != null ise.) */
  supported: boolean;
  /** LLM judge cumleyi atladi mi (eksik geldi, "claim+null" olarak dolduruldu). */
  missing_from_llm?: boolean;
}

/** clarification_node'un urettigi strukturli takip sorusu payload'i. */
export interface ClarificationPayload {
  intro: string;
  differentials: string[];
  follow_up_questions: string[];
}

/** Backend response_status alan ozellikle clarification durumunu isaretler. */
export type ResponseStatus =
  | "ok"
  | "clarification_needed"
  | "clarification_exhausted"
  | "insufficient_evidence"
  | "out_of_scope"
  | "fallback"
  | "error"
  | string;

/** POST /api/v1/chat — response body */
export interface ChatResponse {
  response: string; // markdown
  thread_id: string;
  evidence_confidence: EvidenceConfidence;
  sources: Source[];
  /** Tam chunk metinleri — frontend [Kaynak N] tiklaminda modal'da gosterir. */
  chunks: ChunkFull[];
  /** claim_attribution per-sentence kararlari (debug=false durumunda da gelir). */
  sentence_citations: SentenceCitation[];
  /** clarification_node aktifse strukturli payload — frontend ozel UI render eder. */
  clarification?: ClarificationPayload | null;
  /** Workflow son durumu — frontend UI varyantini secmek icin kullanir. */
  response_status?: ResponseStatus | null;
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
  node:
    | "scope_check"
    | "compress"
    | "retriever"
    | "generator"
    | "claim_attribution"
    | "clarification"
    | "confidence"
    | "sentence_grounding"
    | "critic";
  ts: number;
  latency_ms?: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

/** LettuceDetect v3 kalintisi — sentence_grounding node icin (v5'te kullanilmiyor ama trace eski formatla gelirse). */
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
  hallucination_ratio?: number;
  hallucination_spans?: HallucinationSpan[];
  atomic_claims?: Array<{ claim: string; chunk: number | null; supported: boolean }>;
}

export interface ChunkSnapshot {
  title: string;
  language?: string;
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
  /** Asistan mesajinin turu — clarification ise farkli UI varyantı (sari accent
   *  badge, listeler) goster. Backend'e history ile geri gonderilir, max clarification
   *  attempts sayacini backend buradan turetir. */
  kind?: "answer" | "clarification" | "fallback";
  /** clarification mesajinda payload (intro + differentials + follow_up_questions) */
  clarification?: ClarificationPayload | null;
  sources?: Source[];
  chunks?: ChunkFull[];
  sentenceCitations?: SentenceCitation[];
  confidence?: EvidenceConfidence;
  criticAttempts?: number;
  createdAt: number;
}
