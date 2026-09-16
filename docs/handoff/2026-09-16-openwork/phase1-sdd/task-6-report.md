# Task 6 Report: ember-api app, routers, poll loop, Dockerfile

## What was done

Implemented the `ember-api` FastAPI app per the brief, verbatim except for one disclosed
signature fix:

- `ember-api/tests/test_api.py` — copied from the brief's Step 1 exactly.
- `ember-api/ember_api/routers/__init__.py` — empty, as specified.
- `ember-api/ember_api/routers/services.py` — `GET /api/services`, `POST /api/services/refresh`,
  `GET /api/nodes`.
- `ember-api/ember_api/routers/models.py` — `GET /api/models`, `GET /api/capabilities`, the
  9-alias `ALIASES` table, `CAPABILITY_ENV` map.
- `ember-api/ember_api/routers/providers.py` — `GET /api/providers` (never echoes key values,
  only `bool(...)` presence flags and the non-secret `OPENROUTER_THINK_MODEL` name).
- `ember-api/ember_api/routers/config.py` — `GET /api/config/validate`, `REQUIRED_ENV`,
  `run_checks()`.
- `ember-api/ember_api/main.py` — `Registry` (poll loop via `asyncio.gather` + `asyncio.sleep`),
  `_lifespan` (creates `httpx.AsyncClient`, loads manifests, starts/cancels the poll task per
  `EMBER_POLL_ON_START`), `create_app()` (public `GET /api/health`, includes the four routers),
  module-level `app`.
- `ember-api/Dockerfile` — written exactly as specified. Not built or run — Docker is not
  installed on this Mac, per the task instructions.

## Deviations (disclosed)

1. **`_ui_url` signature** — the brief's `services.py` defines `_ui_url(svc, state_detail: dict)`
   but never uses `state_detail`, and the call site passes `{}`. Per the task instructions, I
   dropped the unused second parameter: `_ui_url(svc)`, and updated the call site to
   `"ui_url": _ui_url(svc)`. No behavioural change — confirmed by `test_services_and_nodes`
   still asserting `by_id["omlx"]["ui_url"] == "https://omlx.vaxel.xyz/docs"`.

2. **Ruff mechanical fixes** — the brief's literal code was not ruff-clean under this repo's
   effective rule set (all default categories enabled, no `select` override in `pyproject.toml`;
   confirmed pre-existing files like `security.py`/`settings.py` already comply with the same
   rules). Applied only mechanical fixes, mirroring conventions already present elsewhere in
   this codebase (e.g. `security.py`'s existing `# noqa: B008` pattern):
   - `ruff check --fix .` auto-fixed 2× `UP017` (`datetime.now(timezone.utc)` →
     `datetime.now(UTC)`) in `main.py` and `routers/services.py`.
   - `PIE810` in `routers/config.py`: merged three `base.startswith(...)` calls into one
     `base.startswith(("http://172.", "http://10.", "http://192.168."))`.
   - `B008` ×2 in `routers/models.py` (`models()`) and `routers/providers.py` (`providers()`):
     added `# noqa: B008` on the `Depends(get_settings)` default-argument lines, consistent with
     the existing suppression in `security.py`.
   No logic changed by any of these — only cosmetic/stylistic.

## Known design choices (not deviations, per task instructions)

- `Registry.poll_once` uses `asyncio.gather(...)` without `return_exceptions=True`. Kept as
  the brief specifies. This is safe because every per-service failure path (connect error,
  timeout, malformed JSON, non-2xx status) is already caught and turned into a `ServiceHealth`
  result inside `health.probe()` — so `gather` should never see an exception raised out of any
  of the coroutines it's awaiting, absent a bug in `probe`.
- `test_services_and_nodes` triggers a real TCP attempt to the unresolvable hostname
  `litellm-postgres:5432` (via `_probe_postgres` → `_tcp_open`), producing an `OSError` →
  `unreachable`. On this Mac this resolved fast — full suite runs in ~0.35–0.46s total — so no
  monkeypatch of `ember_api.health._tcp_open` was needed.

## TDD evidence

**RED** (before routers/main existed):
```
$ cd ember-api && python3 -m pytest tests/test_api.py -q
ImportError while importing test module '.../tests/test_api.py'.
...
E   ModuleNotFoundError: No module named 'ember_api.main'
=========== short test summary info ===========
ERROR tests/test_api.py
Interrupted: 1 error during collection
2 warnings, 1 error in 1.03s
```

**GREEN** (after routers/main/Dockerfile written, before ruff fixes):
```
$ cd ember-api && python3 -m pytest -q
.....................                                                    [100%]
21 passed, 2 warnings in 0.46s
```
(The 2 warnings are pre-existing `StarletteDeprecationWarning`/`DeprecationWarning` from the
`fastapi`/`starlette` dependencies themselves — confirmed present in an identical run against
only the pre-Task-6 files, so they predate and are unrelated to this task's code.)

**Ruff, before fixes:**
```
$ ruff check .
UP017 [*] Use `datetime.UTC` alias           (main.py:28, routers/services.py:35)
PIE810 Call `startswith` once with a `tuple` (routers/config.py:17)
B008 Do not perform function call `Depends` in argument defaults  (routers/models.py:31)
B008 Do not perform function call `Depends` in argument defaults  (routers/providers.py:12)
Found 5 errors.
```

**Ruff, after fixes:**
```
$ ruff check .
All checks passed!
```

**Final full run:**
```
$ cd ember-api && ruff check . && python3 -m pytest -q
All checks passed!
.....................                                                    [100%]
21 passed, 2 warnings in 0.35s
```
21 passed matches the expected count (15 pre-existing + 6 new: `test_health_is_public`,
`test_services_requires_key`, `test_services_and_nodes`, `test_capabilities_and_models`,
`test_providers_never_echo_keys`, `test_config_validate_reports_missing_alias_model`).

## Files changed

- `ember-api/tests/test_api.py` (new)
- `ember-api/ember_api/main.py` (new)
- `ember-api/ember_api/routers/__init__.py` (new)
- `ember-api/ember_api/routers/services.py` (new)
- `ember-api/ember_api/routers/models.py` (new)
- `ember-api/ember_api/routers/providers.py` (new)
- `ember-api/ember_api/routers/config.py` (new)
- `ember-api/Dockerfile` (new)

## Commit

`083dfdfb6` — `feat(ember-api): services/nodes/capabilities/models/providers/config routes and poll loop`
(exact message from the brief's Step 5), on branch `feature/ember-lean-rebuild`.

## Self-review

- Every route in the brief's Interfaces table exists with the exact JSON keys:
  `/api/health`, `/api/services`, `/api/services/refresh`, `/api/nodes`, `/api/capabilities`,
  `/api/models`, `/api/providers`, `/api/config/validate`. Verified against the actual manifests
  in `services/*/manifest.yaml` (omlx on `jons-mac-mini`; ember-api, ember-dashboard, litellm,
  litellm-postgres, qdrant on `docker01`) — matches the `test_services_and_nodes` node-set
  assertion `{"docker01", "jons-mac-mini"}`.
- `/api/health` is public (no `Depends(require_api_key)` — defined directly on `app`, outside
  the four routers, all of which carry `dependencies=[Depends(require_api_key)]`). Confirmed by
  `test_health_is_public` and `test_services_requires_key` (401 no header, 403 wrong token).
- `routers/providers.py` returns only `bool(...)` configured flags, `base_url`, and the
  non-secret model *name* string — never `settings.omlx_api_key` or `OPENROUTER_API_KEY` values.
  Confirmed by `test_providers_never_echo_keys` asserting `"omlx-k"` and `"or-key"` are absent
  from the full response body.
- `ALIASES` in `routers/models.py` is exactly the 9 brief aliases, in brief order: `ember-auto`,
  `ember-local`, `ember-fast`, `ember-code`, `ember-vision`, `ember-embed`, `ember-stt`,
  `ember-tts`, `ember-think`.
- Test output is pristine: `21 passed, 2 warnings` — the 2 warnings are pre-existing dependency
  deprecation notices unrelated to this task's code (verified identical on a baseline run).
- `ruff check .` is clean after mechanical-only fixes (all disclosed above).

## Concerns

- None blocking. The two pre-existing `DeprecationWarning`s from `fastapi.testclient` /
  `starlette.testclient` (recommending `httpx2`) are outside this task's scope — flagging for
  awareness only, not treating as a defect to fix here.
- Docker build/run was not exercised (no Docker on this Mac, per task instructions) — the
  Dockerfile is written and matches the brief exactly but is otherwise unverified.
