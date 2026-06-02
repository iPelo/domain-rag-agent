import { useEffect, useState } from "react";
import {
  ApiError,
  answer as answerApi,
  getHealth,
  getIndexStats,
  retrieve as retrieveApi,
  type AnswerResponse,
  type HealthResponse,
  type IndexStats,
  type RetrieveResponse,
} from "./api.ts";
import { Controls, type SearchForm } from "./components/Controls.tsx";
import { ChunkCard } from "./components/ChunkCard.tsx";
import { AnswerPanel } from "./components/AnswerPanel.tsx";
import { StatusBar } from "./components/StatusBar.tsx";

type Result =
  | { kind: "retrieve"; data: RetrieveResponse }
  | { kind: "answer"; data: AnswerResponse };

const INITIAL_FORM: SearchForm = {
  query: "",
  mode: "hybrid",
  topK: 5,
  rerank: false,
  lawCode: "",
  action: "retrieve",
};

export function App() {
  const [form, setForm] = useState<SearchForm>(INITIAL_FORM);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([getHealth(), getIndexStats()]).then(([healthResult, statsResult]) => {
      if (!active) return;
      if (healthResult.status === "fulfilled") {
        setHealth(healthResult.value);
        setStatusError(null);
      } else {
        setStatusError(
          healthResult.reason instanceof Error
            ? healthResult.reason.message
            : "Backend unreachable",
        );
      }
      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const handleChange = (patch: Partial<SearchForm>) => {
    setForm((current) => ({ ...current, ...patch }));
  };

  const handleSubmit = async () => {
    const params = {
      query: form.query.trim(),
      mode: form.mode,
      topK: form.topK,
      rerank: form.rerank,
      lawCode: form.lawCode.trim() || undefined,
    };

    setLoading(true);
    setError(null);
    setHint(null);

    try {
      if (form.action === "answer") {
        const data = await answerApi(params);
        setResult({ kind: "answer", data });
      } else {
        const data = await retrieveApi(params);
        setResult({ kind: "retrieve", data });
      }
    } catch (caught) {
      setResult(null);
      const message = caught instanceof Error ? caught.message : "Unexpected error";
      setError(message);
      if (caught instanceof ApiError && form.action === "answer" && caught.status === 503) {
        setHint("Answer generation is not configured. Set MODEL_* in .env, or use /retrieve.");
      } else if (caught instanceof ApiError && caught.status === 503) {
        setHint("The retrieval index may not be built yet. Run `make index` in the backend.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__title">
          <h1>GermanLawRAG</h1>
          <span className="app__subtitle">Retrieval &amp; answer console</span>
        </div>
        <StatusBar health={health} stats={stats} error={statusError} />
      </header>

      <main className="app__main">
        <Controls form={form} loading={loading} onChange={handleChange} onSubmit={handleSubmit} />

        <section className="results">
          {loading && <LoadingState />}

          {!loading && error && (
            <div className="state state--error" role="alert">
              <strong>Request failed</strong>
              <p>{error}</p>
              {hint && <p className="state__hint">{hint}</p>}
            </div>
          )}

          {!loading && !error && !result && <IdleState />}

          {!loading && !error && result?.kind === "retrieve" && (
            <RetrieveResults data={result.data} />
          )}

          {!loading && !error && result?.kind === "answer" && (
            <AnswerResults data={result.data} />
          )}
        </section>
      </main>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="state state--loading">
      <span className="spinner" aria-hidden="true" />
      <span>Querying the corpus…</span>
    </div>
  );
}

function IdleState() {
  return (
    <div className="state state--idle">
      <p>Run a query to retrieve cited passages from the German law corpus.</p>
    </div>
  );
}

function RetrieveResults({ data }: { data: RetrieveResponse }) {
  if (data.count === 0) {
    return (
      <div className="state state--empty">
        <p>
          No passages matched <q>{data.query}</q>
          {data.law_code ? ` in ${data.law_code}` : ""}.
        </p>
      </div>
    );
  }

  return (
    <div className="results__list">
      <div className="results__summary">
        {data.count} result{data.count === 1 ? "" : "s"} · mode {data.mode}
        {data.rerank ? " · reranked" : ""}
        {data.law_code ? ` · ${data.law_code}` : ""}
      </div>
      {data.results.map((chunk, index) => (
        <ChunkCard key={chunk.chunk_id} chunk={chunk} rank={index + 1} />
      ))}
    </div>
  );
}

function AnswerResults({ data }: { data: AnswerResponse }) {
  return (
    <div className="results__list">
      <AnswerPanel answer={data} />
      {data.sources.length > 0 && (
        <>
          <div className="results__summary">Sources ({data.sources.length})</div>
          {data.sources.map((chunk, index) => (
            <ChunkCard key={chunk.chunk_id} chunk={chunk} rank={index + 1} />
          ))}
        </>
      )}
    </div>
  );
}
