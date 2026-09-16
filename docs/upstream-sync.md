# Upstream sync

Ember-AI is a lean rebuild inside a fork of [`Osmantic/ODS`](https://github.com/Osmantic/ODS),
last synced at `v2.6.0` / `21f4b3a64` (2026-09-14). ODS is a donor/reference implementation,
not an architecture to preserve: the `upstream` git remote and full history are retained so
individual fixes or features can be cherry-picked later, but the ODS runtime itself
(installer, `ods-cli`, host agent, compose overlays, ~27 services) was deleted rather than
overlaid or kept compatible. See [`DOWNSTREAM.md`](../DOWNSTREAM.md) for exactly what was
kept and what was removed.

## Retained from ODS

- `services/schema/service-manifest.v1.json` — manifest schema, extended with `x_ember` and
  `type: external`.
- `dashboard/` — the React/Vite/Tailwind scaffold, theme context, sidebar pattern, nginx +
  entrypoint auth injection.
- `docs/donor/litellm-compose.yaml`, `docs/donor/langfuse-compose.yaml` — reference compose
  fragments for future phases.
- `.gitleaks.toml`, `.pre-commit-config.yaml` — secret scanning.
- `LICENSE` (Apache-2.0, Osmantic) and `NOTICE`.

## Checking for upstream changes

```bash
git fetch upstream
git log upstream/main --oneline -- <path>
```

Run this against a path that still exists in Ember (e.g. `dashboard/`, or
`services/schema/service-manifest.v1.json`) to see what has changed upstream since the last
sync. Most upstream commits will touch deleted paths and are not relevant — skim the log for
commits under the retained paths above.

## Cherry-picking a fix

```bash
git cherry-pick -x <sha>
```

If the cherry-pick conflicts because the surrounding file no longer matches ODS's structure
(likely for anything under `dashboard/`), copy the relevant change into the matching Ember
location by hand instead, and record what you did.

## Recording what was pulled

Add a line to [`DOWNSTREAM.md`](../DOWNSTREAM.md) under "Cherry-pick procedure" naming the
upstream sha and what it fixed, so the next sync knows it has already been applied. Do this
whether you used `git cherry-pick -x` (which records the sha in the commit message
automatically) or a manual copy (where it would otherwise be lost).

## Re-syncing the baseline

If Ember ever needs to re-baseline against a newer ODS release, update the "last synced ref"
line at the top of `DOWNSTREAM.md` and re-check the retained-paths list above — a newer ODS
release may have changed the manifest schema or the dashboard scaffold in ways worth pulling
in, even though the rest of the runtime stays deleted.
