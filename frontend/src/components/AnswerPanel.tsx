import type { AnswerResponse } from "../api.ts";

interface AnswerPanelProps {
  answer: AnswerResponse;
}

export function AnswerPanel({ answer }: AnswerPanelProps) {
  return (
    <section className={`answer-panel${answer.no_answer ? " answer-panel--no-answer" : ""}`}>
      <header className="answer-panel__header">
        <h2>Answer</h2>
        <div className="answer-panel__meta">
          {answer.no_answer && <span className="badge badge--no-answer">no answer</span>}
          <span className="badge">{answer.mode}</span>
          {answer.rerank && <span className="badge">reranked</span>}
          {answer.law_code && <span className="badge badge--law">{answer.law_code}</span>}
        </div>
      </header>

      <p className="answer-panel__text">{answer.answer}</p>

      {answer.no_answer && (
        <p className="answer-panel__note">
          The retrieved passages do not support an answer. Try rephrasing the question or
          removing the law filter.
        </p>
      )}

      {answer.citations.length > 0 && (
        <div className="answer-panel__citations">
          <span className="answer-panel__citations-label">Citations</span>
          <ul>
            {answer.citations.map((citation) => (
              <li key={citation.chunk_id}>
                <a href={citation.source_url} target="_blank" rel="noreferrer noopener">
                  {citation.citation}
                </a>
                <span className="answer-panel__citation-title">{citation.title}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
