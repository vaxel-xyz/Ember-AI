# oMLX

oMLX is the Apple-Silicon inference runtime on `jons-mac-mini`, reached by LiteLLM over the
LAN at `OMLX_BASE_URL` (`http://172.20.142.184:8000`) with a bearer key (`OMLX_API_KEY`).
Ember never talks to oMLX directly from a browser or a consumer — everything goes through
LiteLLM (`ember-*` aliases) or, for dashboard health, through ember-api's probe.

## Endpoints used

| Endpoint | Auth | Used for |
|---|---|---|
| `GET /health` | none | health probe (ember-api, `bin/ember doctor`) |
| `GET /v1/models` | bearer | model ids on disk (folder names) |
| `GET /v1/models/status` | bearer | per-model loaded/unloaded + estimated size (ember-api `/api/models`) |
| `POST /v1/chat/completions` | bearer, via LiteLLM | `ember-auto`, `ember-local`, `ember-fast`, `ember-code` |
| `POST /v1/chat/completions` (vision) | bearer, via LiteLLM | `ember-vision` |
| `POST /v1/embeddings` | bearer, via LiteLLM | `ember-embed` |
| `POST /v1/rerank` | bearer, via LiteLLM (not yet routed) | `ember-rerank` — see [ADR 0006](adr/0006-rerank-routing.md) |
| `POST /v1/audio/transcriptions` | bearer, via LiteLLM | `ember-stt` |
| `POST /v1/audio/speech` | bearer, via LiteLLM | `ember-tts` |
| `GET /v1/audio/voices` | bearer | voice listing for TTS (ember-api) |

## `/health` semantics → five states

`/health` returns `status`, `engine_pool.loaded_count`, `engine_pool.current_model_memory`,
`engine_pool.final_ceiling`. `ember-api`'s oMLX probe (`ember-api/ember_api/health.py`) maps
the response to one of the five service states:

| Condition | State |
|---|---|
| connect failure / DNS failure / timeout | `unreachable` |
| HTTP 503, `status: "loading"` | `starting` |
| HTTP ≥ 400 (any other case), or a non-JSON body | `reachable-unhealthy` |
| HTTP 200, `engine_pool.loaded_count == 0` | `degraded` |
| HTTP 200, `engine_pool.loaded_count > 0` | `healthy` |

`degraded` does not mean oMLX is broken — it means no model is currently resident, and the
first request against it will trigger an on-demand load (oMLX's own LRU behaviour).

## Model ids are folder names

oMLX reports the **directory name** under `~/.omlx/models/<org>/<name>`, not the Hugging Face
repo id, as the model id over `/v1/models`. `.env` values such as `OMLX_CHAT_MODEL` must be
the folder name (e.g. `Ornith-1.5-9B-MLX-4bit`), not `ornith-ai/Ornith-1.5-9B-MLX-4bit`. See
[`docs/troubleshooting.md`](troubleshooting.md#model-not-found) for the failure mode when
these are confused.

## Downloading a model

```bash
uvx --from huggingface_hub hf download <repo> --local-dir ~/.omlx/models/<org>/<name>
~/.omlx/bin/omlx restart
```

oMLX only rescans its models directory on restart — a model downloaded while oMLX is running
will not appear in `/v1/models` until `~/.omlx/bin/omlx restart` runs.
