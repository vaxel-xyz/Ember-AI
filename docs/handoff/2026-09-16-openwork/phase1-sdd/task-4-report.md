# Task 4 Report: ember-api scaffold, settings, security, manifest loader

## What was done

Created the `ember-api` Python package scaffold and the manifest-loader TDD cycle, per the brief:

- `ember-api/pyproject.toml` — verbatim from the brief (project metadata, deps, `[project.optional-dependencies].dev`, pytest/ruff config).
- `ember-api/ember_api/__init__.py` — `__version__ = "0.1.0"`, verbatim.
- `ember-api/tests/conftest.py` — `env` and `services_dir` fixtures (one mechanical deviation, see below).
- `ember-api/tests/test_manifests.py` — the four tests from the brief, verbatim.
- `ember-api/ember_api/settings.py` — `Settings` frozen dataclass + `_req` + `get_settings()`, verbatim.
- `ember-api/ember_api/security.py` — `require_api_key` FastAPI dependency using `HTTPBearer` + `secrets.compare_digest`, verbatim except two `# noqa: B008` comments (see below).
- `ember-api/ember_api/manifests.py` — `Service` frozen dataclass, `_service_from_manifest`, `load_manifests`, verbatim except the `Mapping` import source (see below).

## Deviations from the brief

1. **Environment: repo-root `.venv` was Python 3.10, but `pyproject.toml` requires `>=3.12` (verbatim from brief).** `uv pip install -e '.[dev]'` failed outright with "current Python version (3.10.20) does not satisfy Python>=3.12". Rather than weaken `requires-python` (an explicit verbatim value) or fork a second venv, I rebuilt the repo-root `.venv` in place with `uv venv --python 3.12 .venv` (uv downloaded CPython 3.12.13) and reinstalled. Rationale: `.venv/` is fully gitignored (root `.gitignore:85`) and disposable; the root-level code that previously ran under 3.10 (`config/litellm/render-config.py`, `scripts/validate-manifests.py`, task 3's `test_render_litellm.py`) has no 3.10-specific syntax, and I re-ran `test_render_litellm.py` under the new interpreter before touching anything else — still 2 passed. This was a genuine environment gap, not a spec ambiguity, so I fixed it rather than asking NEEDS_CONTEXT.
2. **`manifests.py`: `from typing import Mapping` → `from collections.abc import Mapping`.** Ruff (`UP035`, deprecated import for `target-version = "py312"`) flagged the brief's literal import. Pure import-source swap, no signature/behavior change — `load_manifests(services_dir: Path, env: Mapping[str, str])` still matches the brief's interface exactly.
3. **`security.py`: added `# noqa: B008` on the `Security(_scheme)` and `Depends(get_settings)` default-argument lines.** Ruff's flake8-bugbear flags function calls in argument defaults, but this is the required FastAPI dependency-injection idiom, not the mutable-default bug B008 targets. Chose inline `# noqa` over editing `pyproject.toml`'s `[tool.ruff]` table (which the brief also gives verbatim) — keeps the ruff config byte-for-byte as specified and confines the exception to the two lines it actually applies to. No change to `require_api_key`'s signature, so Tasks 5–6 are unaffected.
4. **`conftest.py`: removed unused `import os`.** The brief's fixture file imports `os` but never references it (only `Path` and the `env`/`services_dir` fixtures are used). Ruff `F401`. Removing it changes nothing about fixture behavior or names.

No dataclass field, function name, or default value was changed from the brief's Interfaces block.

## TDD evidence

### RED (manifests module missing)
```
$ source .venv/bin/activate && cd ember-api && python3 -m pytest tests/test_manifests.py -q
==================================== ERRORS ====================================
___________________ ERROR collecting tests/test_manifests.py ___________________
ImportError while importing test module '.../ember-api/tests/test_manifests.py'.
tests/test_manifests.py:1: in <module>
    from ember_api.manifests import load_manifests
E   ModuleNotFoundError: No module named 'ember_api.manifests'
=========================== short test summary info ============================
ERROR tests/test_manifests.py
1 error in 0.10s
```
(This was captured after `pyproject.toml`/`__init__.py`/`conftest.py`/`test_manifests.py` existed and `ember-api` was `pip install -e`'d, but before `settings.py`/`security.py`/`manifests.py` were written — the required RED per the brief's Step 2.)

### GREEN (after settings.py, security.py, manifests.py written)
```
$ source .venv/bin/activate && cd ember-api && python3 -m pytest -q
......                                                                   [100%]
6 passed in 0.16s
```
6 passed = the brief's expected count (2 render tests from Task 3 + 4 manifest tests from this task).

## Ruff

First run surfaced 4 issues, all in files created this task:
```
$ ruff check .
UP035  ember_api/manifests.py:3   — typing.Mapping deprecated, use collections.abc
B008   ember_api/security.py:12   — Security(_scheme) call in argument default
B008   ember_api/security.py:13   — Depends(get_settings) call in argument default
F401   tests/conftest.py:1        — `os` imported but unused
Found 4 errors.
```
After the fixes described above:
```
$ ruff check .
All checks passed!
```
Re-ran the full suite after the ruff fixes — still 6 passed (see final verification below).

## Final verification
```
$ source .venv/bin/activate && cd ember-api && python3 -m pytest -q
......                                                                   [100%]
6 passed in 0.11s

$ ruff check .
All checks passed!

$ git status --short
(empty)

$ git log --oneline -3
0f628c205 feat(ember-api): settings, bearer auth, manifest loader
114653a75 feat: LiteLLM ember.yaml template and renderer
adddc31cd feat: Ember service manifests with x_ember extension and validator
```

## Files changed

New (all in this commit, `0f628c205`):
- `ember-api/pyproject.toml`
- `ember-api/ember_api/__init__.py`
- `ember-api/ember_api/settings.py`
- `ember-api/ember_api/security.py`
- `ember-api/ember_api/manifests.py`
- `ember-api/tests/conftest.py`
- `ember-api/tests/test_manifests.py`

Also touched, not committed (gitignored, disposable): repo-root `.venv/` rebuilt from Python 3.10.20 → 3.12.13, with the same packages it previously held (pytest, pyyaml, jsonschema, etc.) plus `ember-api[dev]`'s new deps (fastapi, uvicorn, httpx, respx, ruff, pytest-asyncio).

Commit: `0f628c205` — "feat(ember-api): settings, bearer auth, manifest loader" (exact message from the brief).

## Self-review

- `Service` fields: `id, name, host, port, external_port, health_path, health_timeout, type, category, ui_path, external_link, public_url, node, role, managed, capabilities: list[str], health_probe` — matches the Interfaces block field list and order exactly.
- `Settings` fields: `ember_api_key, services_dir, omlx_base_url, omlx_api_key, litellm_base_url, litellm_master_key, llm_public_url, llm_internal_url, poll_interval_s` — matches exactly. `get_settings() -> Settings` is `@lru_cache`d (env-driven, cached) as specified.
- `public_url` semantics verified two ways: `test_host_env_overrides_default_host` (env var `OMLX_PUBLIC_URL` set → `public_url == "https://omlx.vaxel.xyz"`) and `test_defaults_when_env_missing` (env `{}` → `public_url is None`). The `env.get(pub_env) or None` expression also collapses an explicitly-empty-string env value to `None`, matching the self-review requirement in the task message (not directly exercised by the brief's tests, but consistent with the `or None` logic).
- `host_env` override verified by `test_host_env_overrides_default_host` (`OMLX_HOST=10.0.0.5` → `omlx.host == "10.0.0.5"`); default-host fallback verified by `test_defaults_when_env_missing` (`omlx.host == "172.20.142.184"` with empty env).
- `external_port` fallback verified by `test_docker_service_shape` (`litellm`: no `LITELLM_PORT` in the `env` fixture → falls back to `external_port_default: 4000`).
- No broad `except` anywhere in `ember_api/*.py` (confirmed via `grep -n "except" ember_api/*.py` → no matches — `load_manifests` lets `KeyError`/`ValueError` propagate naturally, `_req` raises `RuntimeError` explicitly).
- Type hints present throughout: every function parameter and return type is annotated in `settings.py`, `security.py`, `manifests.py`.
- `ruff check .` clean (see above).
- `git status --short` clean after commit; `.venv/` not committed (confirmed absent from `git status` output both before and after commit; root `.gitignore` covers both `.venv/` and `ember-api/.venv/`).

## Concerns

- The repo-root `.venv` Python version bump (3.10 → 3.12) is an environment change, not a code change, but it's worth downstream tasks (5–13) knowing about: any task that assumes a 3.10 interpreter for root-level tooling should re-check against 3.12. I verified the one existing consumer (`test_render_litellm.py`) still passes; I did not exhaustively test `scripts/validate-manifests.py` end-to-end (only inspected it for 3.10-specific syntax, of which there was none).
- `ember-api/.gitignore`-listed `ember-api/.venv/` path was never used — I kept everything on the single repo-root venv per the R3 instruction, rather than creating a second per-package venv. If a future task expects a dedicated `ember-api/.venv`, that will need to be created separately; nothing here precludes it.
- The two `# noqa: B008` comments in `security.py` are the only non-blank-line addition to that file beyond the brief's verbatim code. If a reviewer prefers the `extend-immutable-calls` route in `pyproject.toml`'s ruff config instead, that's a trivial follow-up and won't change `require_api_key`'s public signature either way.
