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
