# Ember-AI — Overnight handoff to OpenWork (2026-09-16)

You are continuing a build that Claude Code ran with Jon Howard-Totham on 14–16 Sep 2026. Read this file fully, then `STATE.md`, then `SPEC.md`, then execute `PLAN.md` task by task. Everything you need is in this folder or in the repo.

## What this is
Ember-AI = Vaxel's (Jon's personal homelab) shared AI infrastructure: a LiteLLM gateway on the Prox01 Docker VM ("Docker01") routing logical aliases to oMLX on a Mac mini and to OpenRouter, plus a thin FastAPI `ember-api`, a React admin dashboard, and a small `bin/ember` CLI. Phase 1 is complete, live on Docker01, and sits in **PR #1** (https://github.com/vaxel-xyz/Ember-AI/pull/1) awaiting Jon's review — do not merge it.

Your job tonight = **branch 2**: apply Jon's "ADR: Ember Frontend, Routing and Voice Architecture" (2026-09-16) to Ember. Scope is exactly `SPEC.md`; the steps are `PLAN.md`.

## Files in this folder
| File | Purpose |
|---|---|
| `HANDOFF.md` | this — rules, context, how to work |
| `STATE.md` | verified state of repo, hosts, live stack, pending human items |
| `SPEC.md` | branch-2 design (binding) |
| `PLAN.md` | branch-2 tasks with exact code, tests, commands, acceptance |
| `adr-0010-source.md` | Jon's ADR text, sanitised for the PUBLIC repo — copy verbatim into `docs/adr/0010-frontend-routing-voice.md` |
| `SPEC-phase1-reference.md` | Phase 1 design spec (background only) |
| `phase1-ledger.md` | Phase 1 build ledger: every ruling, deferred minor, and why |

## Hard rules (Jon's, not negotiable)
1. **Repo is PUBLIC.** No secrets, no keys, no remote-access URLs (in particular never the Home Assistant Nabu Casa URL). Placeholders only in any `*.example`. gitleaks runs in CI.
2. **Never touch:** the n8n or Portainer stacks on Docker01; Hermes on the mini (`~/.hermes`); oMLX model files. Do not rewrite git history. Do not merge any PR.
3. **oMLX restarts** (`~/.omlx/bin/omlx restart`) are permitted if needed; prefer not to.
4. **Aliases `ember-*` are immutable** (Hermes cutover doc and ember-api depend on them). You ADD `local-fast`, `local-smart`, `heavy`; you do not rename.
5. **Open WebUI runs as a SEPARATE stack** at `/opt/stacks/openwebui` on Docker01 — not inside the Ember compose file. Ember only gets a manifest tile + a reference compose under `deploy/openwebui/`.
6. **Never poll LiteLLM `GET /health`** from anything periodic — it runs real inference per deployment and thrashed the mini once already. Gateway health = `/health/readiness` + `/model/info`.
7. **Do not add MCP, chat, or conversation code to `ember-api`.** MCP lives in Open WebUI/Hermes config (later phase).
8. **Secrets handling:** generate with `openssl rand -hex 24` on the host; move the oMLX key only via `ssh mini … | ssh docker …` pipelines; never echo a key into a log, report, or commit.
9. **Local tooling note:** Jon's Claude Code permission rules block any path matching `.env*` on the laptop. If your harness has the same guard, edit `.env.example`/`.env.schema.json` only via a small `python3` script, and never create a file literally named `.env` locally. On Docker01 (`ssh`) there is no such guard.
10. **Stop and leave a note** (in `REPORT.md` in this folder) rather than improvise if: tests fail after two attempts, the live stack fails to come up, doctor fails on chat/embed, or a step would require a credential you don't have.

## How to work
- Base branch: `feature/ember-lean-rebuild` (PR #1's head, `b44d98123`). Create `feature/frontend-routing-adr` from it. Open PR #2 as a **draft** against `main` when done, body noting it stacks on #1.
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`), one logical change per commit, no policy commentary, en-GB spelling in prose.
- TDD where the plan gives tests: write the test, see it fail, implement, see it pass.
- Python: `source .venv/bin/activate` at repo root (Python 3.12; `uv pip install -e './ember-api[dev]' jsonschema pyyaml` if the venv is missing). Run `cd ember-api && python3 -m pytest -q && ruff check .`. Dashboard: `cd dashboard && npm ci && npm run lint && npm test && npm run build`. Whole suite: `bash tests/run.sh` (compose test SKIPs without Docker locally; CI runs it for real).
- Push after each task; CI = `.github/workflows/ci.yml` + `secret-scan.yml`; watch with `gh run watch --exit-status`. Fix root causes; never weaken a gate (`|| true`, `continue-on-error`, deleted assertions).
- Live hosts (SSH aliases in Jon's `~/.ssh/config`, key `~/.ssh/id_ed25519_vaxel`, non-interactive): `vaxel-docker` = root@172.20.142.7; `vaxel-mini` = jtotham@172.20.142.184. Read-only inspection is always fine; changes only where `PLAN.md` says.
- Write `REPORT.md` in this folder as you go: per task → commit SHAs, test output tail, live evidence (redacted), deviations, open questions. Jon reads only that file in the morning.

## Where the human is needed (do not block on these)
- Cloudflare hostnames on the Proxmox-host tunnel: `ai.vaxel.xyz → http://172.20.142.7:4000`, `chat.vaxel.xyz → http://172.20.142.7:3003`, `ember.vaxel.xyz → http://172.20.142.7:3001`. Until then LAN URLs work.
- OpenRouter API key into `/opt/stacks/ember/.env` (`OPENROUTER_API_KEY`) → validates `heavy`/`ember-think`. If absent, skip those checks and say so.
- First Open WebUI admin sign-up at `chat.vaxel.xyz` (or `http://172.20.142.7:3003`), then set `ENABLE_SIGNUP=false` and restart. You may create the stack and leave signup enabled for Jon.
- Orphan `omlx-server` PID 66607 on the mini (from an earlier drill) — leave it; it works.
