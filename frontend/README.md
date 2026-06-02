# Frontend

A small developer console for the GermanLawRAG backend. It submits queries to the
retrieval and answer endpoints and renders the cited source passages.

Stack: Vite + React + TypeScript. No UI framework; styling is plain CSS and the
data layer uses the native `fetch` API, so the dependency footprint stays small.

## Features

- Query input with retrieval **mode** (`hybrid`, `bm25`, `dense`), **top_k**,
  **rerank** toggle, and an optional **law_code** filter.
- Defaults to `GET /retrieve`; switch the action to `POST /answer` when the
  backend has a model configured.
- Result cards show citation, law code, score, retrieval method, title,
  hierarchy, source link, and expandable passage text.
- Loading, error, empty, and idle states, plus a status bar showing backend
  health and index stats.

## Prerequisites

- Node.js 18+ and npm.
- The backend running on `http://127.0.0.1:8000` (see the repository root README).

## Run

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`).

## How it reaches the backend

The browser calls the app under the `/api` prefix. In development, Vite proxies
those requests to the FastAPI backend, so no CORS configuration is needed on the
backend. The proxy is defined in `vite.config.ts`.

To point at a backend on a different host or port, set `VITE_BACKEND_URL` before
starting the dev server:

```bash
VITE_BACKEND_URL=http://127.0.0.1:9000 npm run dev
```

If you serve the production build behind your own reverse proxy, route `/api` to
the backend there, or set `VITE_API_BASE` at build time to an absolute backend
URL.

## Scripts

| Command             | Description                                  |
| ------------------- | -------------------------------------------- |
| `npm run dev`       | Start the dev server with backend proxy.     |
| `npm run build`     | Type-check (`tsc --noEmit`) and bundle.      |
| `npm run preview`   | Serve the production build locally.          |
| `npm run typecheck` | Type-check without emitting output.          |

## Notes

- `/answer` returns `503` until model credentials (`MODEL_*` in the backend
  `.env`) are configured. The UI surfaces this and you can keep using
  `/retrieve`.
- `law_code` is an exact match (for example `GG`, `BGB`, `StGB`).
