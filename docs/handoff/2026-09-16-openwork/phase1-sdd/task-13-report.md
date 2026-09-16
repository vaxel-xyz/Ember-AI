# Task 13 report (Steps 1 & 2 only — PR deferred to controller)

## Step 1: full local suite

`source .venv/bin/activate && bash tests/run.sh` from repo root. Tail:

```
manifests OK
SKIP: docker not available
Ember doctor
  ✓ env OMLX_BASE_URL set
  ✓ env OMLX_API_KEY set
  ✓ env LITELLM_MASTER_KEY set
  ✓ env EMBER_API_KEY set
  ✓ env OMLX_CHAT_MODEL set
  ✓ env OMLX_EMBED_MODEL set
  ✓ oMLX reachable (loaded models: 1)
  ✓ LiteLLM readiness
  ✓ ember-api health
  ✓ ember-auto completion: pong
  ✓ ember-embed vector length 2
all checks passed
doctor OK
.....................                                                    [100%]
21 passed, 2 warnings in 1.41s

 RUN  v4.1.7 /Users/jtotham/Projects/Ember-AI/dashboard
 Test Files  2 passed (2)
      Tests  4 passed (4)
   Duration  9.58s

ALL OK
```

Compose test SKIPped as expected (no local Docker); the real compose test ran in CI. Everything else green, ends `ALL OK`.

## Step 2: fold raw drill evidence into the receipt

Edited `docs/deployment.md`, appending a new subsection immediately after the existing
"Validation receipt 2026-09-14" table (Task 12 rows left untouched):

**`#### Mini-off drill — raw capture (controller re-run, 18:21–18:24 UTC)`**

- Opening note: the controller's first re-run attempt saw `omlx stop` take no effect within
  60 s and was abandoned/repeated; the table reflects the successful repeat.
- 7-row table (Time | oMLX state | LiteLLM state | Dashboard HTTP | Note), built from
  `.superpowers/sdd/2026-09-14-ember-ai-phase1-foundation/drill-raw-182124.json`:
  1. `18:21:02` baseline `healthy` (2 resident), litellm `degraded`, dashboard 200
  2. `18:21:25` `omlx stop` issued
  3. `18:21:39` first unreachable probe (`000000`)
  4. `18:22:13` mid-outage sample (`000000`)
  5. `18:23:03` mid-outage sample (`000000`)
  6. `18:23:27` `/api/services` catches up to `unreachable` (timeout after 5s); `omlx start`
     issued same instant
  7. `18:24:40` recovery — `healthy` (1 resident), ~54 s after start
- Closing note ties the raw capture back to the Task 12 prose row (`ember-api`/`ember-dashboard`
  held HTTP 200 throughout, `litellm` degraded independent of the oMLX outage, `qdrant`
  unreachable throughout as its profile is off) and cites the raw JSON file as a
  workspace-only, git-ignored artefact.

Diff: `docs/deployment.md` +24 lines, no deletions. `git diff --stat` confirmed this was the
only tracked file touched (pr-body.md and the raw JSON both live under `.superpowers/`, which
is git-ignored in this repo — verified with `git check-ignore -v`).

## PR body

Written to `/Users/jtotham/Projects/Ember-AI/.superpowers/sdd/2026-09-14-ember-ai-phase1-foundation/pr-body.md`
(git-ignored workspace file, not part of the commit). Contains:
- `## Summary` — 4 sentences per brief.
- `## Acceptance (spec §11)` — all 9 criteria, all `- [x]` (Phase 1 scope fully met per the
  receipts read), each with one evidence line pointing at the validation receipt, CI, or an
  ADR. `ember-think` (OpenRouter cloud alias) called out as unvalidated — no key provisioned —
  under criterion 4's evidence and reiterated in "Rulings and follow-ups", per instruction.
- `## Rulings and follow-ups` — Kokoro TTS blind-A/B result, rerank via `jina_ai/` LiteLLM
  route, `encoding_format` fix, Qdrant key required at compose time, inherited LiveKit
  credential (annotated in `.gitleaks.toml`/`DOWNSTREAM.md`, purge left to the owner), Phase 3
  Langfuse pending, Hermes cutover deferred to Phase 5.
- Closing line: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- No secrets, no policy commentary.

## Commit & push

```
commit f8cc15d4e
docs: add raw mini-off drill capture to validation receipt
1 file changed, 24 insertions(+)
```

Pushed to `feature/ember-lean-rebuild` (`c4aad464e..f8cc15d4e`).

## CI

Both required workflows green on the new commit:
- `ci` — https://github.com/vaxel-xyz/Ember-AI/actions/runs/34880910870 (dashboard, compose-and-shell, python, images all ✓)
- `secret-scan` — https://github.com/vaxel-xyz/Ember-AI/actions/runs/34880910593 (gitleaks ✓)

`gh run watch 34880910870 --exit-status` exited 0.

## Self-review

- Verified `.superpowers/` is git-ignored before writing `pr-body.md` there, so it can't
  accidentally get swept into the docs commit.
- Confirmed HEAD before starting (`c4aad464e`, clean tree) matched the dispatch's stated
  starting point.
- Cross-checked every acceptance-criteria evidence line against either the existing receipt
  table, the new raw-capture table, an ADR number that exists in `docs/adr/`, or this
  dispatch's own `tests/run.sh` run — no fabricated figures.
- Did not touch Step 3 (PR creation) — left for the controller's whole-branch review, per
  dispatch scope.
- Concern to flag to the controller: the raw JSON's recorded "back after 54 s" event text
  doesn't precisely match the gap between its own `18:23:27` start-issued and `18:24:40`
  recovery timestamps (~73 s clock time) — I reported both figures in the table/summary as
  given in the source data rather than reconciling them, since the discrepancy is in the
  controller's own capture, not something I should silently correct.
