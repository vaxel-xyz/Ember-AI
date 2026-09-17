# ADR 0011: Codex Subscription as a Cloud Provider (cloud-gpt6)

**Status:** Accepted
**Date:** 2026-09-17
**Project:** `vaxel-xyz/Ember-AI`
**Author:** Jon Howard-Totham (directed in session); text prepared by the OpenWork agent.

## Context

Ember's `cloud-` tier (ADR 0010, as amended) routes remote inference through OpenRouter on
platform API billing. Jon also holds a ChatGPT subscription with Codex access, whose quota is
included in the subscription rather than billed per token. GPT-6-class models are available
through that subscription via the same Responses-style backend the Codex CLI uses
(`chatgpt.com/backend-api/codex`), authenticated by ChatGPT OAuth — not by an OpenAI platform
key.

The subscription path has no first-party OpenAI-compatible API. Community bridges exist; the
selected one is [`thezillo/codex-proxy`](https://github.com/thezillo/codex-proxy) (Apache-2.0,
Rust, single static binary, ~3 MiB resident, pinned container image): OpenAI-compatible
`/v1/chat/completions` + `/v1/responses`, automatic OAuth token refresh, client API keys,
unauthenticated `/health` for probes, per-request usage logs.

## Decision

1. **`codex-proxy` runs on Docker01 as a separate stack** at `/opt/stacks/codex-proxy`
   (reference deployment in `deploy/codex-proxy/`), port 8787, LAN-only — no Cloudflare
   hostname, mirroring the external-service model of ADR 0005 and the Open WebUI precedent.
2. **Ember consumes it as an ordinary OpenAI-compatible provider.** One new alias,
   `cloud-gpt6`, routes `openai/${CODEX_GPT6_MODEL}` (default `gpt-6`) at
   `${CODEX_BASE_URL}/v1` with the proxy client key (`CODEX_PROXY_KEY`). `ember-*`, `local-*`
   and the other `cloud-*` aliases are untouched.
3. **Auth model:** the ChatGPT OAuth `auth.json` is seeded once from a machine with a
   logged-in Codex CLI (the mini), transferred over an ssh pipe, never logged or committed.
   After seeding, the Docker01 `data/` directory is the **canonical, token-rotating**
   credential store. Exactly **one** proxy instance may share it; the mini's copy goes stale
   and must not be used concurrently by the Codex CLI.
4. **Monitoring:** `services/codex-proxy/manifest.yaml` adds an external, unmanaged tile
   (`role: inference`, node docker01, probed at `/health`) so `cloud-gpt6` outages are visible
   on the dashboard. No MCP/chat/conversation code is added to ember-api.
5. **Voice is out of scope:** the subscription covers the text Responses API only. OpenAI
   audio (TTS/STT/Realtime) remains platform-API-billed; `ember-stt`/`ember-tts` stay on oMLX
   (ADR 0002/0007).

## Consequences

- **ToS risk (accepted by Jon):** the bridge uses OpenAI's unofficial ChatGPT backend. Worst
  case is the account being flagged or rate-limited; nothing irreplaceable should depend
  solely on `cloud-gpt6`.
- **Quota ceiling:** Codex subscription usage caps now bound everything routed to
  `cloud-gpt6`. The proxy's per-account cooldown and (optional) fallback providers mitigate
  429s; Ember-side, `cloud-glm`/`cloud-fast` remain the independent cloud paths.
- **Breakage risk:** the unofficial backend can change without notice; the pinned proxy
  version is upgraded deliberately, not automatically.
- **Secrets hygiene:** the OAuth tokens and the client key live only in host files
  (`/opt/stacks/codex-proxy/data/auth.json`, the two stacks' `.env`) — never in git, logs, or
  reports. The public repo carries placeholders only.
