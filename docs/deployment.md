# Deployment

Ember-AI runs as a Docker Compose stack on Docker01 (`root@172.20.142.7`), alongside the
existing n8n and Portainer stacks. Nothing is deployed to `jons-mac-mini` — oMLX and Hermes
there are untouched (see [`docs/prox01.md`](prox01.md) and [`docs/mac-mini.md`](mac-mini.md)).

## Deploy

```bash
ssh vaxel-docker
git clone https://github.com/vaxel-xyz/Ember-AI /opt/stacks/ember
cd /opt/stacks/ember
cp .env.example .env
# edit .env: OMLX_API_KEY, OPENROUTER_API_KEY, LITELLM_MASTER_KEY, LITELLM_DB_PASSWORD,
# EMBER_API_KEY, QDRANT_API_KEY (keep this set even if the qdrant profile is unused —
# compose interpolates the whole file, so a CHANGE_ME value here fails ember doctor)
bin/ember up
bin/ember doctor
```

`bin/ember up` runs `docker compose up -d --build` against `/opt/stacks/ember` using `.env`.
`bin/ember doctor` then checks required env vars are set, that the compose config renders,
that Qdrant (if running) has a real API key, that oMLX is reachable and its `/health` parses,
that LiteLLM readiness responds, that ember-api is healthy, and runs one real `ember-auto`
completion and one `ember-embed` request. It exits non-zero with a plain reason on any
failure.

## Validation

Run these once the stack is up and `bin/ember doctor` is green, using either the LAN URL
(`http://172.20.142.7:4000`) or the public one (`https://llm.vaxel.xyz/v1`) as `$LLM`.

**Chat completion (`ember-auto`):**

```bash
LLM=http://172.20.142.7:4000
curl -s "$LLM/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"ember-auto","messages":[{"role":"user","content":"Reply with the single word: pong"}],"max_tokens":8}'
```

**Embeddings (`ember-embed`):**

```bash
curl -s "$LLM/v1/embeddings" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"ember-embed","input":"ember doctor"}'
```

**Speech-to-text (`ember-stt`), with a WAV file:**

```bash
curl -s -F file=@sample.wav -F model=ember-stt \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  "$LLM/v1/audio/transcriptions"
```

**Text-to-speech (`ember-tts`):**

```bash
curl -s "$LLM/v1/audio/speech" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"ember-tts","input":"Ember is online.","voice":"af_heart"}' \
  --output reply.wav
```

Each virtual key used by a real consumer should be minted with `bin/ember keys create
<client>` rather than the master key — see [`docs/litellm.md`](litellm.md).

## Mini-off drill

Stop oMLX on `jons-mac-mini` (or unplug it) and re-run `bin/ember doctor` / the dashboard
Overview page:

- LiteLLM, ember-api and the dashboard stay up and healthy.
- The `omlx` service tile shows `unreachable`.
- `ember-auto`, `ember-embed`, `ember-stt`, `ember-tts` requests return a LiteLLM 5xx with a
  clear backend error.
- `ember-think` (OpenRouter) continues to work.

This is the expected behaviour from [`docs/architecture.md`](architecture.md#failure-behaviour), not a bug.

## Rollback

```bash
bin/ember down
```

`bin/ember down` runs `docker compose down` for the Ember stack only. It does not touch n8n,
Portainer, Home Assistant, oMLX or Hermes — nothing else on Docker01 or the mini is affected.

## Validation receipt 2026-09-14

Task 12 (Phase 1 foundation) live deployment to Docker01, validated against oMLX on
`jons-mac-mini`. n8n and Portainer stacks were not touched.

| Field | Result |
|---|---|
| Date | 2026-09-14 |
| Branch / sha | `feature/ember-lean-rebuild` @ `5225d722bcdc5ec3a1d1a3528b2b7fa464ad846a` (started from `ba1c43bf823d80e811afb9cadd412f18f7e4f636`; one fix commit applied during validation, see below) |
| Docker01 RAM | 7855 MiB total, ~1978 MiB used, ~5877 MiB available after stack up — well within budget alongside the existing n8n (~900 MiB) and Portainer (~37 MiB) stacks |
| Containers | `ember-api` Up (healthy), `ember-dashboard` Up (healthy), `ember-litellm` Up (healthy), `ember-litellm-postgres` Up (healthy) — memory: litellm 428.5 MiB / 1.465 GiB, dashboard 4.9 MiB / 64 MiB, postgres 28.5 MiB / 7.67 GiB, ember-api 38.5 MiB / 256 MiB |
| `bin/ember doctor` | All checks passed after one config fix (below). Also saw one transient `ember-auto completion failed` on a doctor run immediately after a stack restart — root cause was oMLX having unloaded the chat model (0 resident models) so the cold-load exceeded doctor's request timeout; a direct request with a longer timeout succeeded (`model_load_duration: 5.15s`), and the next `bin/ember doctor` run passed cleanly. Not a code defect. |
| Fix applied during validation | LiteLLM's OpenAI-compatible embeddings client sent an `encoding_format` value oMLX's strict backend rejected with HTTP 422 (`body -> encoding_format: Input should be 'float' or 'base64'`), failing `ember-embed`. Fixed by pinning `encoding_format: "float"` in `ember-embed`'s `litellm_params` in `config/litellm/ember.yaml.tmpl` (commit `5225d722b`). Confirmed fixed via direct curl and `bin/ember doctor`. |
| Chat (`ember-auto` via LiteLLM) | Pass — 200, completion returned |
| Embed (`ember-embed` via LiteLLM) | Pass — 200, vector length 1024 |
| STT (`ember-stt` via LiteLLM) | Pass — 200, transcribed a TTS-generated WAV back to "Ember is online." |
| TTS (`ember-tts` via LiteLLM) | Pass — 200, 88,844-byte valid RIFF/WAVE PCM 16-bit mono 24 kHz file (> 20 KB threshold) |
| Rerank, direct oMLX (`/v1/rerank`, `bge-reranker-v2-m3`) | Pass — 200, correct top result ("Bins go out tonight.", relevance_score 0.408) |
| Rerank via LiteLLM (`ember-rerank`, `jina_ai/${OMLX_RERANK_MODEL}` provider prefix) | Pass on first attempt — 200, identical relevance_score to the direct oMLX call. No `cohere/` fallback needed. See ADR 0006. |
| `ember-think` (OpenRouter) | Skipped: no OpenRouter key available for this validation pass (`OPENROUTER_API_KEY` left as `CHANGE_ME`; LiteLLM started fine since the key is only read per-request) |
| Dashboard | `http://172.20.142.7:3001/` title "Ember AI"; `/api/services` returns structured JSON for all 6 tracked services |
| Mini-off drill | `omlx stop` issued 18:01:30 UTC. By 18:02:14 UTC (44s later) `/api/services` showed `omlx: unreachable`, `litellm: degraded` (9/9 deployments unhealthy), dashboard and ember-api still serving HTTP 200 throughout. `omlx start` issued 18:02:20 UTC; oMLX `/health` returned 200 by 18:02:30 UTC (~10s); dashboard's poll reflected `omlx: healthy` by 18:03:17 UTC (~57s after start, gated by `EMBER_POLL_INTERVAL_S=15`). `litellm` returned to its pre-drill baseline `degraded` state (6/9 unhealthy — the same set as before the drill, caused by LiteLLM's generic health probe not suiting embed/vision/audio deployment types, not an actual functional problem — chat/embed/stt/tts all passed functional tests independently) after one real chat request. `omlx stop`/`start` both reported managing the server directly; no deviation to `omlx restart` was needed. |

Secrets: `OMLX_API_KEY` was piped mini→Docker01 without appearing in any transcript, log, or file under version control. `LITELLM_MASTER_KEY`, `EMBER_API_KEY`, `LITELLM_DB_PASSWORD`, `QDRANT_API_KEY` were generated on Docker01 with `openssl rand -hex`. `OPENROUTER_API_KEY` remains `CHANGE_ME` on Docker01 pending Jon supplying it. No secret value appears in this document, in git history, or in this task's report.
