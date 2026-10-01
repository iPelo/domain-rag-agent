# Troubleshooting

## `/retrieve` Returns `503`

The local chunk file or Qdrant index is probably missing.

```bash
make chunks
make up
make index
```

Then check `http://localhost:8000/index/stats`.

## `/answer` Returns `503`

Answer generation requires `MODEL_NAME`, `MODEL_BASE_URL`, and `MODEL_API_KEY`
in `.env`. Retrieval remains available without them.

## Qdrant Is Unavailable

```bash
docker compose ps
docker compose logs qdrant
make up
```

The default URL is `http://localhost:6333`.

## A Model Download Is Slow

The first dense query or reranked query downloads model weights. Use BM25 mode
for a lightweight local check:

```bash
curl --get http://localhost:8000/retrieve \
  --data-urlencode "q=Art 5 GG" \
  --data-urlencode "mode=bm25"
```

## CI Passes Locally but Fails on GitHub

Do not let tests depend on `.env`, local indexes, Qdrant, or downloaded model
weights. API tests should override service dependencies with fakes. Run the
same checks as CI with:

```bash
make verify
```
