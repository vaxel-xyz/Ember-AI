# Task 5 Report: Health state machine and probes

## What was done

Implemented the five-state health machine and probes exactly per the brief:

- `ember-api/ember_api/omlx.py` — `OmlxClient(base_url, api_key, client)` with `health()`, `models_status()`, `voices()`.
- `ember-api/ember_api/litellm_client.py` — `LiteLLMClient(base_url, master_key, client)` with `readiness()`, `deployment_health()`, `model_info()`.
- `ember-api/ember_api/health.py` — `State` literal (`healthy`, `degraded`, `starting`, `reachable-unhealthy`, `unreachable`), `ServiceHealth` dataclass, module-level `_tcp_open` coroutine, `_url`, `_probe_http`, `_probe_omlx`, `_probe_litellm`, `_probe_postgres`, and the dispatching `probe(service, client, settings)`.
- `ember-api/tests/test_health.py` — the 7 tests from the brief (respx-mocked oMLX healthy/degraded/starting/unreachable, generic HTTP 500 reachable-unhealthy, LiteLLM degraded-on-unhealthy-deployment, Postgres TCP probe via monkeypatched `_tcp_open`).

Verified against the live manifest fixtures in `services/omlx`, `services/ember-dashboard`, `services/litellm`, `services/litellm-postgres` — hosts/ports/`health_probe` values (`omlx`, `http`, `litellm`, `postgres`) line up with what the tests expect (e.g. `omlx` resolves `OMLX_HOST=10.0.0.5` + port `8000` via the `env` fixture).

## Deviations

Two mechanical ruff fixes, no behaviour or signature changes:

1. `ember_api/health.py`: `except (OSError, asyncio.TimeoutError):` → `except (TimeoutError, OSError):` (ruff `UP041` — `asyncio.TimeoutError` is an alias for the builtin `TimeoutError` on Python 3.11+; same exception classes caught).
2. `tests/test_health.py`: `import ember_api.health as health` → `from ember_api import health` (ruff `PLR0402` — same module object bound to the same name `health`; `monkeypatch.setattr(health, "_tcp_open", fake_tcp)` still patches the module's global namespace that `_probe_postgres` reads from).

No other deviations from the brief — client and health-machine code, and all seven test bodies, were written verbatim as specified.

## TDD RED/GREEN evidence

RED (before writing implementation, only `tests/test_health.py` added):

```
$ cd ember-api && python3 -m pytest tests/test_health.py -q
==================================== ERRORS ====================================
____________________ ERROR collecting tests/test_health.py _____________________
ImportError while importing test module '.../ember-api/tests/test_health.py'.
tests/test_health.py:5: in <module>
    from ember_api.health import probe
E   ModuleNotFoundError: No module named 'ember_api.health'
=========================== short test summary info ============================
ERROR tests/test_health.py
1 error in 0.13s
```

GREEN (after adding `omlx.py`, `litellm_client.py`, `health.py`):

```
$ cd ember-api && python3 -m pytest -q
.............                                                            [100%]
13 passed in 0.13s
```

Confirmed no hidden warnings by re-running with warnings promoted to errors and with `-rw`:

```
$ python3 -m pytest -q -W error::DeprecationWarning
.............                                                            [100%]
13 passed in 0.12s

$ python3 -m pytest -q -rw
.............                                                            [100%]
13 passed in 0.11s
```

No pytest-asyncio deprecation warning was emitted (the project's `pyproject.toml` already sets `asyncio_mode = "auto"`, and no default-loop-scope warning appeared under either run), so `asyncio_default_fixture_loop_scope` was **not** added — output was already pristine without it.

## Ruff

Before mechanical fixes:

```
$ ruff check .
UP041 Replace aliased errors with `TimeoutError`  (ember_api/health.py:28)
PLR0402 Use `from ember_api import health` in lieu of alias  (tests/test_health.py:74)
Found 2 errors.
```

After the two mechanical fixes above:

```
$ ruff check .
All checks passed!
```

## Files changed

- `ember-api/ember_api/health.py` (new)
- `ember-api/ember_api/omlx.py` (new)
- `ember-api/ember_api/litellm_client.py` (new)
- `ember-api/tests/test_health.py` (new)

## Commit

```
fbbdb8a89 feat(ember-api): five-state health probes for oMLX, LiteLLM, Postgres, HTTP
```

## Self-review

- All five `State` values reached by a test: `healthy` (omlx loaded model, postgres tcp-open), `degraded` (omlx no model loaded, litellm unhealthy deployment), `starting` (omlx 503 loading), `reachable-unhealthy` (generic HTTP 500), `unreachable` (omlx connect error). `State` literal names match the brief exactly.
- Exceptions caught in the three HTTP-probe functions (`_probe_http`, `_probe_omlx`, `_probe_litellm`) are `httpx.ConnectError`, `httpx.TimeoutException`, `httpx.HTTPError` only — no bare/broad `except`. `_tcp_open` (raw socket, not httpx) catches `TimeoutError`/`OSError`, which is correct for `asyncio.open_connection`/`asyncio.wait_for`.
- `_tcp_open` is a module-level `async def` in `ember_api/health.py`; `_probe_postgres` calls it via the module global namespace, so `monkeypatch.setattr(health, "_tcp_open", fake_tcp)` in the test correctly substitutes it — verified by the passing `test_postgres_probe_uses_tcp`.
- Test output is pristine: 13 passed, 0 warnings (checked with `-W error::DeprecationWarning` and `-rw`).
- `ruff check .` clean after two disclosed mechanical fixes.

## Concerns

- None blocking. One thing worth flagging for Task 6 (which the brief says will call `probe`/`models_status`): `OmlxClient.models_status()` and `LiteLLMClient.model_info()` are implemented but not exercised by any test in this task — they're plumbing for Task 6, consistent with the brief's interface list, but currently have zero test coverage. Task 6 should add coverage when it starts consuming them.
- `Settings(services_dir=None)` in the test module is constructed as specified in the brief even though the dataclass field is typed `Path` — this is intentional per the task instructions (no runtime validation) and not a bug.

---

## Fix round 1 (review finding: unhandled JSONDecodeError)

### What changed

Review flagged that `r.json()` in `_probe_omlx` (health.py) and `deployment_health()` → `r.json()` in `_probe_litellm` raise `json.JSONDecodeError` (a `ValueError`) on an empty/malformed body even when `content-type` claims JSON — uncaught, this crashes the probe and, per Task 6's `asyncio.gather` without `return_exceptions`, would take out every service's health in one bad response.

Applied controller ruling R7:

1. `ember_api/health.py::_probe_omlx` — wrapped the JSON parse in `try/except ValueError`, returning `ServiceHealth(service.id, "reachable-unhealthy", f"HTTP {r.status_code}, invalid JSON body", ms)` on failure.
2. `ember_api/health.py::_probe_litellm` — extended the `deployment_health()` except clause from `except httpx.HTTPError as exc` to `except (httpx.HTTPError, ValueError) as exc`, keeping the existing `degraded` mapping and reason format (`f"readiness ok, /health failed: {exc.__class__.__name__}"`, which now also renders as `"...failed: JSONDecodeError"` for malformed bodies).
3. Added two tests to `tests/test_health.py`:
   - `test_omlx_invalid_json_body_is_reachable_unhealthy` — oMLX `/health` returns `200` with `content=b"not json"` and `content-type: application/json` → asserts `state == "reachable-unhealthy"` and `"invalid JSON body" in reason`.
   - `test_litellm_invalid_json_body_is_degraded` — LiteLLM readiness `200`, then `/health` returns the same malformed body → asserts `state == "degraded"` and `"JSONDecodeError" in reason`.

Only `ValueError` (base of `json.JSONDecodeError`) is caught in both spots — no broad `except`.

### Commands + output

```
$ cd ember-api && python3 -m pytest tests/test_health.py -q
.........                                                                [100%]
9 passed in 0.13s

$ python3 -m pytest -q -rw
...............                                                          [100%]
15 passed in 0.14s

$ ruff check .
All checks passed!
```

### Files changed (this round)

- `ember-api/ember_api/health.py` (modified — 2 except-clause changes)
- `ember-api/tests/test_health.py` (modified — 2 new tests appended)

### Commit

```
ef38f9896 fix(ember-api): tolerate malformed JSON bodies in oMLX/LiteLLM probes
```
