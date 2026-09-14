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
