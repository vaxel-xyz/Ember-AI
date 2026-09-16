### Task 1: Strip ODS to the donor set

**Files:**
- Delete: everything listed in Step 1.
- Move: `ods/extensions/schema/service-manifest.v1.json` → `services/schema/service-manifest.v1.json`; `ods/extensions/services/dashboard/` → `dashboard/`; `ods/extensions/services/litellm/compose.yaml` → `docs/donor/litellm-compose.yaml` (reference only); `ods/extensions/services/langfuse/compose.yaml.disabled` → `docs/donor/langfuse-compose.yaml`; `ods/.env.schema.json` → `.env.schema.json` (rewritten in Task 8); `LICENSE` stays; `.gitleaks.toml`, `.pre-commit-config.yaml`, `.gitignore` stay (edited).
- Create: `DOWNSTREAM.md`, `NOTICE`

**Interfaces:**
- Produces: repo root with only donor files + `dashboard/` + `services/schema/`.

- [ ] **Step 1: Delete ODS**

```bash
cd /Users/jtotham/Projects/Ember-AI
mkdir -p services/schema docs/donor
git mv ods/extensions/schema/service-manifest.v1.json services/schema/service-manifest.v1.json
git mv ods/extensions/services/dashboard dashboard
git mv ods/extensions/services/litellm/compose.yaml docs/donor/litellm-compose.yaml
git mv ods/extensions/services/langfuse/compose.yaml.disabled docs/donor/langfuse-compose.yaml
git mv ods/.env.schema.json .env.schema.json
git rm -r -q ods installer install.sh install.ps1 ARCHITECTURE.md CLAUDE.md CONTRIBUTING.md CONTRIBUTORS.md SECURITY.md SECURITY_AUDIT.md .claude .gitleaksignore .github/workflows
git rm -q README.md
rm -rf dashboard/manifest.yaml dashboard/compose.local.yaml
git add -A
```

- [ ] **Step 2: Write DOWNSTREAM.md and NOTICE**

`DOWNSTREAM.md`:

```markdown
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
extension library/templates, Tauri installer, all ODS docs.

## Cherry-pick procedure
`git fetch upstream && git log upstream/main -- <path>`; apply with `git cherry-pick -x <sha>` or copy the
file into the matching donor location; record the sha here.
```

`NOTICE`:

```text
Ember-AI
Copyright 2026 Vaxel (Jon Howard-Totham)

This product includes software developed by Osmantic (ODS, https://github.com/Osmantic/ODS),
licensed under the Apache License, Version 2.0. See LICENSE.
```

- [ ] **Step 3: Tighten .gitignore and gitleaks allowlist**

Append to `.gitignore`:

```gitignore
.env
.env.*
!.env.example
ember-api/.venv/
ember-api/**/__pycache__/
dashboard/node_modules/
dashboard/dist/
tests/.tmp/
```

Replace the `[allowlist]` block in `.gitleaks.toml` with:

```toml
[allowlist]
  description = "Placeholder templates only"
  paths = [ '''\.env\.example$''' ]
```

- [ ] **Step 4: Verify tree and commit**

Run: `git status --short | wc -l && ls`
Expected: only `DOWNSTREAM.md LICENSE NOTICE dashboard docs services .env.schema.json .gitignore .gitleaks.toml .pre-commit-config.yaml .gitattributes .git`.

```bash
git add -A
git commit -m "chore: strip ODS runtime to Ember donor set (see DOWNSTREAM.md)"
```

---

