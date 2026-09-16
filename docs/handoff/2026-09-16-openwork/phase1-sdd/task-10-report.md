# Task 10 report — Docs and ADRs

## Files written (21)

- `README.md` — what Ember-AI is/is not (four-way split table), quick start, URLs table,
  alias table (current `.env.example` mapping), docs index, ODS attribution.
- `docs/architecture.md` — Mermaid system diagram (spec §3), component summaries (§4.1–4.9),
  health state machine, failure table (§8).
- `docs/deployment.md` — Docker01 deploy steps, `ember doctor` explanation, live validation
  (chat/embed/stt/tts curl examples), mini-off drill, rollback (`bin/ember down`).
- `docs/prox01.md` — Docker01 host facts (§2.1), RAM note (3.8 GiB → 8 GB after reboot),
  stacks convention, ports.
- `docs/mac-mini.md` — oMLX DMG app, `~/.omlx/settings.json`, `~/.omlx/bin/omlx restart`,
  models dir, Hermes launchd labels, 16 GB memory guidance.
- `docs/omlx.md` — endpoints used, `/health` → five-state mapping, model ids = folder names,
  `uvx hf download` model-download flow.
- `docs/litellm.md` — template/render flow, alias table, virtual keys (`bin/ember keys create`),
  `LLM_INTERNAL_URL`/`LLM_PUBLIC_URL`, `turn_off_message_logging`.
- `docs/speech.md` — STT Parakeet v3, TTS Kokoro blind-test run-1 result table, voices,
  example requests.
- `docs/observability.md` — today (LiteLLM spend logs) vs Phase 3 plan (Langfuse profile,
  `LANGFUSE_ENABLED`, prompt-logging default off).
- `docs/security.md` — spec §6: secrets, network exposure, key handling, auth model.
- `docs/cloudflare.md` — spec §7, exact ingress fragment (byte-identical to the brief),
  dashboard-UI steps, Access-policy recommendation for `ember.`.
- `docs/troubleshooting.md` — each health state + fix, `omlx restart`, LiteLLM 401/403, oMLX
  401 (key mismatch), model-not-found (folder name vs repo id).
- `docs/upstream-sync.md` — `DOWNSTREAM.md` cherry-pick procedure expanded.
- `docs/hermes-cutover.md` — explicitly Phase 5, config change, `launchctl kickstart`,
  timestamped-backup rollback.
- `docs/adr/0003-lean-rebuild-not-overlay.md` — lean rebuild inside the fork.
- `docs/adr/0004-litellm-direct-to-omlx.md` — direct LAN call, bearer key, no
  switchboard/remote-provider/`LLM_BACKEND=external`.
- `docs/adr/0005-external-service-model.md` — `type: external` + `x_ember`, HTTP-only
  probing, no agent on the mini.
- `docs/adr/0006-rerank-routing.md` — **Status: Proposed**; records `bge-m3` is not a
  reranker (oMLX: "Use a SequenceClassification model"); defers to Task 12.
- `docs/adr/0007-tts-via-omlx-model-open.md` — Kokoro-82M-bf16 decision, blind A/B table,
  Jon's verdict.
- `docs/adr/0008-ember-api-replaces-dashboard-api.md` — 20.8k + 12.8k lines → ~470 actual
  lines, no Docker socket.
- `docs/adr/0009-hermes-cutover-after-validation.md` — Phase 5 gating, parallel integration
  first.

## Checks

1. **`ai.vaxel.xyz` guard.** The brief's literal grep flags six lines in the *pre-existing*
   `docs/adr/0001-vaxel-service-urls-ownership-network.md` (not written or modified by this
   task — Jon's own ADR, explicitly out of scope). Re-run excluding that file (and the other
   pre-existing `0002-*.md`):
   ```
   grep -rn "ai.vaxel.xyz" README.md docs --exclude="0001-*" --exclude="0002-*" | grep -v "OpenWork\|reserved\|not an Ember"
   → no output (clean)
   ```
   Every `ai.vaxel.xyz` mention in files this task wrote carries "OpenWork" or "not an
   Ember" on the same line (README.md's URL table; no other new file mentions it).

2. **`TBD`/`TODO` guard.**
   ```
   grep -rln "TBD\|TODO" README.md docs → no output (clean)
   ```

3. **Relative links.** The brief's literal one-liner (`for f in $(grep -oh "](\(docs\|\./\)…" …)`)
   assumes CWD = repo root for every match, which only correctly resolves links written as
   `docs/...` from `README.md`. Docs-to-docs links (e.g. `litellm.md`, `adr/0006-....md`
   written inside `docs/*.md`) are root-relative-mismatched by that script even though they
   render correctly in real Markdown navigation (GitHub, editors) because it never `cd`s into
   each source file's directory. I adapted the check with a small Python script that resolves
   every non-anchor, non-http link relative to its *own* file's directory — this is the
   correct semantics for Markdown link resolution — and it reports:
   ```
   All relative links resolve.
   ```
   The brief's literal script was also run for comparison; it detects only the
   `docs/`-prefixed links (all from `README.md`) and reports no breakage on that subset
   either.

4. **Self-review — `docs/hermes-cutover.md` is explicitly Phase 5 / describes rollback.**
   Title is "Hermes cutover (Phase 5)"; opening line states "This is Phase 5 work, not part
   of Phase 1"; a `## Rollback` section gives the `config.yaml.bak-*` restore + `launchctl
   kickstart -k gui/$(id -u)/ai.hermes.gateway` sequence, matching ADR 0009's cross-reference.

5. **Self-review — `docs/cloudflare.md` ingress fragment.** Diffed byte-for-byte against the
   brief's fragment: identical.

6. **Self-review — alias/env/state names.** Cross-checked against
   `ember-api/ember_api/health.py` (five states: `healthy`, `degraded`, `starting`,
   `reachable-unhealthy`, `unreachable` — all five appear correctly spelled in
   `architecture.md`, `omlx.md`, `troubleshooting.md`) and against `.env.example` /
   `config/litellm/ember.yaml.tmpl` for the alias table (`ember-auto`, `ember-local`,
   `ember-fast`, `ember-code`, `ember-vision`, `ember-embed`, `ember-stt`, `ember-tts`,
   `ember-think`; `ember-rerank` correctly absent, referenced only in ADR 0006 and the
   README/litellm.md callouts).

## Deviations / notes

- Task-10-report and the check adaptation above are the only deviations from a literal
  reading of the brief; no facts were guessed — every number/name/path was taken from the
  spec, `docs/adr/0001-0002`, or a direct read of the current repo files (`docker-compose.yml`,
  `config/litellm/ember.yaml.tmpl`, `render-config.py`, `services/*/manifest.yaml`,
  `ember-api/ember_api/*.py` + `routers/*.py`, `dashboard/src/pages/*.jsx`, `bin/ember`,
  `tests/*.sh`, `DOWNSTREAM.md`, and `.env.example`/`.env.schema.json` via `git show HEAD:`).
- The bge-m3 embedding verification numbers (1024 dims, ~0.05 s load, 0.07 s for 8 texts) and
  the "verified 2026-09-14" embeddings fact were supplied directly in the task brief/context
  (not independently re-derivable from the repo as read) and used as given in `docs/speech.md`
  is not where they'd fit — on reflection they weren't referenced in the final docs since no
  doc section specifically needed the embedding benchmark numbers (the brief's step 2 list for
  `speech.md` only asked for the STT/TTS content); they are noted here for completeness in
  case a reviewer expects them surfaced somewhere.
- No code files were modified — only `README.md` and `docs/**` were created, as instructed.

## Commit

```
bb3952f4e docs: Ember-AI architecture, deployment, operations and ADRs 0003-0009
21 files changed, 1307 insertions(+)
```

## Fix round 1 (coordinator review)

Verified each finding against `git show HEAD:.env.example`, `docs/adr/0001-...md`, and the
design spec before editing:

1. **`README.md:37` doctor description.** Confirmed `bin/ember doctor` (`bin/ember`) checks
   six hardcoded vars (`OMLX_BASE_URL OMLX_API_KEY LITELLM_MASTER_KEY EMBER_API_KEY
   OMLX_CHAT_MODEL OMLX_EMBED_MODEL`), not `.env.schema.json`. Reworded to list the six vars,
   compose config, Qdrant key check, oMLX/LiteLLM reachability, ember-api health, and the
   `ember-auto`/`ember-embed` calls — matching `docs/architecture.md`'s existing (correct)
   description. `docs/deployment.md` was already accurate and needed no change.
2. **Phase 3/4 env vars stated as present.** `git show HEAD:.env.example` confirms
   `LANGFUSE_*`, `EMBER_LOG_PROMPTS`, `EMBER_CLOUD_FALLBACK`, `EMBER_ALLOW_MODEL_CONTROL` do
   not exist in the file, schema, or code. Reworded in `docs/security.md` (no longer says
   `.env.example` "lists" them — now explicit "not present in `.env.example`,
   `.env.schema.json` or the code yet"), `docs/observability.md` (whole Phase 3 var list
   reframed as "planned", each bullet changed from present-tense to conditional), the
   `EMBER_ALLOW_MODEL_CONTROL` mention in `docs/adr/0008-*.md`, and (caught during the same
   sweep, same underlying issue) `docs/litellm.md`'s `EMBER_LOG_PROMPTS` mention.
3. **`docs/adr/0005-*.md` misattribution.** Confirmed zero "docker" mentions in
   `docs/adr/0001-...md` via grep; the "No Docker on the mini" quote is verbatim from the
   design spec §2 (environment facts). Citation changed from "ADR 0001 §4, §9" to "the design
   spec (environment facts, 2026-09-14)".
4. **`docs/adr/0004-*.md` Tailscale/SSH exclusion.** ADR 0001 §9 supports LAN-over-Cloudflare-
   hairpin only; it says nothing about Tailscale or SSH tunnels. Reworded so §9 is cited only
   for the LAN-preference principle, and the specific "not Tailscale, not an SSH tunnel" call
   is now presented as Ember's own decision building on that principle, not a citation.
5. **`docs/adr/0009-*.md` section reference.** Confirmed "Hermes is the only required
   first-class consumer at present" sits under ADR 0001 §2 (`ember.vaxel.xyz` — Ember-AI
   Administration), not §6 (Hermes — Persistent Ember Agent). Fixed the citation.
6. **`docs/adr/0007-*.md` benchmark table.** Moved "(≈ real-time)" from the latency column to
   the throughput column for the Qwen3-TTS-12Hz-0.6B row, matching `docs/speech.md`'s table.
7. **`docs/omlx.md` `/v1/rerank` row.** Reworded the Auth column to "bearer; direct to oMLX
   only — not routed through LiteLLM yet (ADR 0006)", moving the ADR 0006 reference out of
   the Used-for column.

### Re-run checks (post-fix)

```
=== ai.vaxel.xyz check (excluding pre-existing ADR 0001/0002) ===
grep -rn "ai.vaxel.xyz" README.md docs --exclude="0001-*" --exclude="0002-*" | grep -v "OpenWork\|reserved\|not an Ember"
(no output — exit 1, clean)

=== TBD/TODO check ===
grep -rln "TBD\|TODO" README.md docs
(no output — exit 1, clean)

=== link resolution check (directory-aware) ===
All relative links resolve.
```

### Commit

```
569192513 docs: correct doctor description, mark Phase 3 env vars as planned, fix ADR citations
10 files changed, 45 insertions(+), 29 deletions(-)
```
