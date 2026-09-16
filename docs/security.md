# Security

## Secrets

No secrets are committed to git. `.env.example` lists every variable the Phase 1 stack needs,
including: `OMLX_HOST`, `OMLX_BASE_URL`, `OMLX_API_KEY`, `OMLX_*_MODEL`,
`OPENROUTER_API_KEY`, `LITELLM_MASTER_KEY`, `LITELLM_DB_PASSWORD`, `EMBER_API_KEY`,
`QDRANT_API_KEY` and `LITELLM_TURN_OFF_MESSAGE_LOGGING`. `LANGFUSE_*`, `EMBER_LOG_PROMPTS`,
`EMBER_CLOUD_FALLBACK` and `EMBER_ALLOW_MODEL_CONTROL` are planned for later phases
(observability, cloud fallback, gated model control) and are **not present in
`.env.example`, `.env.schema.json` or the code yet** — verify with `git show
HEAD:.env.example` before assuming otherwise. A `gitleaks` pre-commit hook
(`.gitleaks.toml`, `.pre-commit-config.yaml`) runs on every commit against the full default
ruleset (`[extend] useDefault = true`); `.env.example`'s placeholder values simply don't match
any detector, so they pass without needing an allowlist entry. The only path allowlist in
`.gitleaks.toml` is the annotated, inherited LiveKit key/secret pair — a real upstream
disclosure in dead history, not a false positive.

## Network exposure

All control-plane ports bind to `${BIND_ADDRESS}` (default `0.0.0.0` on Docker01's LAN
interface, kept off the public internet — the Cloudflare tunnel on the Proxmox host is the
only public path in). Public exposure is Cloudflare-only:

- `llm.vaxel.xyz` → `litellm:4000` — required, this is the public gateway.
- `ember.vaxel.xyz` → `ember-dashboard:3001` — optional, recommended behind Cloudflare Access.
- `ember-api`, `litellm-postgres` and Qdrant are never public.

See [`docs/cloudflare.md`](cloudflare.md) for the exact ingress configuration.

## Keys

- Each consumer gets its own LiteLLM virtual key (`bin/ember keys create <client>
  [--budget USD]`), optionally rate/budget-limited. The LiteLLM master key is never
  distributed to consumers.
- `EMBER_API_KEY` is a single bearer key that guards every `ember-api` route (`Depends
  (require_api_key)` on every router in `ember-api/ember_api/routers/`); the dashboard holds
  it, consumers of `ember-api` routes do not get their own keys in Phase 1.
- The oMLX key (`OMLX_API_KEY`) lives only in `.env` on the Docker VM — LiteLLM injects it
  into `api_key: os.environ/OMLX_API_KEY` when calling oMLX. Consumers calling through
  LiteLLM never see it.
- `QDRANT_API_KEY` must be a real value even when the `qdrant` profile is unused — compose
  interpolates the whole file, so a `CHANGE_ME` placeholder here still exists in the
  rendered environment, and `bin/ember doctor` fails deliberately if Qdrant is ever running
  with it unset or left at `CHANGE_ME`.

## Auth model

`ember-api` implements a single shared-secret bearer scheme (`ember-api/ember_api/security.py`,
`secrets.compare_digest`) — there is no per-user auth, no magic-link flow, no session store.
The dashboard is expected to sit behind LAN access or Cloudflare Access; Ember does not
implement its own user authentication.
