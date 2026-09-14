# LiteLLM

LiteLLM (`ghcr.io/berriai/litellm:v1.81.3-stable`) is the OpenAI-compatible gateway that every
Ember consumer talks to. It owns virtual keys, spend logs and (Phase 3) observability
callbacks. It is backed by its own Postgres (`litellm-postgres`).

## Template / render flow

There is a single config source, `config/litellm/ember.yaml.tmpl`, with `${VAR}` placeholders.
At container start, the entrypoint runs:

```bash
python3 /app/render-config.py /app/ember.yaml.tmpl /tmp/config.yaml
exec litellm --config /tmp/config.yaml --port 4000
```

`config/litellm/render-config.py` substitutes every `${VAR}` from the process environment
using `string.Template`, and fails loudly (`KeyError` naming the missing variable) if
anything required is unset. There are no ODS mode files, no switchboard, no model-router —
one template, rendered once per container start.

## Alias table

| Alias | `litellm_params.model` | Backing env var |
|---|---|---|
| `ember-auto` | `openai/${OMLX_CHAT_MODEL}` | `OMLX_CHAT_MODEL` |
| `ember-local` | `openai/${OMLX_CHAT_MODEL}` | `OMLX_CHAT_MODEL` (pinned local model) |
| `ember-fast` | `openai/${OMLX_FAST_MODEL}` | `OMLX_FAST_MODEL` |
| `ember-code` | `openai/${OMLX_CODE_MODEL}` | `OMLX_CODE_MODEL` |
| `ember-vision` | `openai/${OMLX_VISION_MODEL}` | `OMLX_VISION_MODEL` |
| `ember-embed` | `openai/${OMLX_EMBED_MODEL}` | `OMLX_EMBED_MODEL` |
| `ember-rerank` | `jina_ai/${OMLX_RERANK_MODEL}` | `OMLX_RERANK_MODEL` |
| `ember-stt` | `openai/${OMLX_STT_MODEL}` | `OMLX_STT_MODEL` |
| `ember-tts` | `openai/${OMLX_TTS_MODEL}` | `OMLX_TTS_MODEL` |
| `ember-think` | `openrouter/${OPENROUTER_THINK_MODEL}` | `OPENROUTER_THINK_MODEL` |

All oMLX-backed aliases share `api_base: ${OMLX_BASE_URL}/v1` and
`api_key: os.environ/OMLX_API_KEY`. `ember-rerank` is configured and routes through LiteLLM
using the `jina_ai/` provider prefix — oMLX's `/v1/rerank` is Cohere/Jina-shaped, so no
`cohere/` fallback and no ember-api proxy were needed; see
[ADR 0006](adr/0006-rerank-routing.md).

The non-chat aliases (`ember-embed`, `ember-rerank`, `ember-stt`, `ember-tts`) carry
`model_info.mode` — `embedding`, `rerank`, `audio_transcription`, `audio_speech`
respectively, the last with `health_check_voice: af_heart`. Without it LiteLLM's deep health
check (`GET /health`) falls back to a chat completion against an embedding or audio model.
That check is never run from ember-api's poll loop; see
[`docs/troubleshooting.md`](troubleshooting.md#deep-gateway-check-on-demand).

## Virtual keys

Never distribute the LiteLLM master key. Each real consumer gets its own key, with usage
attributed to it in `/spend/logs` and `/key/info`:

```bash
bin/ember keys create hermes
bin/ember keys create hermes --budget 20
```

This calls `POST /key/generate` with `key_alias` and `metadata.client` set to the client
name, and an optional `max_budget` in USD. The dashboard's Clients/Usage view is entirely
derived from this generic telemetry — no bespoke per-consumer code is needed to make a new
client show up.

## `LLM_INTERNAL_URL` vs `LLM_PUBLIC_URL`

| Variable | Value | Used by |
|---|---|---|
| `LLM_INTERNAL_URL` | `http://172.20.142.7:4000/v1` | LAN consumers (e.g. Hermes) — no Cloudflare hairpin |
| `LLM_PUBLIC_URL` | `https://llm.vaxel.xyz/v1` | remote/public consumers, surfaced by `/api/providers` |

Both are surfaced by ember-api and the dashboard's Providers page; nothing forces a consumer
onto one or the other.

## Message logging

`litellm_settings.turn_off_message_logging` is set from `LITELLM_TURN_OFF_MESSAGE_LOGGING`
(default `true` in `.env.example`) — prompts and responses are **not** stored in spend logs by
default, only metadata (model, tokens, latency, client). Setting it to `false` is an explicit
opt-in. Phase 3's planned Langfuse `success_callback` is designed to respect the same
`turn_off_message_logging` behaviour via a planned `EMBER_LOG_PROMPTS` toggle — that
variable is not present in `.env.example` yet — see
[`docs/observability.md`](observability.md).
