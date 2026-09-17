# Ember-AI

Vaxel's shared AI infrastructure layer. Ember-AI provides model routing, local and cloud
inference access, speech-to-text, text-to-speech, model/provider management, observability
and an administrative dashboard. It is consumed over standards-compatible (OpenAI-shaped)
HTTP APIs by independent applications — it does not talk to end users directly.

**Personal project (Vaxel homelab).**

## What Ember-AI is not

Ember-AI is not a chat UI, an agent, a RAG application, an MCP host, a workflow engine or a
home-automation integration. Those responsibilities live elsewhere in the Vaxel stack:

| Role | Owner | Ember's relationship |
|---|---|---|
| Human-facing UI | Open WebUI (`chat.vaxel.xyz`) | external consumer, separate stack; one LiteLLM virtual key ([ADR 0010](docs/adr/0010-frontend-routing-voice.md)) |
| Reasoning, memory, skills, tools, MCP, HA, scheduling, RAG logic | Hermes Agent (on `jons-mac-mini`) | required first-class consumer |
| Interactive software engineering | OpenCode (launched locally by Jon per repo) | optional consumer, never deployed by Ember |
| Model routing, inference access, STT, TTS, provider management, observability, admin | **Ember-AI** | this repo |

MCP is configured in Open WebUI / Hermes — never in ember-api.

ODS (`Osmantic/ODS`) is a donor/reference implementation, not an architecture to preserve — see
[`DOWNSTREAM.md`](DOWNSTREAM.md) for what was kept, what was deleted, and how to cherry-pick from upstream.

## Quick start

Run on the Docker VM (`docker01`, `/opt/stacks/ember`):

```bash
cp .env.example .env
# fill in OMLX_API_KEY, OPENROUTER_API_KEY, LITELLM_MASTER_KEY, LITELLM_DB_PASSWORD,
# EMBER_API_KEY, QDRANT_API_KEY (required even if the qdrant profile is unused)
bin/ember up
bin/ember doctor
```

`bin/ember doctor` checks that six required env vars are set (`OMLX_BASE_URL`,
`OMLX_API_KEY`, `LITELLM_MASTER_KEY`, `EMBER_API_KEY`, `OMLX_CHAT_MODEL`,
`OMLX_EMBED_MODEL`), that the compose config renders, that Qdrant (if running) has a real
API key, that oMLX and LiteLLM are reachable, that ember-api is healthy, and runs one real
`local-smart` completion and one `ember-embed` request. See
[`docs/deployment.md`](docs/deployment.md) for the full
walkthrough, including STT/TTS validation and the mini-off drill.

## URLs

| URL | Service | Notes |
|---|---|---|
| `https://ai.vaxel.xyz/v1` | LiteLLM gateway | public, OpenAI-compatible; via Cloudflare tunnel on the Proxmox host → `http://172.20.142.7:4000` |
| `http://172.20.142.7:4000/v1` | LiteLLM gateway | LAN — used by LAN consumers such as Hermes (`LLM_INTERNAL_URL`), no Cloudflare hairpin |
| `https://ember.vaxel.xyz` | Ember dashboard | optional, recommend Cloudflare Access; via the same tunnel → `http://172.20.142.7:3001` |
| `https://chat.vaxel.xyz` | Open WebUI (chat) | human UI — separate stack on Docker01, Ember only monitors it ([ADR 0010](docs/adr/0010-frontend-routing-voice.md)) |

## Model aliases

Clients never couple to a concrete model — they call an `ember-*` alias, and the alias's
backing model is `.env`-driven (see `config/litellm/ember.yaml.tmpl`). Current mapping:

| Alias | Provider | Model |
|---|---|---|
| `ember-embed` | oMLX | `bge-m3-mlx-8bit` |
| `ember-stt` | oMLX | `parakeet-tdt-0.6b-v3` |
| `ember-rerank` | oMLX | `bge-reranker-v2-m3` |
| `ember-tts` | oMLX | `Kokoro-82M-bf16` |
| `local-fast` | oMLX | `Qwen2.5-3B-Instruct-4bit` |
| `local-smart` | oMLX | `Ornith-1.5-9B-MLX-4bit` |
| `local-code` | oMLX | `gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4` |
| `local-vision` | oMLX | `gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4` |
| `cloud-fast` | OpenRouter | `inception/mercury-2.5` |
| `cloud-glm` | OpenRouter | `z-ai/glm-5.3-flash` |

Alias tiers (ADR 0010, amended 2026-09-17): `ember-` = local non-LLM services
(embed/rerank/stt/tts), `local-` = oMLX LLM/chat, `cloud-` = remote providers.

`ember-rerank` routes through LiteLLM with the `jina_ai/` provider prefix, which matches the
Cohere/Jina-shaped `/v1/rerank` oMLX serves; validated against the live stack with scores
identical to a direct oMLX call. Rationale in
[`docs/adr/0006-rerank-routing.md`](docs/adr/0006-rerank-routing.md).

## Documentation

| Doc | Covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System diagram, component summaries, failure behaviour |
| [`docs/deployment.md`](docs/deployment.md) | Deploying and validating the stack on Docker01 |
| [`docs/prox01.md`](docs/prox01.md) | Docker01 host facts, RAM, ports, stacks convention |
| [`docs/mac-mini.md`](docs/mac-mini.md) | oMLX + Hermes on `jons-mac-mini` |
| [`docs/omlx.md`](docs/omlx.md) | oMLX endpoints, health semantics, model management |
| [`docs/litellm.md`](docs/litellm.md) | Gateway config, aliases, virtual keys |
| [`docs/speech.md`](docs/speech.md) | STT/TTS models, blind-test result, example requests |
| [`docs/observability.md`](docs/observability.md) | Langfuse plan, LiteLLM spend logs today |
| [`docs/security.md`](docs/security.md) | Secrets, network exposure, key handling |
| [`docs/cloudflare.md`](docs/cloudflare.md) | Tunnel ingress, dashboard exposure |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Health states and fixes |
| [`docs/upstream-sync.md`](docs/upstream-sync.md) | Cherry-picking from `Osmantic/ODS` |
| [`docs/hermes-cutover.md`](docs/hermes-cutover.md) | Phase 5: switching Hermes to Ember |
| [`docs/adr/`](docs/adr/) | Architecture decision records, 0001–0009 |

## Attribution

Ember-AI is a fork of [`Osmantic/ODS`](https://github.com/Osmantic/ODS) (Apache-2.0). ODS
supplied the service-manifest schema, the dashboard scaffold, secret-scanning config and the
license/attribution itself; the rest of the ODS runtime was deleted as part of the lean
rebuild (see [`DOWNSTREAM.md`](DOWNSTREAM.md)). See `LICENSE` and `NOTICE`.
