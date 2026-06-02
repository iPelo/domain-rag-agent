import type { HealthResponse, IndexStats } from "../api.ts";

interface StatusBarProps {
  health: HealthResponse | null;
  stats: IndexStats | null;
  error: string | null;
}

export function StatusBar({ health, stats, error }: StatusBarProps) {
  let dotClass = "status-dot status-dot--unknown";
  let label = "Connecting to backend…";

  if (error) {
    dotClass = "status-dot status-dot--down";
    label = "Backend unreachable";
  } else if (health) {
    const ready = stats?.collection_ready ?? false;
    dotClass = ready ? "status-dot status-dot--up" : "status-dot status-dot--warn";
    label = ready ? "Backend ready" : "Backend up · index not built";
  }

  return (
    <div className="status-bar" role="status">
      <span className={dotClass} aria-hidden="true" />
      <span className="status-bar__label">{label}</span>
      {health && <span className="status-bar__item">env: {health.environment}</span>}
      {stats && (
        <>
          <span className="status-bar__item">collection: {stats.collection}</span>
          <span className="status-bar__item">
            chunks: {stats.indexed_chunks.toLocaleString()}
          </span>
          <span className="status-bar__item">points: {stats.qdrant_points.toLocaleString()}</span>
          <span className="status-bar__item" title={stats.embedding_model}>
            embed: {stats.embedding_model}
          </span>
        </>
      )}
    </div>
  );
}
