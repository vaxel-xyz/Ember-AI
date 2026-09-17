## Summary

Lean rebuild of the ODS fork into Ember-AI's shared AI infrastructure layer: strips the donor's installer/switchboard/extension sprawl and replaces it with a single Compose stack (`litellm`, `litellm-postgres`, `ember-api`, `ember-dashboard`) that routes through LiteLLM to oMLX on `jons-mac-mini`, with OpenRouter as the cloud alias. `ember-api` (thin FastAPI, health/models/providers/usage) and `ember-dashboard` (React, 5-state health) replace the 20.8k-line `dashboard-api` and `ods-host-agent.py`. Live-validated end-to-end on Docker01 against the real mini: chat, embed, STT, TTS, and rerank all pass through LiteLLM, and a mini-off drill confirms the control plane stays up with `omlx` correctly reported `unreachable`. `ember-think` (OpenRouter) is wired but unvalidated — no key provisioned yet.

## Acceptance (spec §11)

- [x] 1. oMLX, Hermes, n8n untouched and functional — Task 12 receipt confirms n8n/Portainer stacks untouched; oMLX and Hermes run unmanaged on the mini, verified reachable throughout (`docs/deployment.md#validation-receipt-2026-09-14`).
- [x] 2. No duplicate n8n/Hermes/oMLX/OpenCode deployment — Ember ships only `litellm`, `litellm-postgres`, `ember-api`, `ember-dashboard` (+ profile-gated `qdrant`/`observability`); ADR 0005 (external service model) documents oMLX/Hermes as unmanaged externals.
- [x] 3. LiteLLM runs on the Docker VM independently of the mini — receipt: mini-off drill and raw capture (`docs/deployment.md`, "Mini-off drill" rows) show `litellm`/`ember-api`/`ember-dashboard` holding HTTP 200 for the full oMLX outage window.
- [x] 4. OpenAI-compatible request via `ember-auto` returns an oMLX completion; `ember-embed` returns vectors — receipt rows "Chat (`ember-auto` via LiteLLM)" (200, completion returned) and "Embed (`ember-embed` via LiteLLM)" (200, vector length 1024); CI `tests/run.sh` pytest suite covers the same paths against mocked oMLX/LiteLLM.
- [x] 5. Dashboard shows control-plane + inference-node services with real 5-state health; mini shutdown shows `unreachable`, dashboard stays up — receipt "Mini-off drill" row plus the new raw-capture table; dashboard served HTTP 200 throughout both the original drill and the controller's re-run.
- [x] 6. No secrets committed; gitleaks passes — CI secret-scan job; `.gitleaks.toml` allowlists only dead history (deleted paths) with the one known upstream LiveKit key/secret pair annotated per finding C1, not a live Ember credential (see "Rulings and follow-ups").
- [x] 7. `ember doctor` green on the target VM — receipt: "`bin/ember doctor` — All checks passed after one config fix"; also green in this dispatch's local `tests/run.sh` run (stubbed HTTP, since Docker isn't available in this environment).
- [x] 8. Docs + ADRs + `DOWNSTREAM.md` present; upstream divergence = "everything, by design", cherry-pick path documented — `docs/`, `docs/adr/0001`–`0009`, `DOWNSTREAM.md` all present and reviewed in this dispatch.
- [x] 9. Tests pass in CI — this dispatch's `bash tests/run.sh` ends `ALL OK` (manifests OK, compose test SKIP locally/real in CI, doctor OK, 21 pytest passed, 4 Vitest passed); CI on HEAD `c4aad464e` is green per the controller's prior run, re-confirmed on the final head `b44d98123` (`ci` + `secret-scan` green); local suite now 52 pytest + 4 Vitest.

## Final review and fix wave

The whole-branch review found the health poll calling LiteLLM `GET /health`, which runs a live inference call per deployment — it was evicting the mini's STT/TTS/embedding models every ~30 s. Fixed: the gateway probe is now readiness + `/model/info` (alias-set check), deep per-deployment checks are operator-only (`ember doctor`, direct bearer `POST /api/services/refresh?deep=true`), `model_info.mode` is set on non-chat aliases, the poll cycle tolerates probe exceptions (`return_exceptions`) and malformed bodies, `REQUIRED_ENV` is derived from the template, dashboard links are corrected, the nginx proxy is GET-only, and ODS residue/hygiene items are cleared. Re-validated on Docker01: gateway `healthy` 10/10 aliases, zero `/health` calls from the loop, mini idle.

## Open items for the reviewer

- `.env.schema.json` `required` still lacks `OMLX_RERANK_MODEL` (load-bearing in the template); blocked by a local `.env*` tooling guard — one-word hand edit.
- Mini-off drill was not re-run after the fix wave: an orphaned `omlx-server` (PID 66607, PPID 1) from an earlier `omlx start` makes `omlx stop` a no-op. Reap + re-drill when convenient; substitute cadence evidence is in the receipt.
- `ember-think` (OpenRouter) unvalidated until a key is provisioned.
- Follow-up ADR (frontend/routing/voice, 2026-09-16) changes the public hostname to `ai.vaxel.xyz/v1` and adds Open WebUI at `chat.vaxel.xyz`; handled on a separate branch.

## Rulings and follow-ups

- TTS model chosen by blind A/B between Kokoro-82M-bf16 and Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16 — Kokoro won on naturalness/clarity/prosody across all sentences; recorded in ADR 0007.
- Rerank routes through LiteLLM via the `jina_ai/${OMLX_RERANK_MODEL}` provider prefix against oMLX's Cohere/Jina-shaped `/v1/rerank`, matching direct-oMLX relevance scores on first attempt; no `cohere/` fallback needed. See ADR 0006.
- `encoding_format` fix: LiteLLM's OpenAI-compatible embeddings client was sending a value oMLX's strict backend rejected with HTTP 422; pinned to `"float"` in `ember-embed`'s `litellm_params` (commit `5225d722b`).
- Qdrant requires `QDRANT_API_KEY` at compose time even with the profile off; generated alongside the other Docker01 secrets.
- One known-inherited credential: a LiveKit API key/secret committed upstream (Osmantic ODS, `SECURITY_AUDIT.md` finding C1) lives only in dead git history under a deleted path. It is annotated in `.gitleaks.toml` and `DOWNSTREAM.md` rather than purged — rotation is the upstream account owner's call, and a history rewrite (`git filter-repo`) is a separate decision, not taken here.
- Phase 3 (Langfuse observability, per-client virtual keys via `ember keys`) is planned but not built in this branch.
- Hermes cutover (switching Hermes's `OPENAI_BASE_URL` to Ember) is intentionally out of scope — Phase 5, per ADR 0009 — and was not executed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
