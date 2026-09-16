# Ember-AI Phase 1 — final fix wave report

**Date:** 2026-09-14
**Branch:** `feature/ember-lean-rebuild`
**Start:** `f8cc15d4e` · **Final head:** `dc5659bf5` (pushed, CI green)
**Spec:** `/Users/jtotham/Projects/superpowers/specs/2026-09-14-ember-ai-design.md` (§4.4 as amended)
**Live stack:** Docker01 `/opt/stacks/ember`, synced to `dc5659bf5`, all four containers healthy

## Commits

| # | Commit | Subject |
|---|---|---|
| 1 | `76c699f19` | `fix(ember-api): gateway probe never triggers inference; deep check on demand` |
| 2 | `dd5f8dc67` | `fix(ember-api): poll loop survives probe exceptions; tolerate null engine_pool` |
| 3 | `186a3dd85` | `fix(ember-api): gateway degraded only when no aliases/deployments healthy` |
| 4 | `3d7de1c46` | `fix: make load-bearing template variables required everywhere` |
| 5 | `0f44d899a` | `fix(ember-api): correct dashboard links for gateway and container-only services` |
| 6 | `8f7471f8c` | `docs: rerank is routed via LiteLLM; refresh stale facts` |
| 7 | `977c50f12` | `chore: repo hygiene from final review` |
| 8 | `dc5659bf5` | `docs: re-validation receipt after the final review fix wave` |

## Test and CI results

- `cd ember-api && python3 -m pytest -q` → **50 passed** (was 27 at `f8cc15d4e`)
- `cd ember-api && ruff check .` → **All checks passed**
- `cd dashboard && npm run lint` → 0 errors, 20 pre-existing warnings (unused imports in tests/App.jsx)
- `cd dashboard && npm test` → **4 passed**; `npm run build` → built in 5.76 s
- `bash tests/run.sh` → manifests OK, compose SKIP (no docker on the Mac), doctor OK, pytest 50, vitest 4 → **ALL OK**
- CI on `dc5659bf5`: `ci` **success**, `secret-scan` **success** (`gh run watch --exit-status` → exit 0)

---

## Per-finding detail

### C1 (Critical) — gateway probe triggered inference → commit 1

`_probe_litellm` called `LiteLLMClient.deployment_health()` → LiteLLM `GET /health`, which runs a
live call per deployment (a chat completion whenever `model_info.mode` is unset). At a 15 s poll
interval that fired ~10 inference requests at the mini every ~30 s.

Fixed by replacing the poll-path call with readiness + `GET /model/info`:

- `unreachable` on transport error/timeout
- `reachable-unhealthy` on readiness ≥ 400
- `degraded` when `/model/info` fails or is missing published aliases
- `healthy` otherwise, `detail = {aliases_registered, aliases_expected, missing}`

`ALIASES` moved to `ember_api/aliases.py` (with a derived `ALIAS_NAMES`) so `health.py` compares
against the published set without importing the routers package. `deployment_health()` is gone
from the poll path entirely; it is now reachable only via
`POST /api/services/refresh?deep=true` (bearer-protected, `?deep` defaults false) and
`bin/ember doctor`, which already made real chat/embed calls and was left alone.

**Tests** (`ember-api/tests/test_health.py`, `test_api.py`):

- `test_litellm_degraded_when_an_alias_is_missing` — replaces
  `test_litellm_degraded_when_a_deployment_is_unhealthy`; one alias absent from `/model/info` →
  `degraded`, `missing == ["ember-rerank"]`
- `test_litellm_healthy_when_full_alias_set_registered` — full set → `healthy`, exact `detail`
- `test_litellm_probe_never_calls_live_health_endpoint` — registers a respx route for
  `GET /health` and asserts `.called is False` after `probe()`
- `test_litellm_reachable_unhealthy_when_readiness_errors`
- `test_litellm_invalid_json_body_is_degraded` — retargeted at `/model/info`
- `test_shallow_refresh_does_not_deep_check`, `test_deep_refresh_runs_deployment_health`,
  `test_deep_refresh_requires_key`

**Docs:** `docs/architecture.md` (endpoint table gains both refresh rows; §health rewritten) and
`docs/troubleshooting.md` (new *Deep gateway check (on demand)* section with the curl, plus an
explicit "do not poll either of these on a timer").

### I1 + minors — poll loop fragility → commit 2

Three narrowings that could freeze the whole registry:

- All three first-request handlers caught `httpx.ConnectError` only, so `ReadError`,
  `RemoteProtocolError`, `WriteError` and `ProxyError` escaped. Now `httpx.TransportError`, with
  the specific `TimeoutException` branch kept first (it is a `TransportError` subclass), and the
  exception class name as the reason.
- `_probe_omlx` used `body.get("engine_pool", {})`, which yields `None` — not `{}` — for
  `"engine_pool": null`, so the next `.get` raised. Now `or {}`, plus an `isinstance(body, dict)`
  guard that returns `reachable-unhealthy` for a non-object JSON body.
- `Registry.run` had no guard: one raising probe ended the loop while `/api/services` kept
  serving the last snapshot as current. Wrapped in the one permitted broad `except`, logging
  `log.exception("poll failed")`. `CancelledError` derives from `BaseException`, so shutdown
  still propagates.

**Tests:**

- `test_unreachable_on_remote_protocol_error` — reason `"connect failed: RemoteProtocolError"`
- `test_omlx_null_engine_pool_is_degraded_not_a_crash`
- `test_omlx_non_object_json_body_is_reachable_unhealthy`
- new `ember-api/tests/test_poll_loop.py`:
  `test_run_continues_after_a_probe_raises` (monkeypatched `probe` raises `RuntimeError` on the
  first iteration, 0.01 s interval, cancel after the loop advances; asserts it kept going, a
  later poll completed, and `"poll failed"` is in `caplog`) and
  `test_poll_once_propagates_so_the_supervisor_can_log`

**Verified meaningful:** reverting only `Registry.run` makes
`test_run_continues_after_a_probe_raises` fail with `RuntimeError: probe blew up`; restoring it
passes. (Captured during the fix wave.)

### I2 — gateway `degraded` semantics → commit 3

Behaviour is already correct from commit 1: `degraded` only when an alias is not routable at
all, never because an individual deployment failed a deep probe. This commit brings the docs in
line — `docs/architecture.md`'s state table and `docs/troubleshooting.md`'s `degraded` row now
say the same thing as the code, and say explicitly that per-deployment failures belong in the
deep check's `unhealthy_endpoints`.

Evidence it matters: the pre-fix baseline sat at `degraded (6/9 unhealthy)` at rest while chat,
embed, STT and TTS all passed functional tests. Post-fix baseline is `healthy`, 10/10.

### I3 — load-bearing template variables → commit 4

`REQUIRED_ENV` in `routers/config.py` was hand-written and had drifted from
`config/litellm/ember.yaml.tmpl`: `OMLX_RERANK_MODEL` and `LITELLM_TURN_OFF_MESSAGE_LOGGING` were
both load-bearing (`render-config.py` raises `KeyError` without them, so the gateway does not
start) yet neither was validated. Now derived:

- `template_path()` reads `EMBER_LITELLM_TEMPLATE`, default `/app/config/litellm/ember.yaml.tmpl`
- `template_identifiers()` → `string.Template(text).get_identifiers()`
- `required_env()` = those ∪ `("EMBER_API_KEY", "OMLX_API_KEY", "LITELLM_MASTER_KEY")` — the three
  the template cannot advertise because LiteLLM resolves them via `os.environ/NAME` rather than a
  `${}` placeholder
- `run_checks()` adds a `litellm_template_readable` check, so a missing or placeholder-free
  template is a visible failure rather than a silently empty required set

`docker-compose.yml` mounts `./config/litellm/ember.yaml.tmpl:/app/config/litellm/ember.yaml.tmpl:ro`
into `ember-api` and sets `EMBER_LITELLM_TEMPLATE`; `tests/conftest.py` points it at the repo file.

`config/litellm/ember.yaml.tmpl` also gains `model_info` on the non-chat aliases:
`{mode: embedding}` (embed), `{mode: rerank}` (rerank), `{mode: audio_transcription}` (stt),
`{mode: audio_speech, health_check_voice: af_heart}` (tts).

**Tests** — new `ember-api/tests/test_config_validate.py`:
`test_template_path_honours_env_override`, `test_template_path_defaults_to_the_container_mount`,
`test_required_env_superset_of_template_identifiers`,
`test_required_env_includes_non_placeholder_secrets`,
`test_previously_optional_vars_are_now_required`,
`test_unreadable_template_is_reported_as_a_failed_check`. Plus
`test_non_chat_aliases_declare_their_mode` in `test_render_litellm.py`, which asserts each
non-chat mode, the TTS `health_check_voice`, and that chat routes carry no explicit mode.

**SKIPPED — `.env.schema.json` `required` still needs `OMLX_RERANK_MODEL`.** See *Skipped* below.
`LITELLM_TURN_OFF_MESSAGE_LOGGING` was already in `required` and was left there.

### I5 — dashboard links → commit 5

`routers/services.py::_ui_url`:

- `_strip_api_suffix()` removes a trailing `/v1` before appending `ui_path`, so
  `LLM_PUBLIC_URL=https://llm.vaxel.xyz/v1` + `/ui/` → `https://llm.vaxel.xyz/ui/`, not
  `https://llm.vaxel.xyz/v1/ui/`
- a Docker service with no public URL is now built from the host part of
  `settings.llm_internal_url` (`urlsplit(...).hostname`) plus its published external port, so
  `qdrant` → `http://172.20.142.7:6333/dashboard` instead of the unresolvable
  `http://qdrant:6333/dashboard`; falls back to the manifest host if the URL will not parse

`services()` takes `settings` via `Depends`. `tests/conftest.py` gained `EMBER_PUBLIC_URL` so the
fixtures reflect a real `.env`.

**Tests** — new `ember-api/tests/test_ui_urls.py`: `test_strip_api_suffix` (5 params),
`test_gateway_ui_is_not_nested_under_v1`,
`test_container_only_service_uses_the_lan_host_and_published_port`,
`test_public_url_without_v1_is_untouched`, `test_services_opting_out_have_no_link`,
`test_docker_service_falls_back_to_lan_when_its_public_url_is_unset`,
`test_falls_back_to_the_manifest_host_when_internal_url_is_unparseable`. Plus four new assertions
in `test_services_and_nodes`.

**Confirmed live:** see the redeploy section — all four URL shapes correct in the running stack.

### I4 + minors — docs → commit 6

- `README.md`: `ember-rerank` row added to the alias table; the "not configured yet" paragraph
  replaced with the `jina_ai/` routing fact
- `docs/litellm.md`: `ember-rerank` template row added; "no entry in the template yet" removed;
  new paragraph documenting `model_info.mode` and linking the deep-check section
- `docs/omlx.md:18`: `/v1/rerank` is "via LiteLLM (`jina_ai/` provider prefix)", not "direct to
  oMLX only — not routed through LiteLLM yet"
- `docs/prox01.md`: RAM row → 7.8 GiB (raised from 3.8 GiB, applied on the 2026-09-14 reboot);
  the RAM note rewritten — Langfuse is gated on Phase 3 not starting, not on memory
- `docs/observability.md`: same correction
- `docs/deployment.md`: one clause reconciling 54 s vs 73 s — the recovery sample was taken ~73 s
  after `omlx start` while the drill log had oMLX's own `/health` back at ~54 s; the ~19 s gap is
  the 15 s poll interval plus the 5 s sampling cadence, not slower recovery
- `docs/architecture.md` §health: the C1 lesson in one sentence ("a health probe that performs
  inference is not a health probe"), with the numbers
- `DOWNSTREAM.md:22`: `Task 11 recreates .github/workflows/ from scratch` → plain past tense

### Repo hygiene → commit 7

- Deleted `dashboard/frontend/model-manager.html` and `dashboard/templates/index.html` (ODS
  leftovers; grep found no reference, and the Dockerfile ships `dist/` only). Both directories
  removed.
- `.gitleaks.toml`: the dead-history allowlist described itself as "verified false-positive",
  which is wrong — the LiveKit pair inside it is a real upstream disclosure. Description and the
  comment above it corrected and reflowed. The `.env.example` path allowlist **removed**, verified
  in two steps: `git show HEAD:.env.example | gitleaks stdin --config .gitleaks.toml` → *no leaks
  found*; then `gitleaks git . --config .gitleaks.toml` with the allowlist gone → *3804 commits
  scanned, no leaks found*. Local gitleaks was already installed at 8.30.1 (no `brew install`
  needed).
- `.pre-commit-config.yaml`: gitleaks `v8.21.2` → `v8.30.1`; deleted the
  `no-backticks-in-installer-heredocs` local hook (its `entry` pointed at
  `ods/scripts/check-heredoc-backticks.awk`, and `ods/` does not exist); deleted the comment
  referencing `.github/workflows/lint-shell.yml`, which does not exist either (only `ci.yml` and
  `secret-scan.yml` do); retitled the shellcheck hooks off "installer".
- `.gitignore`: rewritten. The `.env` / `.env.*` / `!.env.example` triplet appeared twice; `ods/**`,
  `token-spy/` and `archive/` entries were dead. Grouped, deduped, and the caches the tree actually
  produces added (`.pytest_cache/`, `.ruff_cache/`, `.venv/`).
- `dashboard/nginx.conf`: nginx injects `EMBER_API_KEY`, so everything it proxies is reachable
  without a key. The general `/api/` location is now `limit_except GET { deny all; }`, with an
  exact-match `location = /api/services/refresh` allowing `GET POST`. Exact matches beat the
  prefix, so `?deep=true` lands on the right block, and the entrypoint's `sed -i ... g` rewrites the
  bearer in both blocks. **Validated** on Docker01: `nginx -t` in `nginx:alpine` against the file
  with a dummy key → *syntax is ok / test is successful*.
- Theme rename: `ods-theme` → `ember-theme`, theme id `ods` → `dark` across
  `dashboard/src/contexts/ThemeContext.jsx`, `dashboard/index.html`, `dashboard/src/index.css`.
  Also dropped tailwind's unused legacy `ods` colour namespace (grep confirmed no `ods-*` utility
  class in use). No ODS string remains anywhere in `dashboard/`. Behaviour preserved; anyone
  holding the old localStorage key falls back to the default theme once.

---

## Redeploy log

```
ssh vaxel-docker 'cd /opt/stacks/ember && git pull --ff-only && bin/ember up'
```

- Pulled `c4aad464` → `977c50f12`; `ember-api` and `ember-dashboard` images rebuilt;
  `ember-api` restarted (it had been stopped by the controller), `ember-dashboard` recreated
- `ember-api` Up (healthy), `ember-dashboard` Up (healthy), `ember-litellm` Up (healthy),
  `ember-litellm-postgres` Up (healthy)
- n8n (7 containers) and Portainer untouched throughout; Hermes not touched

**Gotcha worth remembering:** `bin/ember up` left `litellm` *running* because its compose service
definition did not change — but `config/litellm/ember.yaml.tmpl` is rendered at container start,
so the new `model_info.mode` entries were absent from `/tmp/config.yaml` until an explicit
`docker compose restart litellm`. Confirmed present afterwards by
`docker exec ember-litellm grep -n model_info /tmp/config.yaml`.

`bin/ember doctor` — all green:

```
✓ env OMLX_BASE_URL / OMLX_API_KEY / LITELLM_MASTER_KEY / EMBER_API_KEY / OMLX_CHAT_MODEL / OMLX_EMBED_MODEL set
✓ compose config renders
✓ oMLX reachable (loaded models: 1)
✓ LiteLLM readiness
✓ ember-api health
✓ ember-auto completion: The user is asking me to reply with
✓ ember-embed vector length 1024
all checks passed
```

Baseline `/api/services` (19:02:01 UTC), gateway `healthy` with `OPENROUTER_API_KEY=CHANGE_ME`:

```
ember-api          healthy   HTTP 200                    ui=None
ember-dashboard    healthy   HTTP 200                    ui=https://ember.vaxel.xyz/
litellm            healthy   10/10 aliases registered    ui=https://llm.vaxel.xyz/ui/
   detail: {"aliases_registered": 10, "aliases_expected": 10, "missing": []}
litellm-postgres   healthy   tcp open                    ui=None
omlx               healthy   1 model(s) resident         ui=https://omlx.vaxel.xyz/docs
   detail: {"default_model": "Ornith-1.5-9B-MLX-4bit", "model_count": 8, "loaded_count": 1,
            "memory_used_gb": 7.6, "memory_ceiling_gb": 12.0}
qdrant             unreachable  connect failed: ConnectError  ui=http://172.20.142.7:6333/dashboard
```

Deep endpoint behaviour: `POST /api/services/refresh` → `{"polled_at": ..., "deep": false}` and no
`GET /health`; `POST /api/services/refresh?deep=true` → `deep: true` plus a `gateway` object with
`healthy_count`/`unhealthy_count`/both endpoint lists; unauthenticated → **401**.

## Churn-stopped evidence

Quiet window 19:06:48–19:13:18 UTC, poll loop only:

| Measurement | Count |
|---|---|
| `ember-litellm` `GET /health ` (deep, inference-triggering) | **0** |
| `ember-litellm` `GET /health/readiness` | 36 (≈24 poll + ≈12 container healthcheck) |
| `ember-litellm` `GET /model/info` | 24 — exactly one per 15 s poll |
| `ember-api` `poll failed` lines | 0 |
| oMLX `server.log` lines of any kind, 20:06:00–20:14:00 BST | **0** |

Over the whole 20 min since redeploy, `docker logs --since 20m ember-litellm | grep -c "GET /health "`
→ **3**, which is exactly the three deep checks issued deliberately (one via the API endpoint, two
direct `curl`s). Nothing from the loop.

oMLX churn by hour (`~/.omlx/logs/server.log`, BST):

| Hour | Evictions | Chat completions | Load refusals |
|---|---|---|---|
| 09 | 1 | 3 | 0 |
| 10 | 0 | 28 | 0 |
| 11–16 | 4 | 1 | 0 |
| 18 | 30 | 23 | 42 |
| **19 (pre-fix loop live)** | **299** | **178** | **449** |
| 20 (post-fix; all from 3 deliberate deep checks + doctor) | 18 | 12 | 18 |

The 19:00 row is the C1 signature, with refusals reading
`Cannot load gemma-4-12B-...: projected memory 14.69GB would exceed the dynamic memory ceiling`.

`model_info.mode` verified by the same deep check before and after the litellm restart:

| Deep check | Healthy | Unhealthy | Notes |
|---|---|---|---|
| Before (no `model_info`) | 3 | 7 | `bge-m3-mlx-8bit`, `parakeet-tdt-0.6b-v3`, `Kokoro-82M-bf16` all rejected with *"is not an LLM / chat model. Use /v1/embeddings"* etc. |
| After (`model_info.mode` live) | 8 | 2 | only `jina_ai/bge-reranker-v2-m3` (real memory ceiling that instant) and `openrouter/z-ai/glm-5.3` (`CHANGE_ME` key) |

## Drill table

The mini-off drill **was not re-run** — see *Skipped*. Substitute measurement: 76 samples of
`/api/services` at 5 s intervals, 19:15:47–19:22:06 UTC (raw rows on Docker01 at
`/tmp/drill2.jsonl`, formatter `/tmp/capfmt.py`).

| Metric | Value |
|---|---|
| Samples / distinct polls | 76 / 27 |
| Poll interval observed | min 15 s, max 16 s, mean 15.0 s (`EMBER_POLL_INTERVAL_S=15`) |
| oMLX `health_timeout` (manifest) | 5 s |
| **Worst-case detection bound** | **16 + 5 = 21 s ≤ 25 s** |
| `litellm` state, all 76 samples | `healthy (10/10 aliases registered)` |
| `omlx` state, all 76 samples | `healthy (2 model(s) resident)` |
| `ember-api` / `ember-dashboard` HTTP, all 76 samples | 200 / 200 |

Representative rows:

| sample (UTC) | api | dash | polled_at | omlx | litellm |
|---|---|---|---|---|---|
| 19:15:47 | 200 | 200 | 19:15:35 | healthy (2 model(s) resident) | healthy (10/10 aliases registered) |
| 19:15:52 | 200 | 200 | 19:15:50 | healthy | healthy — new poll (+15 s) |
| 19:16:07 | 200 | 200 | 19:16:05 | healthy | healthy — new poll (+15 s) |
| 19:20:40 | 200 | 200 | 19:20:36 | healthy | healthy — new poll (+16 s) |
| 19:22:06 | 200 | 200 | 19:22:06 | healthy | healthy — new poll (+15 s) |

Why this is the right substitute: C1's real damage to detection was that `asyncio.gather` awaited
the ~30 s `GET /health`, so *every* state transition inherited that delay — which is why the
original drill measured 44 s to detect and 57–73 s to recover. With that call gone the loop
completes on schedule (27 consecutive polls at 15–16 s), so detection is bounded by poll interval
plus the probe's own 5 s timeout. It does not, however, re-prove the end-to-end transition, which
still wants the real drill once the mini is unblocked.

## Skipped, and why

1. **`.env.schema.json` `required` += `OMLX_RERANK_MODEL`** — not done. `.env*` paths are denied by
   this session's permission rules: the `Read` tool returns *"File is in a directory that is denied
   by your permission settings"*, and a `git` command naming the path is refused with
   *"blocked by a deny rule"* (so even `git add` would fail). The task suggested editing it via a
   `python3 -c` script; that is deliberately routing around a user-configured guard, so it was not
   done. **Apply by hand:** insert `"OMLX_RERANK_MODEL",` into the `required` array after
   `"OMLX_TTS_MODEL"`. Nothing currently fails without it — `render-config.py` already raises
   `KeyError` on a missing placeholder, and `/api/config/validate` now derives the same requirement
   from the template — so this is belt-and-braces for `tests/test-compose.sh`. If the deny glob was
   only ever meant to cover the real `.env`, narrowing it to `.env` / `.env.local` would let this be
   fixed normally. No change was needed to `.env.example`: it already carries
   `OMLX_RERANK_MODEL=bge-reranker-v2-m3`.

2. **Mini-off drill re-run** — blocked by a pre-existing condition on the mini, not by this branch.
   `~/.omlx/bin/omlx stop` prints `oMLX stopped` but leaves :8000 bound (`/health` kept returning 200
   for 80 s); `osascript -e 'quit app "oMLX"'` likewise (200 for 35 s); `~/.omlx/bin/omlx restart`
   refuses with `Port 8000 is in use by PID 66607`. `lsof` shows the listener is `omlx-server`
   **PID 66607, PPID 1, started 19:02:21 BST** — the instant the *previous* drill ran `omlx start`.
   That run orphaned a detached server the CLI no longer manages, while `oMLX.app` (PID 79372,
   launchd `application.app.omlx.64052047.64052054`) runs beside it.
   **Action for Jon:** reap PID 66607, confirm `oMLX.app` re-binds :8000 (else `omlx start`), then
   re-run the drill. Deliberately not reaped here — the mini is Hermes's fallback provider and a kill
   that fails to come back leaves the inference node down, which is not a call to make unattended.

3. **Two non-invasive drill substitutes** — both refused by local tooling policy, not attempted
   further: (a) a self-cleaning `DOCKER-USER` DROP rule for `172.20.142.184:8000` on Docker01
   (add → sleep 100 → delete, nohup'd so it cleans up even if ssh drops); (b) a throwaway
   `ember-api` container on `ember_default` pointed at a stoppable oMLX-shaped `/health` stub. Both
   were blocked by the auto-mode classifier. Neither was worked around. No containers, networks or
   firewall rules were created — verified afterwards: only the four Ember containers plus the
   untouched n8n/Portainer ones exist.

## Notes / concerns

- **`litellm` needs an explicit restart when the template changes.** `bin/ember up` will not do it.
  Worth either adding `--force-recreate litellm` to `bin/ember up`, or moving the render to a
  compose-visible input so the hash changes. Not done here — it is a design change, not a review
  finding.
- The deep check still reports `jina_ai/bge-reranker-v2-m3` unhealthy when the mini is near its
  memory ceiling (2.38 GB fp32 reranker). That is a real capacity condition, correctly surfaced,
  and no longer affects the gateway's polled state. The 8-bit MLX conversion noted in spec §4.1
  would help.
- `openrouter/z-ai/glm-5.3` remains deep-check-unhealthy until a real `OPENROUTER_API_KEY` lands.
  Expected; the gateway is `healthy` regardless because the alias is registered and routable.
- 20 pre-existing eslint warnings in `dashboard/` (unused imports). Untouched — out of scope.
- No secret value (oMLX key, LiteLLM master key, `EMBER_API_KEY`, DB password) was printed to any
  transcript, log, or file during this wave. Remote `curl`s sourced `.env` inside the remote shell.
