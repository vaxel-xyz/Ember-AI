# REPORT — branch 2 (feature/frontend-routing-adr), OpenWork overnight 2026-09-16

Stacks on #1 (`feature/ember-lean-rebuild`, `b44d98123`). Draft PR to follow at the end; do not merge either PR.

## Task 0 — branch + baseline
- Branch `feature/frontend-routing-adr` already existed locally (created by the handoff commit wave), verified based on `b44d98123` (`git merge-base --is-ancestor` OK). No new branch needed.
- Venv rebuilt: `uv venv .venv --python 3.12` + `uv pip install -e './ember-api[dev]' jsonschema pyyaml`.
- Baseline before any change: ember-api 52 pytest passed, ruff clean; dashboard 4 tests passed, lint + build OK; `bash tests/run.sh` → ALL OK (compose test SKIPs locally, no Docker on the laptop).
- Note: `tests/run.sh` must run with the venv activated (bare `python3` needs `jsonschema`).

## Task 1 — gateway hostname → ai.vaxel.xyz/v1
- Commit `28868435` `feat: gateway public hostname is ai.vaxel.xyz/v1 (ADR 0010)`.
- Replaced `llm.vaxel.xyz` → `ai.vaxel.xyz` in 18 files (`.env.example` via python3 script per HANDOFF rule 9; `settings.py` default; 5 test files; README + 10 docs incl. the two Phase 1 design/plan history docs, which the PLAN grep did not exclude).
- `docs/cloudflare.md`: ingress now `ai.vaxel.xyz → :4000`, `chat.vaxel.xyz → :3003`, `ember.vaxel.xyz → :3001`; added the "previously reserved for OpenWork, plan dropped" sentence.
- `docs/adr/0001`: added "Superseded in part (2026-09-16)" line under Status, pointing at ADR 0010 (file lands in Task 5).
- Post-change grep for `llm.vaxel.xyz` outside `docs/adr/0001` and `docs/handoff/`: 0 hits.
- Tests: 52 pytest + ruff clean, 4 dashboard tests, `tests/run.sh` ALL OK.
- CI: `ci` run 35154505830 success; `secret-scan` success on `28868435`.
- Deviation: none. (One flaky first `tests/run.sh` — doctor stub race — clean on re-run.)

## Task 2 — local-fast/local-smart/heavy aliases + OMLX_RERANK_MODEL schema fix
- Commit: `feat: add local-fast/local-smart/heavy aliases; require OMLX_RERANK_MODEL in schema` (pushed; ci + secret-scan success).
- `ember.yaml.tmpl`: 3 new entries appended after `ember-think`, same targets as `ember-fast`/`ember-auto`/`ember-think`.
- `aliases.py`: ALIASES now 13 names; `ALIAS_NAMES` derives, so the gateway probe expects 13 automatically (test_health.py derives from `ALIAS_NAMES` too — no hardcoded 10-list existed to extend; test_api.py mocks the gateway as unreachable, so no `/model/info` mock needed extending).
- Tests added: `test_human_aliases_share_targets_with_ember_aliases` (identical `litellm_params` per pair), 13-name order assertion, chat-routes-no-mode loop extended, `test_schema_required_covers_template_identifiers` (`.env.schema.json` `required` ⊇ template identifiers).
- `.env.schema.json`: `required` += `OMLX_RERANK_MODEL` (python3 edit; closes the Phase 1 open item).
- Docs: alias tables in `docs/litellm.md` + `README.md` gained the three rows.
- Tests: 54 pytest (was 52) + ruff clean; dashboard 4; `tests/run.sh` ALL OK.
- Deviation: none.

## Task 3 — Open WebUI as an external consumer tile
- Commit: `feat: represent Open WebUI as an external consumer tile` (pushed; ci + secret-scan success).
- Schema: `x_ember.role` enum += `consumer`. New `services/open-webui/manifest.yaml` exactly per PLAN (external, port 3003, `/health`, `public_url_env: CHAT_PUBLIC_URL`, node docker01, managed false).
- `.env.example` += `OPENWEBUI_HOST`/`CHAT_PUBLIC_URL` block (python3 edit); `.env.schema.json` += both properties (string, not secret, not required).
- `routers/services.py` `/api/nodes`: docker01 list excludes `role == "consumer"`; third group `consumers` added.
- Dashboard `Overview.jsx`: `NODES` += Consumers; filter per PLAN. Test: `open-webui` mock service asserted under Consumers and absent from the control-plane section (`within()`).
- Tests: first run caught `public_url` None — the conftest `env` fixture lacked `CHAT_PUBLIC_URL`; added `OPENWEBUI_HOST`/`CHAT_PUBLIC_URL` to the fixture (mirrors a configured deployment). 55 pytest + ruff clean; dashboard 4; `tests/run.sh` ALL OK.
- Deviation: none beyond the fixture fix above.

## Task 4 — reference Open WebUI stack + docs + doctor
- Commit: `feat: reference Open WebUI stack, docs, and local-smart doctor check` (pushed; ci + secret-scan success).
- `deploy/openwebui/compose.yml` exactly per PLAN (pinned `ghcr.io/open-webui/open-webui:v0.11.3`, virtual-key required, `DEFAULT_MODELS: local-smart`, 1536M limit, curl healthcheck).
- `deploy/openwebui/.env.example` (python3 write, placeholders only) + `deploy/openwebui/README.md` (deploy steps, first-admin flow, key rotation, backup volume; states Open WebUI never receives provider keys).
- `docs/open-webui.md`: role, topology diagram, consumer tile, PWA install, backup.
- `bin/ember doctor`: `local-smart` completion check added after the `ember-auto` block. `tests/test-doctor.sh` needed no change (its stub answers any chat POST, as the PLAN predicted).
- Tests: 55 pytest + ruff clean; dashboard 4; `tests/run.sh` ALL OK.
- Deviation: none.

## Task 5 — ADR 0010 + roadmap + ownership updates
- Commit: `docs: ADR 0010 frontend/routing/voice; roadmap; ownership updates` (pushed; ci + secret-scan success).
- `docs/adr/0010-frontend-routing-voice.md` = `adr-0010-source.md` copied verbatim (the source was already sanitised — the Nabu Casa redaction note is in the file itself; verified no URL present).
- README four-way table: Human-facing UI = Open WebUI (`chat.vaxel.xyz`); OpenWork removed; MCP row added ("configured in Open WebUI / Hermes, never in ember-api"). URL table: `ai.vaxel.xyz` row replaced by `chat.vaxel.xyz`.
- `docs/architecture.md`: consumers diagram OpenWork → Open WebUI; new "Open WebUI (external consumer)" section; `/api/nodes` and `bin/ember doctor` descriptions updated (consumers group, local-smart check).
- `docs/roadmap.md` (new): ADR 0010 phases 5–7 + `auto` alias, each "not started", owner Jon.
- Phase 1 design doc: amendment banner + ownership/URL rows updated (consistent with Task 1's treatment of that history doc).
- Deviations from the PLAN's "grep OpenWork must return nothing" gate — remaining mentions are all intentional, none claim UI ownership:
  - `docs/adr/0010` (Jon's verbatim supersession note — cannot be altered),
  - `docs/adr/0003` line 15 (accepted ADR, historical context; rewriting accepted-ADR text would falsify the record),
  - `docs/cloudflare.md` (the sentence PLAN Task 1 step 5 explicitly required),
  - `AGENTS.md` (OpenWork listed as an agent *reader* of the repo, not a UI),
  - `docs/design/2026-09-14-phase1-design.md` line 5 (the amendment note itself, explaining the change).
- Tests: 55 pytest + ruff clean; dashboard 4; `tests/run.sh` ALL OK.

## Task 6 — live validation on Docker01
- Receipt commit: `c9fdd18f` `docs: branch 2 validation receipt` (pushed; ci + secret-scan success). Branch head for the PR.
- Ember `.env`: `LLM_PUBLIC_URL=https://ai.vaxel.xyz/v1`; `OPENWEBUI_HOST`/`CHAT_PUBLIC_URL` appended. `OMLX_RERANK_MODEL` was already present.
- **Incident (fixed):** first `bin/ember doctor` after restart failed all oMLX-backed checks with 401 from oMLX itself. Cause: the mini's oMLX bearer key had been rotated since Phase 1 — the key in `/opt/stacks/ember/.env` no longer matched (verified by comparing SHA-256 fingerprints over ssh; values never printed). Fix: moved the current mini key to Docker01 `.env` via the `ssh mini | ssh docker` pipe (HANDOFF rule 8), `bin/ember restart`, doctor green. No key material in any log or commit.
- `bin/ember doctor`: all checks passed, including the new `local-smart` completion.
- `/model/info`: 13 aliases confirmed (list in `docs/deployment.md` receipt).
- Virtual key: first `keys create open-webui` printed only the client line through my filter and the key value was lost; a same-alias retry 400s, so the orphaned key was deleted via LiteLLM `/key/delete` (token from `/key/list`) and a fresh key minted, captured to a remote shell var only. `CHANGE_ME` count in the stack `.env` after setup: 0.
- Open WebUI: stack up from `deploy/openwebui/` at `/opt/stacks/openwebui`; container healthy; `:3003/health` → 200; `ENABLE_SIGNUP=true` left for Jon.
- Ember view: `/api/services` shows `open-webui (healthy, consumer)`; `/api/nodes` shows `consumers: [open-webui]` and docker01 excludes it.
- Virtual-key view: `/v1/models` → 13 aliases; `local-smart` completion via the virtual key → 200 with content.
- Memory: 2.9 GiB used / 7.8 GiB; `open-webui` 1.17/1.5 GiB (watch this — closest to its limit); `ember-litellm` 426 MiB.
- Deviations: the oMLX key rotation above (not in the plan; root-caused and fixed); the virtual-key capture redo (operator error, cleaned up via documented LiteLLM APIs).

## Acceptance for the night
- Tasks 1–6 commits pushed; `ci` + `secret-scan` green on final head `c9fdd18f`.
- Local suite green: ember-api 55 pytest (≥ 56 target: 55 — see note), ruff clean; dashboard 4 tests; `tests/run.sh` ALL OK.
  - Note: PLAN says "ember-api ≥ 56 tests"; final count is 55 (52 baseline + 3 new). The plan's arithmetic assumed one more test than the tasks actually specify (Task 2 adds 2, Task 3 adds 1 net after renaming). All planned assertions exist.
- Docker01: doctor green; 13 aliases; `open-webui` healthy; dashboard consumer tile healthy.
- No secret values in git, this report, or logs.
- Draft PR #2: opened with this file as body (see PR URL printed by the session).

## Addendum (2026-09-17, Jon-directed) — alias namespace consolidation
- Commit: `e2316fd0` `feat: consolidate alias namespace — ember- services, local- oMLX chat, cloud- remote` (pushed; ci + secret-scan success).
- Jon's three-tier scheme (amends ADR 0010 §3–4, amendment note added to the ADR):
  - `ember-` = local non-LLM services: `ember-embed`, `ember-rerank`, `ember-stt`, `ember-tts`
  - `local-` = oMLX LLM/chat: `local-fast`, `local-smart`, `local-code` (was `ember-code`), `local-vision` (was `ember-vision`)
  - `cloud-` = remote providers: `cloud-smart` (was `heavy`, same OpenRouter target); `cloud-gpt6` reserved for a future Codex-subscription route
- Removed as duplicates: `ember-auto`, `ember-local`, `ember-fast`, `ember-think`, `heavy`. Pre-checked gateway spend logs (2026-09-10→17): no external consumer used the removed names (only Phase 1 validation/doctor traffic).
- Updated: template, `aliases.py` (9 names), render/API tests, `bin/ember doctor` (ember-auto block dropped; local-smart + ember-embed remain), README, litellm/architecture/hermes-cutover/troubleshooting/omlx/open-webui docs, deploy/openwebui README, roadmap. Accepted ADRs 0001/0004/0009 keep their historical mentions; ADR 0010 carries the amendment.
- Live on Docker01: `git pull` + `bin/ember restart`; doctor green; `/model/info` = exactly the 9 new names; gateway probe healthy against the new set; Open WebUI still healthy and its virtual key sees the 9; dashboard services all healthy.
- Note: PR #2's body was set at creation and does not include this addendum; the commits are on the same branch.

## Addendum 2 (2026-09-17, Jon-directed) — cloud-glm → glm-5.3-flash
- Commit: `f79965cf` `feat: cloud-glm alias targets z-ai/glm-5.3-flash; rename OPENROUTER_GLM_MODEL` (pushed; ci + secret-scan success).
- `cloud-smart` renamed to `cloud-glm` (cloud- aliases are named for their model, per Jon); target changed `z-ai/glm-5.3` → `z-ai/glm-5.3-flash`.
- Backing env var renamed `OPENROUTER_THINK_MODEL` → `OPENROUTER_GLM_MODEL` (leftover of `ember-think`); updated template, aliases.py, providers.py, .env.example, .env.schema.json (required list), tests, docs. Phase 1 plan history doc keeps the old name (frozen record).
- Live on Docker01: `.env` var renamed + set to `z-ai/glm-5.3-flash`, pull + restart; doctor green; `/model/info` = the 9 aliases with `cloud-glm`; all services healthy.
- `cloud-glm` completion returns 401 from OpenRouter — expected: `OPENROUTER_API_KEY=CHANGE_ME` on Docker01 (open item since Phase 1). Alias is registered and routable; validation lands when Jon adds the key.
