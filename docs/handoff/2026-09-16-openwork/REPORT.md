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
