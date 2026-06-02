import { useState } from "react";
import type { RetrievedChunk } from "../api.ts";

interface ChunkCardProps {
  chunk: RetrievedChunk;
  rank: number;
}

const COLLAPSE_LENGTH = 360;

export function ChunkCard({ chunk, rank }: ChunkCardProps) {
  const isLong = chunk.text.length > COLLAPSE_LENGTH;
  const [expanded, setExpanded] = useState(false);
  const shownText = expanded || !isLong ? chunk.text : `${chunk.text.slice(0, COLLAPSE_LENGTH)}…`;

  return (
    <article className="chunk-card">
      <header className="chunk-card__header">
        <span className="chunk-card__rank">#{rank}</span>
        <span className="chunk-card__citation">{chunk.citation}</span>
        <span className="badge badge--law">{chunk.law_code}</span>
        <span className="badge badge--method">{chunk.method}</span>
        <span className="chunk-card__score" title="Retrieval score">
          {chunk.score.toFixed(4)}
        </span>
      </header>

      {chunk.title && <p className="chunk-card__title">{chunk.title}</p>}

      {chunk.hierarchy.length > 0 && (
        <p className="chunk-card__hierarchy">{chunk.hierarchy.join(" › ")}</p>
      )}

      <p className="chunk-card__text">{shownText}</p>

      <footer className="chunk-card__footer">
        {isLong && (
          <button
            type="button"
            className="link-button"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
        {chunk.source_url && (
          <a
            className="link-button"
            href={chunk.source_url}
            target="_blank"
            rel="noreferrer noopener"
          >
            Source ↗
          </a>
        )}
        <code className="chunk-card__id" title="chunk_id">
          {chunk.chunk_id}
        </code>
      </footer>
    </article>
  );
}
