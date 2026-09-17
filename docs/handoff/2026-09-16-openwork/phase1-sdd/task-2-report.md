# Task 2 Report: Manifest schema, service manifests, validator

## What I implemented

Followed the brief's 5 steps in order, TDD as specified:

1. **Environment setup (R3):** Created `.venv` with `uv venv .venv && source .venv/bin/activate && uv pip install jsonschema pyyaml`. `.venv/` is already gitignored.

2. **Schema extension** (`services/schema/service-manifest.v1.json`):
   - Changed `service.properties.type` enum from `["docker", "host-systemd"]` to `["docker", "external"]`.
   - Added `service.properties.x_ember` exactly as specified in the brief (required `node`/`role`/`managed`; enums for `node`, `role`, `capabilities` items, `health_probe`; `additionalProperties: false`).
   - Removed the top-level `features` property block entirely (it was not in top-level `required` to begin with — only `schema_version` and `service` were required there — so no `required` edit was needed, just the property definition removal). Rest of the schema left intact.
   - Note: `service.additionalProperties` is `true` in the donor schema (not `false`), so `x_ember` was not strictly needed as a declared property to pass the plain-shape validation — but declaring it is what makes JSON Schema actually validate its *internal* structure (enums on `node`/`role`/etc.). Without declaring it, a bad `node` value would silently pass since `additionalProperties: true` lets unknown keys through unchecked. Added it per the brief regardless.

3. **Six manifests** written verbatim from the brief under `services/{omlx,litellm,litellm-postgres,ember-api,ember-dashboard,qdrant}/manifest.yaml`. Each `service.id` equals its directory name.

4. **Test script** `tests/test-manifests.sh` — written before the validator existed (TDD RED), then confirmed GREEN after the validator was added. `chmod +x` applied, `set -euo pipefail`.

5. **Validator** `scripts/validate-manifests.py` — written verbatim from the brief, `chmod +x` applied.

6. Committed with the exact message specified in the brief.

No deviations from the brief's exact file contents (schema property text, manifest YAML, script contents) — deviations, if any, were only in *how* things were verified (see self-review).

## TDD evidence

**RED** — before the validator existed:

```
$ source .venv/bin/activate && bash tests/test-manifests.sh
python3: can't open file '/Users/jtotham/Projects/Ember-AI/scripts/validate-manifests.py': [Errno 2] No such file or directory
EXIT: 2
```

**GREEN** — after schema, manifests, and validator were written:

```
$ source .venv/bin/activate && bash tests/test-manifests.sh
manifests OK
EXIT: 0
```

Negative-case check run standalone (bad `x_ember.node`):

```
$ python3 scripts/validate-manifests.py "$tmp"
/var/folders/.../bad/manifest.yaml: 'laptop' is not one of ['docker01', 'jons-mac-mini']
validated 1 manifests, 1 errors
EXIT: 1
```

## Validator output

```
$ source .venv/bin/activate && python3 scripts/validate-manifests.py services
validated 6 manifests, 0 errors
EXIT: 0
```

## Files changed

- Modified: `services/schema/service-manifest.v1.json`
- Created: `services/omlx/manifest.yaml`
- Created: `services/litellm/manifest.yaml`
- Created: `services/litellm-postgres/manifest.yaml`
- Created: `services/ember-api/manifest.yaml`
- Created: `services/ember-dashboard/manifest.yaml`
- Created: `services/qdrant/manifest.yaml`
- Created: `scripts/validate-manifests.py`
- Created: `tests/test-manifests.sh`

Commit: `adddc31cd feat: Ember service manifests with x_ember extension and validator` (9 files changed, 142 insertions, 47 deletions).

## Self-review findings

- All six manifests present; each `service.id` equals its directory name (verified by grepping `id:` per file and comparing to `dirname`).
- Schema: `type` enum is `["docker", "external"]`; `x_ember` block matches the brief character-for-character (node/role/managed/capabilities/health_probe enums, `additionalProperties: false`).
- Negative test (bad `node: laptop`) correctly fails validation — confirmed both via the test script and a standalone run showing the jsonschema error message.
- `litellm-postgres/manifest.yaml` has `health: ""` (empty string) with no `host_network` key, so the schema's `if/else` requires `port` and `health` to be present — both are present (`health` is allowed `minLength: 0`), so it validates cleanly. Confirmed via the full validator run (0 errors across 6 manifests).
- `tests/test-manifests.sh`: `chmod +x` applied, `set -euo pipefail` present as the second line. shellcheck is **not installed** on this machine (`brew list shellcheck` → "No such keg"; `which shellcheck` → not found) — per the brief this is optional and skipped; not attempted to install it.
- `scripts/validate-manifests.py`: `chmod +x` applied (brief doesn't require executability but the shebang implies it, and it does no harm).
- `git status --short` is clean after the commit — no stray files.

## Concerns

- None blocking. One judgment call: the donor schema has `service.additionalProperties: true`, not `false`, so the brief's premise ("if additionalProperties:false on service, x_ember must be declared inside properties") technically didn't force declaring `x_ember` for basic validation to pass — but declaring it was still necessary for the *negative test* to actually catch a bad `node` value (otherwise unknown-shape `x_ember` content would pass through unchecked under `additionalProperties: true`). I followed the brief's literal instruction to add `x_ember` to `service.properties` regardless, which is also what made the required negative test correctly fail.
