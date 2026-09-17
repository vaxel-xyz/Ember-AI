# Ember-AI — instructions for AI coding agents

Personal homelab project (Vaxel) of Jon Howard-Totham. Public repository. Any agent (OpenWork, Claude Code, Codex) reads this file first.

## Read next
1. `docs/handoff/2026-09-16-openwork/HANDOFF.md` — current work, hard rules, how to work.
2. `docs/handoff/2026-09-16-openwork/STATE.md` — verified state of repo, hosts, live stack.
3. `docs/handoff/2026-09-16-openwork/CONTEXT.md` — environment facts, decisions, lessons.
4. `docs/design/` — Phase 1 design + plan (history); `docs/handoff/2026-09-16-openwork/SPEC.md` + `PLAN.md` — current branch.
5. `docs/adr/` — architecture decisions (0001–0011). ADR 0010 supersedes 0001 §1/§3; ADR 0011 adds the Codex-subscription provider.

## Conventions
- en-GB spelling in prose; conventional commits (`feat:`/`fix:`/`docs:`/`chore:`/`ci:`); one logical change per commit; never merge a PR yourself.
- Python 3.12 in `.venv` (`uv venv .venv && uv pip install -e './ember-api[dev]' jsonschema pyyaml`); `ruff` clean; pytest under `ember-api/tests`. Dashboard: Node 20.19+, `npm run lint && npm test && npm run build`. Whole suite: `bash tests/run.sh`.
- Health probes must be side-effect free (never LiteLLM `GET /health` on a timer). Aliases `ember-*` are stable API; add names, don't rename.
- Secrets only in gitignored `.env`; placeholders only in `*.example`; gitleaks runs in CI and pre-commit.
- Live hosts: `vaxel-docker` (Docker01) and `vaxel-mini` — read-only inspection is always fine; changes only where a plan says; never touch `/opt/stacks/n8n`, `/opt/stacks/portainer`, or Hermes.
- Design artefacts live in this repo (`docs/design/`, `docs/handoff/`), not outside it.
