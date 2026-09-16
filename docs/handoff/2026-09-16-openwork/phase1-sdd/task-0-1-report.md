# Task 0 + Task 1 execution report — Ember-AI Phase 1 foundation

Executed from `/Users/jtotham/Projects/Ember-AI`, starting on `main @ 21f4b3a64` (clean apart from one
untracked ADR file at repo root).

## Task 0: Branch, remote, worktree, ADR relocation

### Step 1: Branch + upstream remote
Ran verbatim:
```
git remote add upstream https://github.com/Osmantic/ODS.git || true
git fetch upstream --tags --quiet
git checkout -b feature/ember-lean-rebuild main
```
No deviation. `origin` remained `https://github.com/vaxel-xyz/Ember-AI.git`.

### Step 2: Move Jon's URL ADR into docs/adr and add the STT ADR
- `ADR — Vaxel Service URLs, Ownership and Network Architecture.md` was **untracked** (not yet in git), so
  `git mv` failed with "not under version control" on the first attempt. Fix: `git add` the file first,
  then `git mv` it to `docs/adr/0001-vaxel-service-urls-ownership-network.md`. This is the only path
  deviation in Task 0 and is mechanically necessary — no content change.
- `docs/adr/0002-stt-parakeet-via-omlx.md` was created by copying
  `/Users/jtotham/Projects/Ember-AI/.superpowers/sdd/2026-09-14-ember-ai-phase1-foundation/adr-0002-source.md`
  **verbatim**, per the controller decision. Title "Use Parakeet v3 via oMLX for Ember-AI Speech-to-Text",
  Status Accepted, Date 2026-09-14 — confirmed present in the source and preserved exactly. No
  reconstruction from spec was needed; the source file existed and was used directly.

### Step 3: Commit
```
git add -A docs/adr
git commit -m "docs: relocate Vaxel URL/ownership ADR and add STT ADR"
```
Commit `c0993bf5a`. 2 files changed (both adds), 780 insertions, no deletions.

## Task 1: Strip ODS to the donor set

### Step 1: Delete ODS
All commands ran successfully in order:
```
mkdir -p services/schema docs/donor
git mv ods/extensions/schema/service-manifest.v1.json services/schema/service-manifest.v1.json
git mv ods/extensions/services/dashboard dashboard
git mv ods/extensions/services/litellm/compose.yaml docs/donor/litellm-compose.yaml
git mv ods/extensions/services/langfuse/compose.yaml.disabled docs/donor/langfuse-compose.yaml
git mv ods/.env.schema.json .env.schema.json
git rm -r -q ods installer install.sh install.ps1 ARCHITECTURE.md CLAUDE.md CONTRIBUTING.md CONTRIBUTORS.md SECURITY.md SECURITY_AUDIT.md .claude .gitleaksignore .github/workflows
git rm -q README.md
```
Every listed path in `git rm -r -q ...` existed and was removed — nothing was skipped.

**Deviation (per controller decision):** `dashboard/manifest.yaml` and `dashboard/compose.local.yaml` were
removed with `git rm`, not `rm -rf`, as instructed. First attempt (`git rm -q`) failed with "the following
files have changes staged in the index" because the preceding `git mv ods/extensions/services/dashboard
dashboard` had already staged them as part of the directory rename. Used `git rm -f -q` instead — this is
still `git rm` (satisfies the controller decision's intent of not using `rm -rf`), the `-f` only overrides
git's "already staged, are you sure" guard on files that were just moved wholesale by the previous command;
no working-tree state was bypassed.

### Step 2: DOWNSTREAM.md and NOTICE
Both files created verbatim from the brief text. No deviation.

### Step 3: Tighten .gitignore and gitleaks allowlist
- Appended the exact block from the brief to `.gitignore`, **plus** `.superpowers/` and `.venv/` per the
  controller decision (workspace scratch and Python venv). Note: `.env` / `.env.*` / `!.env.example` already
  existed earlier in the pre-existing `.gitignore` (lines 27-29, "Secrets and credentials (global)"); the
  brief's block duplicates these lines. Appended as instructed rather than de-duplicating, since the brief
  says "append" verbatim and duplicate gitignore patterns are harmless.
- Replaced the `[allowlist]` block in `.gitleaks.toml` with the exact replacement from the brief. This
  removes the ODS installer-script allowlist entries (`ods/installers/...`), which is correct since those
  paths no longer exist after Step 1.

### Step 4: Verify tree and commit
`git status --short | wc -l` returned 1339 immediately before the final `git add -A && git commit` (staged
changes pending commit — expected, not an error state). After commit, `git status --short` is empty.

```
git add -A
git commit -m "chore: strip ODS runtime to Ember donor set (see DOWNSTREAM.md)"
```
Commit `f9e5c9019`. 1339 files changed, 46 insertions, 298272 deletions.

## Verification output (post both commits)

```
$ git status --short
(empty)

$ git ls-files | wc -l
132

$ ls
DOWNSTREAM.md  LICENSE  NOTICE  dashboard  docs  services

$ ls -a
.  ..  .env.schema.json  .git  .gitattributes  .github  .gitignore  .gitleaks.toml
.pre-commit-config.yaml  .superpowers  DOWNSTREAM.md  LICENSE  NOTICE  dashboard  docs  services

$ git log --oneline -3
f9e5c9019 chore: strip ODS runtime to Ember donor set (see DOWNSTREAM.md)
c0993bf5a docs: relocate Vaxel URL/ownership ADR and add STT ADR
21f4b3a64 Merge pull request #2810 from tang-vu/fix/uninstall-safe-sudo-prompt

$ git branch --show-current
feature/ember-lean-rebuild

$ git status --short --ignored
!! .superpowers/
```

`git ls-files | wc -l` = 132 — small (hundreds, not thousands), as expected. `.superpowers/` is correctly
ignored and does not appear in plain `git status --short`, matching the brief's "also acceptable" note.

## Files changed / moved / deleted summary

**Task 0**
- Moved: `ADR — Vaxel Service URLs, Ownership and Network Architecture.md` → `docs/adr/0001-vaxel-service-urls-ownership-network.md`
- Created: `docs/adr/0002-stt-parakeet-via-omlx.md` (verbatim copy of `adr-0002-source.md`)

**Task 1**
- Moved: `ods/extensions/schema/service-manifest.v1.json` → `services/schema/service-manifest.v1.json`
- Moved: `ods/extensions/services/dashboard/` → `dashboard/` (minus `manifest.yaml`, `compose.local.yaml`, which were then `git rm -f`'d)
- Moved: `ods/extensions/services/litellm/compose.yaml` → `docs/donor/litellm-compose.yaml`
- Moved: `ods/extensions/services/langfuse/compose.yaml.disabled` → `docs/donor/langfuse-compose.yaml`
- Moved: `ods/.env.schema.json` → `.env.schema.json`
- Deleted (git rm -r): `ods/`, `installer/`, `install.sh`, `install.ps1`, `ARCHITECTURE.md`, `CLAUDE.md`,
  `CONTRIBUTING.md`, `CONTRIBUTORS.md`, `SECURITY.md`, `SECURITY_AUDIT.md`, `.claude/`, `.gitleaksignore`,
  `.github/workflows/`
- Deleted: `README.md`
- Deleted: `dashboard/manifest.yaml`, `dashboard/compose.local.yaml`
- Created: `DOWNSTREAM.md`, `NOTICE`
- Edited: `.gitignore` (appended secrets/build-artifact/scratch block), `.gitleaks.toml` (allowlist replaced)
- Kept unedited: `LICENSE`, `.pre-commit-config.yaml`, `.gitattributes`

Net: 1339 files touched in Task 1's commit (mostly deletions from `ods/`), 46 insertions, 298272 deletions.

## Self-review findings

- **Completeness:** every `git mv`/`git rm` in both briefs was executed. `DOWNSTREAM.md` and `NOTICE`
  created with exact brief text. `.gitignore` additions present (brief block + controller's `.superpowers/`
  and `.venv/`). `.gitleaks.toml` `[allowlist]` block replaced exactly as specified.
- **Nothing extra deleted or created** — with one exception flagged as a concern below (`.github`
  discrepancy). I did not expand scope to remove files not explicitly listed.
- **Both commits present with exact messages:**
  - `c0993bf5a` — "docs: relocate Vaxel URL/ownership ADR and add STT ADR"
  - `f9e5c9019` — "chore: strip ODS runtime to Ember donor set (see DOWNSTREAM.md)"

## Concerns

1. **`.github` discrepancy.** Task 1 Step 1's literal `git rm -r -q ... .github/workflows` only removes
   the `workflows/` subdirectory. The repo's `.github/` also contains `dependabot.yml`,
   `pull_request_template.md`, `ISSUE_TEMPLATE/*.yml`, `scripts/*.py` (docstring/type-hint generation
   helpers), `prompts/*.md` (nightly-code-review, issue-to-pr, nightly-docs-update prompts), and
   `test-events/*.json`. These 15 files remain tracked and appear in `ls -a` as `.github`. However, Task 1
   Step 4's "Expected" listing does **not** include `.github` at all, implying the brief author intended
   `.github` to be fully gone. I followed the literal command (only `.github/workflows` deleted) rather than
   guessing an expanded deletion, per the instruction not to guess and to avoid deleting anything extra —
   but this means the final tree doesn't exactly match Step 4's expected listing. Flagging for controller
   decision: should the rest of `.github/` (dependabot config, issue templates, AI-automation scripts/
   prompts, test fixtures) also be removed as part of the ODS donor strip?
2. Two mechanical deviations from literal brief commands, both necessitated by git state, not by choice:
   the `git add` before `git mv` on the untracked ADR file (Task 0), and `git rm -f -q` instead of plain
   `git rm -q` for `dashboard/manifest.yaml` / `dashboard/compose.local.yaml` (Task 1, per controller
   decision to use `git rm` not `rm -rf`). Both are noted above with rationale.

No other concerns. Both branches/commits are local only — nothing was pushed, `git clean` was never run,
and no work touched anything outside `/Users/jtotham/Projects/Ember-AI`.

## Follow-up fix (coordinator ruling on the `.github` concern)

Coordinator ruled: delete the entire remaining `.github/` directory (dependabot.yml, ISSUE_TEMPLATE,
scripts, prompts, test-events — all ODS-specific); Task 11 recreates `.github/workflows/` from scratch.

Executed as a new commit (not an amend) on `feature/ember-lean-rebuild`:
```
git rm -r -q .github
```
Also updated `DOWNSTREAM.md`'s "Removed" list in the same commit, appending:
`` `.github/` (issue templates, dependabot config, AI-automation prompts/scripts — Task 11 recreates
`.github/workflows/` from scratch). ``

```
git add -A
git commit -m "chore: remove remaining ODS .github metadata"
```
Commit `f445ad14e` — 17 files changed (16 deletions under `.github/`, 1 edit to `DOWNSTREAM.md`), 2
insertions, 1693 deletions.

Verification post-fix:
```
$ git status --short
(empty)

$ ls -a
.  ..  .env.schema.json  .git  .gitattributes  .gitignore  .gitleaks.toml
.pre-commit-config.yaml  .superpowers  DOWNSTREAM.md  LICENSE  NOTICE  dashboard  docs  services

$ git log --oneline -4
f445ad14e chore: remove remaining ODS .github metadata
f9e5c9019 chore: strip ODS runtime to Ember donor set (see DOWNSTREAM.md)
c0993bf5a docs: relocate Vaxel URL/ownership ADR and add STT ADR
21f4b3a64 Merge pull request #2810 from tang-vu/fix/uninstall-safe-sudo-prompt

$ git ls-files | wc -l
116
```

`.github` no longer appears anywhere in `ls -a`. Tree now matches Task 1 Step 4's expected listing exactly
(plus ignored `.superpowers/`). Concern #1 above is resolved; concern #2 (mechanical deviations) stands as
informational only, no action needed.
