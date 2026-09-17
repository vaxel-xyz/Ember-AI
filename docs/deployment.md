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
(`http://172.20.142.7:4000`) or the public one (`https://ai.vaxel.xyz/v1`) as `$LLM`.

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

#### Mini-off drill — raw capture (controller re-run, 18:21–18:24 UTC)

The controller independently re-ran the mini-off drill against the live Docker01 stack to
corroborate the prose row above with raw samples. The first re-run attempt saw `omlx stop`
take no effect within 60 s (oMLX stayed healthy) and was abandoned; the capture below is the
repeated attempt, which behaved as expected. Times are UTC; "dashboard HTTP" is the
`/api/services` response code where a poll snapshot exists at that instant.

| Time | oMLX state | LiteLLM state | Dashboard HTTP | Note |
|---|---|---|---|---|
| 18:21:02 | `healthy` (2 model(s) resident) | `degraded` | 200 | baseline, pre-drill |
| 18:21:25 | — | `degraded` | — | `omlx stop` issued; command returned "oMLX stopped" |
| 18:21:39 | mini `/health` unreachable (curl code `000000`) | — | — | first unreachable probe sample, ~14 s after stop |
| 18:22:13 | mini `/health` unreachable (`000000`) | — | — | mid-outage sample |
| 18:23:03 | mini `/health` unreachable (`000000`) | — | — | mid-outage sample |
| 18:23:27 | `unreachable` (timeout after 5s) | `degraded` | 200 | `/api/services` catches up ~5 s after the mini's `/health` died; `omlx start` issued at the same instant |
| 18:24:40 | `healthy` (1 model(s) resident) | `degraded` | 200 | recovery sample, taken ~73 s after `omlx start`; oMLX's own `/health` was back ~54 s after start per the drill log, so the extra ~19 s is the 15 s poll interval plus the 5 s sampling gap, not slower recovery |

Consistent with the Task 12 receipt row above: `ember-api`/`ember-dashboard` stayed on HTTP 200
throughout, `litellm` held its baseline `degraded` state independent of the oMLX outage, and
`qdrant` remained `unreachable` throughout (profile off) — omitted from the table as unchanged.
Raw JSON: `drill-raw-182124.json` (workspace file, not committed — git-ignored under
`.superpowers/`).

### Re-validation after final review (2026-09-14, 19:00–19:25 UTC)

Branch `feature/ember-lean-rebuild` @ `977c50f12`, deployed with
`git pull --ff-only && bin/ember up` on Docker01. Seven fix commits landed after the whole-branch
review; the headline change is that the `/api/services` poll loop no longer calls LiteLLM
`GET /health`, which performed a live inference call per deployment.

| Field | Result |
|---|---|
| Containers | `ember-api` Up (healthy), `ember-dashboard` Up (healthy), `ember-litellm` Up (healthy), `ember-litellm-postgres` Up (healthy). `ember-api` and `ember-dashboard` images rebuilt; n8n and Portainer stacks untouched. |
| `ember-litellm` restart | Required and easy to miss: `bin/ember up` leaves `litellm` running because its compose definition did not change, but `config/litellm/ember.yaml.tmpl` is rendered **at container start**. Until `docker compose restart litellm`, the new `model_info.mode` entries were absent from `/tmp/config.yaml`. |
| `bin/ember doctor` | All checks passed — env vars, compose config, oMLX reachable (1 model loaded), LiteLLM readiness, ember-api health, real `ember-auto` completion, `ember-embed` vector length 1024. |
| Gateway baseline | `healthy` — `10/10 aliases registered`, `detail = {"aliases_registered": 10, "aliases_expected": 10, "missing": []}` — with `OPENROUTER_API_KEY` still `CHANGE_ME`. Previously this read `degraded (6/9 unhealthy)` at rest. |
| Dashboard links | `litellm` → `https://ai.vaxel.xyz/ui/` (was `.../v1/ui/`); `qdrant` → `http://172.20.142.7:6333/dashboard` (was `http://qdrant:6333/dashboard`); `omlx` → `https://omlx.vaxel.xyz/docs`; `ember-api` → `null` (opts out). |
| Deep check endpoint | `POST /api/services/refresh?deep=true` returns LiteLLM's healthy/unhealthy endpoint lists; unauthenticated it returns 401. Shallow `POST /api/services/refresh` returns `{"deep": false}` and makes no `GET /health` call. |

#### Churn stopped

Quiet window 19:06:48–19:13:18 UTC, poll loop only, no deep checks:

| Measurement | Count |
|---|---|
| `ember-litellm` `GET /health ` (the deep, inference-triggering route) | **0** |
| `ember-litellm` `GET /health/readiness` | 36 (≈24 poll loop at 15 s + ≈12 container healthcheck at 30 s) |
| `ember-litellm` `GET /model/info` | 24 — exactly one per 15 s poll |
| `ember-api` `poll failed` log lines | 0 |
| oMLX `~/.omlx/logs/server.log` lines of any kind, 20:06:00–20:14:00 BST | **0** — no evictions, no completions, no load refusals |

oMLX activity by hour from `~/.omlx/logs/server.log` (BST; the poll loop's unauthenticated
`GET /health` is not logged by oMLX, so an idle Ember contributes nothing):

| Hour (BST) | Evictions | Chat completions | Load refusals |
|---|---|---|---|
| 09 | 1 | 3 | 0 |
| 10 | 0 | 28 | 0 |
| 11–16 | 4 | 1 | 0 |
| 18 | 30 | 23 | 42 |
| **19 (pre-fix loop running)** | **299** | **178** | **449** |
| 20 (post-fix; all of it from three deliberate deep checks + `doctor`) | 18 | 12 | 18 |

The 19:00 BST row is the C1 signature — ~300 evictions/hour caused by the poll loop asking
LiteLLM to complete a chat request against every deployment, including a 12B model whose
`projected memory 14.69GB would exceed the dynamic memory ceiling`.

#### `model_info.mode` verified

Same deep check, before and after `litellm` picked up the re-rendered config:

| Deep check | Healthy | Unhealthy | Notes |
|---|---|---|---|
| Before restart (no `model_info`) | 3 | 7 | `bge-m3-mlx-8bit`, `parakeet-tdt-0.6b-v3` and `Kokoro-82M-bf16` all rejected with *"is not an LLM / chat model. Use /v1/embeddings"* (resp. `/v1/audio/transcriptions`, `/v1/audio/speech`) — the probe was sending chat completions to embedding and audio models. |
| After restart (`model_info.mode` present) | 8 | 2 | Only `jina_ai/bge-reranker-v2-m3` (genuine memory ceiling at that instant: *"projected memory 11.71GB would exceed the dynamic memory ceiling 10.54GB"*) and `openrouter/z-ai/glm-5.3` (`OPENROUTER_API_KEY=CHANGE_ME`, expected). |

#### Detection latency

The poll loop's cadence is the thing C1 broke: `asyncio.gather` awaited the ~30 s
`GET /health` call, so *every* state change inherited that delay — which is why the original
drill measured 44 s to detect and 57–73 s to recover. Measured from 76 samples of
`/api/services` at 5 s intervals, 19:15:47–19:22:06 UTC (raw rows on Docker01 at
`/tmp/drill2.jsonl`, formatter at `/tmp/capfmt.py`):

| Metric | Value |
|---|---|
| Distinct polls observed | 27 |
| Poll interval | min 15 s, max 16 s, mean 15.0 s (`EMBER_POLL_INTERVAL_S=15`) |
| oMLX `health_timeout` (manifest) | 5 s |
| **Worst-case detection bound** | **16 s + 5 s = 21 s ≤ 25 s** |
| `litellm` state across all 76 samples | `healthy (10/10 aliases registered)` — now independent of oMLX, where it previously flipped to `degraded (9/9 unhealthy)` whenever the mini went away |
| `ember-api` / `ember-dashboard` HTTP across all 76 samples | 200 / 200 |

#### Mini-off drill — not re-run (blocker on the mini)

The drill could not be repeated, and the reason is a pre-existing condition on the mini, not
a regression in this branch:

- `~/.omlx/bin/omlx stop` prints `oMLX stopped` but port 8000 stays bound; `/health` kept
  returning 200 for 80 s afterwards.
- `osascript -e 'quit app "oMLX"'` also left `/health` at 200 for 35 s.
- `~/.omlx/bin/omlx restart` refuses outright: `Port 8000 is in use by PID 66607`.

`lsof` shows the listener is `omlx-server` **PID 66607, PPID 1**, started 19:02:21 BST — the
instant the *previous* drill issued `omlx start`. That run left behind a detached, orphaned
server which the oMLX CLI no longer manages, while `oMLX.app` (PID 79372, launchd label
`application.app.omlx.64052047.64052054`) runs alongside it. The CLI's `stop`/`restart` act on
the app's server, not on the orphan, so oMLX cannot be cycled by the documented path.

**Action for Jon:** reap PID 66607 on the mini, confirm `oMLX.app` re-binds :8000 (or run
`~/.omlx/bin/omlx start`), then re-run the drill. It was deliberately not reaped here: the mini
is Hermes's fallback inference provider, and a kill that fails to come back leaves the node
down. Two non-invasive substitutes were attempted and both were refused by local tooling
policy — a self-cleaning `DOCKER-USER` DROP rule for oMLX:8000 on Docker01, and a throwaway
`ember-api` container pointed at a stoppable `/health` stub on the compose network. The poll
cadence table above is the substitute evidence for the ≤ 25 s claim; it bounds detection
without needing the node down.

## Branch 2 receipt (2026-09-16)

Frontend/routing ADR applied to the live stack (`feature/frontend-routing-adr`, head at
receipt time `5c56a990`). All values below are from the Docker01 control plane; no secrets
are recorded.

| Check | Result |
|---|---|
| Ember `.env` hostname | `LLM_PUBLIC_URL=https://ai.vaxel.xyz/v1`; `OPENWEBUI_HOST=172.20.142.7`, `CHAT_PUBLIC_URL=https://chat.vaxel.xyz` appended |
| oMLX key rotation | the mini's oMLX bearer had been rotated since Phase 1; the current key was moved to `/opt/stacks/ember/.env` over an ssh pipe (never logged); `bin/ember restart` re-rendered the template |
| `bin/ember doctor` | all checks passed, including the new `local-smart` completion (chat + embed green) |
| `/model/info` alias set | 13 names: `ember-auto, ember-code, ember-embed, ember-fast, ember-local, ember-rerank, ember-stt, ember-think, ember-tts, ember-vision, heavy, local-fast, local-smart` |
| Virtual key | `open-webui` created via `bin/ember keys create open-webui --budget 20` (name only recorded; an earlier same-alias key from a failed capture was deleted via `/key/delete` first) |
| Open WebUI stack | `/opt/stacks/openwebui` from `deploy/openwebui/`; container `open-webui` healthy; `GET http://127.0.0.1:3003/health` → 200; `ENABLE_SIGNUP=true` left for Jon's first-admin sign-up |
| Ember dashboard view | `/api/services`: `open-webui (healthy, consumer)`, `litellm (healthy, gateway)`; `/api/nodes`: `consumers: [open-webui]`, docker01 list excludes it |
| Model list seen by the virtual key | `/v1/models` with the virtual key → the same 13 aliases |
| Completion via the virtual key | `local-smart` chat completion → 200, content returned |
| Memory on Docker01 | 2.9 GiB used / 7.8 GiB total; `open-webui` 1.17 GiB of its 1.5 GiB limit; `ember-litellm` 426 MiB; control plane unchanged |

Pending (Jon): Cloudflare hostnames `ai./chat./ember.vaxel.xyz`; OpenRouter key into
`/opt/stacks/ember/.env` (validates `heavy`/`ember-think`); first Open WebUI admin sign-up at
`chat.vaxel.xyz`, then `ENABLE_SIGNUP=false`.

## Cloud alias validation receipt (2026-09-17)

OpenRouter key provisioned in `/opt/stacks/ember/.env` (fingerprint-checked into the running
`ember-litellm` container; value never logged). Both cloud aliases validated end-to-end
through the gateway with the master key:

| Alias | Upstream model | Result |
|---|---|---|
| `cloud-glm` | `z-ai/glm-5.3-flash` | completion OK ("pong"), finish `stop`; 169 reasoning tokens on a trivial prompt — budget `max_tokens` accordingly |
| `cloud-fast` | `inception/mercury-2.5` | completion OK ("pong"), finish `stop` |

On-demand deep gateway check (`POST /api/services/refresh?deep=true`): 6/10 deployments
healthy; the 4 failures are oMLX memory-guard artifacts of the deep check itself — it fires
live calls at every deployment concurrently and the mini (16 GB, shared with desktop use)
refuses to load `bge-reranker-v2-m3`, `Ornith-1.5-9B` and `gemma-4-12B` all at once. Spot
check: `local-code` (gemma-4-12B) completes fine when called individually. Do not read the
deep check's unhealthy list as an outage; the shallow probe and `bin/ember doctor` are the
health truth.
