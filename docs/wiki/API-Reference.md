# API Reference

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`
while the backend is running.

## `GET /health`

Returns basic service and environment information. It does not load the index or
an embedding model.

## `GET /index/stats`

Reports the local chunk count, Qdrant point count, collection name, embedding
model, and whether the vector collection exists.

## `GET /retrieve`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `q` | string | required | At least two characters |
| `mode` | string | `hybrid` | `bm25`, `dense`, or `hybrid` |
| `top_k` | integer | `5` | Between 1 and 50 |
| `rerank` | boolean | `false` | Enables cross-encoder reranking |
| `law_code` | string | empty | Exact law filter, for example `GG` |

Example:

```bash
curl --get http://localhost:8000/retrieve \
  --data-urlencode "q=Wo ist die Meinungsfreiheit geregelt?" \
  --data-urlencode "mode=hybrid" \
  --data-urlencode "top_k=5"
```

## `POST /answer`

Retrieves sources and sends them to the configured chat model. The response
contains the answer, validated citations, and the source chunks.

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"Wo ist die Meinungsfreiheit geregelt?","top_k":5}'
```

The endpoint returns `503` when the model is not configured and `502` when the
provider call fails or the generated citations do not pass validation.
