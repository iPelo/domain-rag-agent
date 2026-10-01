import type { KeyboardEvent } from "react";
import { RETRIEVAL_MODES, type RetrievalMode } from "../api.ts";

export type Action = "retrieve" | "answer";

export interface SearchForm {
  query: string;
  mode: RetrievalMode;
  topK: number;
  rerank: boolean;
  lawCode: string;
  action: Action;
}

interface ControlsProps {
  form: SearchForm;
  loading: boolean;
  onChange: (patch: Partial<SearchForm>) => void;
  onSubmit: () => void;
}

export function Controls({ form, loading, onChange, onSubmit }: ControlsProps) {
  const maxTopK = form.action === "answer" ? 20 : 50;
  const canSubmit = form.query.trim().length >= 2 && !loading;

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && canSubmit) {
      event.preventDefault();
      onSubmit();
    }
  };

  return (
    <form
      className="controls"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSubmit) onSubmit();
      }}
    >
      <div className="controls__query">
        <label htmlFor="query">Query</label>
        <textarea
          id="query"
          rows={2}
          placeholder="z. B. Wo ist die Meinungsfreiheit geregelt?"
          value={form.query}
          onChange={(event) => onChange({ query: event.target.value })}
          onKeyDown={handleKeyDown}
        />
      </div>

      <div className="controls__row">
        <div className="control">
          <label htmlFor="action">Action</label>
          <select
            id="action"
            value={form.action}
            onChange={(event) => onChange({ action: event.target.value as Action })}
          >
            <option value="retrieve">/retrieve</option>
            <option value="answer">/answer</option>
          </select>
        </div>

        <div className="control">
          <label htmlFor="mode">Mode</label>
          <select
            id="mode"
            value={form.mode}
            onChange={(event) => onChange({ mode: event.target.value as RetrievalMode })}
          >
            {RETRIEVAL_MODES.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
        </div>

        <div className="control control--narrow">
          <label htmlFor="top-k">top_k</label>
          <input
            id="top-k"
            type="number"
            min={1}
            max={maxTopK}
            value={form.topK}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isNaN(next)) return;
              onChange({ topK: Math.min(Math.max(next, 1), maxTopK) });
            }}
          />
        </div>

        <div className="control control--narrow">
          <label htmlFor="law-code">law_code</label>
          <input
            id="law-code"
            type="text"
            placeholder="GG, BGB…"
            value={form.lawCode}
            onChange={(event) => onChange({ lawCode: event.target.value })}
          />
        </div>

        <div className="control control--checkbox">
          <label htmlFor="rerank">
            <input
              id="rerank"
              type="checkbox"
              checked={form.rerank}
              onChange={(event) => onChange({ rerank: event.target.checked })}
            />
            rerank
          </label>
        </div>

        <button type="submit" className="submit-button" disabled={!canSubmit}>
          {loading ? "Running…" : "Run"}
        </button>
      </div>

      <p className="controls__hint">
        Defaults to <code>/retrieve</code>. Press <kbd>⌘</kbd>/<kbd>Ctrl</kbd> +{" "}
        <kbd>Enter</kbd> to run. <code>law_code</code> is an exact match and optional.
      </p>
    </form>
  );
}
