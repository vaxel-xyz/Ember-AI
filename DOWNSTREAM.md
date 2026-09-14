# Downstream record — Ember-AI

Upstream: https://github.com/Osmantic/ODS — last synced ref `v2.6.0` / `21f4b3a64` (2026-09-14).

## Posture
ODS is a donor/reference implementation. Ember-AI is a lean rebuild inside the fork: git history and the
`upstream` remote are retained for cherry-picks; the ODS runtime (installer, ods-cli, host agent, compose
overlays, 27 services) is deleted rather than overlaid.

## Retained from ODS
- `services/schema/service-manifest.v1.json` — manifest schema (extended with `x_ember`, `type: external`).
- `dashboard/` — React/Vite/Tailwind scaffold, theme context, sidebar pattern, nginx + entrypoint auth injection.
- `docs/donor/litellm-compose.yaml`, `docs/donor/langfuse-compose.yaml` — reference compose fragments.
- `.gitleaks.toml`, `.pre-commit-config.yaml` — secret scanning.
- `LICENSE` (Apache-2.0, Osmantic) + `NOTICE`.

## Removed (by design, 2026-09-14)
installer + phases, `ods-cli`, host agent, model switchboard/router, remote-provider egress/ssh tunnel,
llama-server, Open WebUI, Hermes/hermes-proxy, n8n, APE, OpenClaw, SearXNG, Perplexica, brave-search, ComfyUI,
TEI embeddings, Whisper, Kokoro containers, privacy-shield, token-spy, ods-proxy, Tailscale, OpenCode,
extension library/templates, Tauri installer, all ODS docs, `.github/` (issue templates, dependabot config,
AI-automation prompts/scripts — Task 11 recreates `.github/workflows/` from scratch).

## Cherry-pick procedure
`git fetch upstream && git log upstream/main -- <path>`; apply with `git cherry-pick -x <sha>` or copy the
file into the matching donor location; record the sha here.
