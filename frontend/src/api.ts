// API client and types mirroring the FastAPI backend (backend/app/schemas.py).
// All requests go through the `/api` prefix, which Vite proxies to the backend
// in development (see vite.config.ts).

// This is the ONLY file that talks to the backend. Components call these typed
// functions and never touch fetch() directly, so all HTTP details live in one
// place. The interfaces below mirror the Pydantic models in backend/app/schemas.py.
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export const RETRIEVAL_MODES = ["hybrid", "bm25", "dense"] as const;
export type RetrievalMode = (typeof RETRIEVAL_MODES)[number];

export interface RetrievedChunk {
  chunk_id: string;
  citation: string;
  law_code: string;
  title: string;
  hierarchy: string[];
  source_url: string;
  score: number;
  method: string;
  text: string;
}

export interface RetrieveResponse {
  query: string;
  mode: string;
  rerank: boolean;
  law_code: string | null;
  count: number;
  results: RetrievedChunk[];
}

export interface AnswerCitation {
  chunk_id: string;
  citation: string;
  title: string;
  source_url: string;
}

export interface AnswerResponse {
  query: string;
  answer: string;
  citations: AnswerCitation[];
  sources: RetrievedChunk[];
  mode: string;
  rerank: boolean;
  law_code: string | null;
}

export interface IndexStats {
  collection: string;
  collection_ready: boolean;
  indexed_chunks: number;
  qdrant_points: number;
  embedding_model: string;
}

export interface HealthResponse {
  status: string;
  domain: string;
  environment: string;
  qdrant_collection: string;
}

export interface SearchParams {
  query: string;
  mode: RetrievalMode;
  topK: number;
  rerank: boolean;
  lawCode?: string;
}

// Custom error that remembers the HTTP status, so App.tsx can show tailored hints
// (e.g. 503 = index not built / model not configured) instead of a generic message.
/** Error carrying the HTTP status so the UI can react to 503/502 specifically. */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Turn a FastAPI error body into a readable string. */
function formatDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.join(".") : "";
          return loc ? `${loc}: ${String(item.msg)}` : String(item.msg);
        }
        return JSON.stringify(item);
      })
      .filter(Boolean);
    return messages.length ? messages.join("; ") : null;
  }
  return null;
}

// The shared fetch wrapper every call below uses. It does three
// jobs: prefix the path with /api, parse the JSON body, and on a
// non-2xx response throw an ApiError carrying the server's detail
// message. A network failure becomes ApiError(..., status 0).
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(
      "Cannot reach the backend. Is it running on the proxied port?",
      0,
    );
  }

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? formatDetail((payload as { detail: unknown }).detail)
        : typeof payload === "string"
          ? payload
          : null;
    throw new ApiError(detail ?? `Request failed (${response.status})`, response.status);
  }

  return payload as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getIndexStats(): Promise<IndexStats> {
  return request<IndexStats>("/index/stats");
}

// GET /retrieve — options go in the query string.
// Mirrors the /retrieve route in main.py.
export function retrieve(params: SearchParams): Promise<RetrieveResponse> {
  const query = new URLSearchParams({
    q: params.query,
    mode: params.mode,
    top_k: String(params.topK),
    rerank: String(params.rerank),
  });
  if (params.lawCode) {
    query.set("law_code", params.lawCode);
  }
  return request<RetrieveResponse>(`/retrieve?${query.toString()}`);
}

// POST /answer — options go in a JSON body (lawCode
// becomes null when blank), matching AnswerRequest.
export function answer(params: SearchParams): Promise<AnswerResponse> {
  return request<AnswerResponse>("/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: params.query,
      mode: params.mode,
      top_k: params.topK,
      rerank: params.rerank,
      law_code: params.lawCode ?? null,
    }),
  });
}
