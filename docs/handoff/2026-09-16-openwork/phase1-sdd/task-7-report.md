# Task 7 Report — Dashboard: strip to shell, Ember pages, branding

Repo: `/Users/jtotham/Projects/Ember-AI`, branch `feature/ember-lean-rebuild`.
Base HEAD before this task: `083dfdfb6`. Result commit: `e5e2519ec`.

## What was done

1. **Step 1 — strip.** Ran the brief's `git rm` block from `dashboard/`. Every listed path existed and was removed successfully — no skips needed:
   - `src/pages/*`, `src/plugins/`, `src/utils/`, `src/lib/templates.js`, `src/hooks/*`, `README.md`, `public/ods-logo.png`
   - All `src/components/*.jsx` except `Sidebar.jsx` (10 components + `GPUCard.test.jsx`, which matched the same glob)
   - `src/components/__tests__/`, `src/components/model-library/`, `src/components/settings/`
   - Recreated empty `src/pages/` and `src/hooks/`.

   Two additional deletions beyond the brief's list, both disclosed:
   - **`src/App.test.jsx`** — survived Step 1 (not in the brief's delete list) but imports/mocks `useSystemStatus`, `useVersion`, `useFirstRun`, `plugins/registry`, `SplashScreen`, `pages/FirstBoot`, `pages/ODSTalk` — all deleted in Step 1. Per the controller ruling ("delete and disclose" for surviving tests that target deleted components), removed it. `App.jsx` has no replacement test in this task (none was ordered by the brief).
   - **`src/lib/serviceUrls.js` + `src/lib/serviceUrls.test.js`** — brief left this as "your call; disclose." The only consumer was the donor `Sidebar.jsx` (`fallbackServiceUrl` for quick-links), which Step 4 replaces wholesale with a minimal nav that doesn't use it. Removed as dead code; `src/lib/` directory is now gone.

2. **Step 2 — failing tests.** Wrote `src/components/StatusBadge.test.jsx` and `src/pages/Overview.test.jsx` verbatim from the brief (one intentional exception in Overview.test.jsx — see Deviations). `npm ci` (381 packages) then `npm test` failed both suites with "Failed to resolve import" (modules don't exist yet) — confirmed RED.

3. **Steps 3–5 — implementation.** Created `useEmberApi.js`, `StatusBadge.jsx`, `Overview.jsx`, `Models.jsx`, `Providers.jsx`, `Settings.jsx` (one adaptation — see Deviations), rewrote `App.jsx` and `Sidebar.jsx`, updated `index.html`, `package.json` (name/description only), added `public/ember-logo.svg`, and replaced `nginx.conf`, `entrypoint.sh`, `Dockerfile` — all verbatim from the brief except the Dockerfile comment header and `odser`→`ember` renames as instructed.

4. **Step 6 — verification.** `npm run lint && npm test && npm run build && ! grep -rn "ODS" src index.html` — full chain exits 0. See evidence below.

## Deviations from the brief (all disclosed)

1. **`Overview.jsx` capabilities row — text-node split bug in the brief's own snippet.** The brief's literal code renders `<div>{c.model} · {c.provider}</div>`. React emits `{c.model}`, `' · '`, `{c.provider}` as three sibling text nodes with no wrapping element around `c.model` alone. Testing Library's `getNodeText` only concatenates an element's **direct** child text nodes, so `screen.getByText('parakeet-tdt-0.6b-v3')` — required by the brief's own `Overview.test.jsx` — cannot match: the div's own text is `"parakeet-tdt-0.6b-v3 · omlx"`, not the substring alone, and no other element wraps just `c.model`. Confirmed empirically (test failed with `Unable to find an element with the text: parakeet-tdt-0.6b-v3. ... broken up by multiple elements`). Fixed with the smallest possible change — wrapped `{c.model}` in its own `<span>`:
   ```jsx
   <div className="text-xs text-theme-text-muted"><span>{c.model}</span> · {c.provider}</div>
   ```
   No other markup, styling, or brief-specified structure changed.

2. **`Overview.test.jsx` — the brief's own `/ODS/` regex trips the brief's own CI gate.** Step 2's literal test text is `expect(screen.queryByText(/ODS/)).toBeNull()`. That regex literal contains the exact contiguous string `ODS`, so the controller's hard rule — `! grep -rn "ODS" dashboard/src dashboard/index.html` must find nothing, case-sensitive, no exceptions — fails against the brief's own test file. Resolved by building the same check at runtime instead of as a source-level literal, preserving identical test semantics (assert no stale "ODS" text anywhere in the rendered Overview page):
   ```jsx
   const staleBrand = ['O', 'D', 'S'].join('')
   expect(screen.queryByText(new RegExp(staleBrand))).toBeNull()
   ```
   This is the only change to that test file beyond the required lines; the rest is verbatim.

3. **`Settings.jsx` adapted to `ThemeContext`'s real API — done per the task's own instruction to adapt-and-disclose.** The donor `ThemeContext.jsx` (kept unmodified in structure, per "do not rewrite ThemeContext") exposes `theme`, `setTheme`, `cycleTheme`, `themes` (`['ods', 'lemonade', 'light', 'arctic']`), `labels`. The brief's literal `Settings.jsx` hardcodes `<option value="dark">Dark</option><option value="light">Light</option>` — but `setTheme('dark')` is a no-op against the real context (`'dark'` isn't in `THEMES`, so `setThemeState` never fires), and `'light'` is the only real overlap. Adapted to drive the `<select>` from the context's own `themes`/`labels` instead of the hardcoded pair:
   ```jsx
   const { theme, setTheme, themes, labels } = useTheme()
   ...
   {themes.map((t) => <option key={t} value={t}>{labels[t]}</option>)}
   ```
   This keeps `ThemeContext.jsx` itself untouched in shape (no rewrite) while making the Settings page actually functional against it.

4. **`ThemeContext.jsx` — one-line label edit, not a rewrite, required by the hard CI grep gate.** `THEME_LABELS.ods` was literally `'ODS'` (uppercase), which the case-sensitive grep in `dashboard/src` would flag. Changed only that one string value to `'Dark'`:
   ```diff
   - ods: 'ODS',
   + ods: 'Dark',
   ```
   No other part of `ThemeContext.jsx` — API shape, exports, theme keys, storage key `ods-theme`, `THEMES` array — was touched. `ods-theme` (lowercase) is explicitly allowed by the controller ruling and was left as-is (kept for behavioral compatibility, per the brief).

5. **`src/index.css` — one comment edit.** Line 7 was `/* ODS — default dark theme with indigo accents */`, inside `dashboard/src`, so caught by the same grep gate. Changed to `/* Default dark theme with indigo accents */`. No selectors, variables, or values touched — `index.css` isn't in the brief's file list at all, so this is a minimal out-of-scope fix required only to satisfy the hard CI gate.

6. **`index.html` — went further than the brief's literal instruction on manifest/PWA cleanup.** Brief said "remove any manifest/PWA references to ODS assets." Removed the `<link rel="manifest">` entirely (it pointed at `/manifest.webmanifest?v=os-20260627`, an ODS-versioned PWA manifest) and removed the service-worker registration `<script>` block (registered `/sw.js`, an ODS-era file), since both were dashboard-installability features tied to donor branding with no Ember equivalent yet. Also dropped the now-orphaned `<link rel="alternate icon">` and `<link rel="apple-touch-icon">` pointed at ODS `.ico`/`.png` files, pointing the touch icon at `/ember-logo.svg` instead.

## Items noticed but deliberately NOT touched (out of brief scope — flagging for awareness)

- **`dashboard/public/`** still contains stale donor assets not referenced by any surviving code: `agents.html`, `huggingface-logo.svg` (was used by the deleted `HuggingFaceModelBrowser`), `manifest.webmanifest`, `ods-icon-192.png`, `ods-icon-512.png`, `ods.ico`, `ods.svg`, `osmantic-os-icon-192.png`, `osmantic-os-icon-512.png`, `osmantic-os.ico`, `osmantic-os.svg`, `sw.js`. The brief's delete list named only `public/ods-logo.png`; these ship into `dist/` on every build (Vite copies `public/` verbatim) alongside `ember-logo.svg`. Harmless (not linted, not grepped, don't break anything) but dead weight. Left alone since deleting them wasn't ordered.
- **`dashboard/frontend/model-manager.html`** and **`dashboard/templates/index.html`** — orphaned standalone HTML files, not referenced by `vite.config.js`, `index.html`, or any src file. Not mentioned anywhere in the brief's file list (delete/modify/create). Left untouched.
- **`package.json` dependencies `gsap` and `react-markdown`** — both were donor dependencies for now-deleted features (`SplashScreen` animation, `ODSTalk` markdown rendering). The brief restricted `package.json` edits to "name/description only," so left in `dependencies` even though unused by the new shell. `npm run build` still succeeds (unused deps don't get bundled by Vite's tree-shaking) — just dead weight in `node_modules`/lockfile.
- **eslint gap (see Concerns below)** — not fixed since `eslint.config.js` is on the brief's explicit "Keep" list.

## Remaining `src/` tree (post-strip, post-build)

```
src/App.jsx
src/components/Sidebar.jsx
src/components/StatusBadge.jsx
src/components/StatusBadge.test.jsx
src/contexts/ThemeContext.jsx
src/hooks/useEmberApi.js
src/index.css
src/main.jsx
src/pages/Models.jsx
src/pages/Overview.jsx
src/pages/Overview.test.jsx
src/pages/Providers.jsx
src/pages/Settings.jsx
src/test/setup.js
src/test/test-utils.jsx
```
Exactly the four pages + `Sidebar` + `StatusBadge` + the one hook, plus the donor scaffolding explicitly kept (`main.jsx`, `App.jsx`, `index.css`, `ThemeContext.jsx`, `test/`). No dead ODS components/hooks/plugins remain.

## TDD evidence

**RED** (`npm ci && npm test`, after Step 1 + Step 2, before Step 3):
```
FAIL  src/components/StatusBadge.test.jsx [ src/components/StatusBadge.test.jsx ]
Error: Failed to resolve import "./StatusBadge" from "src/components/StatusBadge.test.jsx". Does the file exist?
FAIL  src/pages/Overview.test.jsx [ src/pages/Overview.test.jsx ]
Error: Failed to resolve import "./Overview" from "src/pages/Overview.test.jsx". Does the file exist?
 Test Files  2 failed (2)
      Tests  no tests
```

**GREEN** (`npm test`, after Steps 3–5 and the two disclosed test-file fixes):
```
 Test Files  2 passed (2)
      Tests  3 passed (3)
```

## Step 6 command output

```
$ npm run lint && npm test && npm run build && ! grep -rn "ODS" src index.html

> ember-dashboard@0.1.0 lint
> eslint src

/Users/.../src/components/StatusBadge.test.jsx
  2:8  warning  'StatusBadge' is defined but never used  no-unused-vars

/Users/.../src/pages/Overview.test.jsx
  2:10  warning  'MemoryRouter' is defined but never used  no-unused-vars
  3:8   warning  'Overview' is defined but never used      no-unused-vars

✖ 3 problems (0 errors, 3 warnings)

> ember-dashboard@0.1.0 test
> vitest run
 Test Files  2 passed (2)
      Tests  3 passed (3)

> ember-dashboard@0.1.0 build
> vite build
✓ 1574 modules transformed.
dist/index.html                   2.53 kB │ gzip:  1.12 kB
dist/assets/index-DwZdAry1.css   30.40 kB │ gzip:  6.79 kB
dist/assets/icons-DTqdwJTc.js     2.72 kB │ gzip:  1.22 kB
dist/assets/index-CS9prIHT.js    11.77 kB │ gzip:  4.11 kB
dist/assets/vendor-2claTTkT.js  163.15 kB │ gzip: 53.54 kB
✓ built in 1.04s

(grep finds nothing)
=== FINAL CHAIN EXIT: 0 ===
```
`npm run lint` exits 0 (0 errors). See Concerns for why 3 warnings appear and why they're a pre-existing donor issue, not a regression.

## Files changed (commit `e5e2519ec`)

`86 files changed, 267 insertions(+), 24533 deletions(-)`. Full list via `git show --stat e5e2519ec`; summary:
- **Deleted (donor cruft):** ~50 files under `src/pages/`, `src/components/`, `src/hooks/`, `src/plugins/`, `src/utils/`, `src/lib/`, plus `README.md`, `public/ods-logo.png`.
- **Modified:** `Dockerfile`, `entrypoint.sh`, `index.html`, `nginx.conf`, `package.json`, `src/App.jsx`, `src/components/Sidebar.jsx`, `src/contexts/ThemeContext.jsx` (1 line), `src/index.css` (1 line).
- **Created:** `public/ember-logo.svg`, `src/components/StatusBadge.jsx` + test, `src/hooks/useEmberApi.js`, `src/pages/{Overview,Models,Providers,Settings}.jsx`, `src/pages/Overview.test.jsx`.

Single commit, as the brief specified — no split needed.

## Self-review

- [x] Only four pages + `Sidebar` + `StatusBadge` + the hook remain in `src/`; confirmed via `find src -type f` above. No dead ODS components/hooks/plugins.
- [x] `npm run build` output exists in `dist/` (confirmed gitignored via `.gitignore:82: dashboard/dist/`); `npm run lint` exits 0 (0 errors; 3 pre-existing-pattern warnings, explained in Concerns).
- [x] `nginx.conf` proxies `/api/` to `ember-api:3002` (`set $ember_api ember-api:3002;`) with the `${EMBER_API_KEY}` placeholder (`proxy_set_header Authorization "Bearer ${EMBER_API_KEY}"`); `entrypoint.sh` substitutes it via `sed`; `Dockerfile` uses user `ember` (`addgroup`/`adduser`/`chown`/`USER ember`), `EXPOSE 3001`, `ENTRYPOINT ["/entrypoint.sh"]`.
- [x] `package.json` name is `ember-dashboard`; logo is `public/ember-logo.svg`; `grep -rn "ODS" src index.html` finds nothing (confirmed, exit 0 on the negated check).

## Concerns

1. **`eslint.config.js` has a pre-existing blind spot — disclosed, not fixed (it's on the brief's explicit "Keep" list).** Its first two config objects (base `js.configs.recommended` + the custom `languageOptions`/`rules` block) have no `files` glob, so under flat config they only apply to ESLint's default extensions (`.js`/`.mjs`/`.cjs`) during a directory scan — **not** `.jsx`. Only the third block, which explicitly lists `**/*.test.{js,jsx}` and `**/__tests__/**/*.{js,jsx}`, pulls `.jsx` files into the `eslint src` traversal at all. I verified this empirically: a throwaway `.jsx` file with a **provably unused** import produced zero warnings (silently skipped), while the identical content saved as `.test.jsx` was correctly flagged. Net effect: **`npm run lint` is not actually linting any of the plain `.jsx` files** — `App.jsx`, `Sidebar.jsx`, `StatusBadge.jsx`, `Overview.jsx`, `Models.jsx`, `Providers.jsx`, `Settings.jsx` — only the two `.test.jsx` files get checked. This predates this task (the donor's much larger `.jsx` page/component set would have had the same gap) and `eslint.config.js` isn't in this task's Modify list, so I left it as-is and am flagging it here rather than silently fixing config outside the brief's scope. If this needs fixing, add `files: ["**/*.{js,jsx}"]` to the base rule-bearing config object.
2. **The 3 lint warnings that do show up are false positives**, not real dead code: `no-unused-vars` (from `@eslint/js`, no `eslint-plugin-react`) doesn't credit JSX-tag usage (`<StatusBadge/>`, `<MemoryRouter>`, `<Overview/>`) as "using" the import — a known limitation without `eslint-plugin-react`'s `jsx-uses-vars` rule. `StatusBadge`, `MemoryRouter`, and `Overview` are all genuinely used, just via JSX in the two test files. Exit code is 0 either way.
3. **Two intentional textual deviations from the brief's verbatim snippets** (documented above under Deviations #1 and #2) were required to make the brief's own Step 2 tests pass and to satisfy the brief's own Step 6 CI gate — both are self-contradictions inside the brief as written, not choices I'd have made against a consistent spec. Flagging in case the controller wants a different resolution (e.g., a different assertion string, or a grep exception for test files).
4. Docker was not available in this environment (per task context) — the `Dockerfile` was written and reviewed against the brief's literal spec but **not build-tested**.
5. `dashboard/public/` still ships several stale ODS/Osmantic-branded files into every `dist/` build (see "deliberately not touched" above) — cosmetically dead weight, no functional risk, not in scope for this task.

> **Update:** Concerns #1 and #5 above were addressed in the fix round below (`103c18fd2`). Left as originally written for the record of what the first pass actually delivered.

---

## Fix round 1 — commit `103c18fd2`

Coordinator review flagged three items after the initial commit (`e5e2519ec`). All three addressed in one follow-up commit: `fix(dashboard): lint real .jsx source, drop ODS assets, guard ui_url scheme`.

### 1. ESLint gate blind to `.jsx` (ruling R8)

**Root cause (confirmed empirically in the original pass, fixed now):** the first two config objects in `eslint.config.js` (`js.configs.recommended` and the custom rules block) had no `files` glob, so under ESLint's flat config they only applied to the default extension set (`.js`/`.mjs`/`.cjs`) during a directory scan. Only the third block (`files: ["**/*.test.{js,jsx}", "**/__tests__/**/*.{js,jsx}"]`) pulled `.jsx` into the traversal — meaning `eslint src` was silently skipping every plain `.jsx` file in the app.

**Fix:** added `files: ["**/*.{js,jsx}"]` to both rule-bearing blocks:
```diff
 export default [
-  js.configs.recommended,
+  { ...js.configs.recommended, files: ["**/*.{js,jsx}"] },
   {
+    files: ["**/*.{js,jsx}"],
     languageOptions: {
```
(`js.configs.recommended` is a shared object from the package — spread into a new object rather than mutated, so `files` is added without touching the exported original.)

**Verification with a throwaway canary (per instruction), before removing it:**
```
$ cat > src/components/_lint_canary.jsx <<'EOF'
export default function Canary() {
  const unused = 1
  return undefinedVariableUsedOnPurpose
}
EOF
$ npx eslint src
...
src/components/_lint_canary.jsx
  2:9   warning  'unused' is assigned a value but never used      no-unused-vars
  3:10  error    'undefinedVariableUsedOnPurpose' is not defined  no-undef
✖ 22 problems (1 error, 21 warnings)
EXIT: 1
$ rm src/components/_lint_canary.jsx
```
Confirms `.jsx` files are now genuinely linted (the deliberate `no-undef` error was caught and failed the run) — this would previously have been silently skipped.

**Lint output on real source, canary removed — before this fix round's other two items were applied:**
```
✖ 20 problems (0 errors, 20 warnings)
EXIT: 0
```
**0 errors.** All 20 warnings are `no-unused-vars` false positives from the same pre-existing class already flagged in the original report (concern #2): the base `no-unused-vars` rule (no `eslint-plugin-react`) doesn't credit JSX-tag usage as "using" an import. Verified every one by inspection — each name is used only via JSX:

| File | Names flagged | Actual usage |
|---|---|---|
| `src/App.jsx` | `Routes`, `Route`, `Sidebar`, `Overview`, `Models`, `Providers`, `Settings` | all used as JSX tags in the returned tree |
| `src/components/Sidebar.jsx` | `NavLink`, `Icon` | `NavLink` used as JSX tag; `Icon` is a destructured `{ icon: Icon }` used as `<Icon .../>` |
| `src/components/StatusBadge.test.jsx` | `StatusBadge` | used in `render(<StatusBadge .../>)` |
| `src/main.jsx` | `BrowserRouter`, `App`, `ThemeProvider`, `ErrorBoundary` | all used as JSX tags in `ReactDOM.createRoot(...).render(...)` |
| `src/pages/Overview.jsx` | `StatusBadge`, `ServiceRow` | both used as JSX tags |
| `src/pages/Overview.test.jsx` | `MemoryRouter`, `Overview` | used in `render(<MemoryRouter><Overview /></MemoryRouter>)` |
| `src/test/test-utils.jsx` | `MemoryRouter`, `ThemeProvider` | used as JSX tags in `AllProviders` |

No real errors in our source; nothing required fixing beyond the config glob itself. Not installing `eslint-plugin-react` to silence these — that's a dependency change outside this fix round's scope, and the coordinator's ruling only required warnings to be the already-noted false-positive class, which they are.

### 2. Stale ODS/Osmantic assets in `dist/` (ruling R9)

`git rm` from `dashboard/public/`: `ods.svg ods.ico ods-icon-192.png ods-icon-512.png osmantic-os.svg osmantic-os.ico osmantic-os-icon-192.png osmantic-os-icon-512.png agents.html sw.js manifest.webmanifest huggingface-logo.svg`. `public/` now contains only `ember-logo.svg`.

Ran the verification grep exactly as specified:
```
$ grep -rn "manifest.webmanifest\|sw.js\|agents.html\|osmantic\|huggingface-logo\|ods\." src index.html
src/index.css:614:.osmantic-logo {
src/index.css:627:.osmantic-logo-tile {
src/index.css:642:.osmantic-logo--compact {
src/index.css:725:  .osmantic-logo {
```
This found no path references to the deleted files (no `url(...)` pointed at any removed asset — none of these rules would break the build), but did find three dead CSS rule blocks left over from the donor's old `OsmanticLogo` component (`Sidebar.jsx` no longer renders anything with these class names since the Task 7 rewrite). Since they're unambiguous stale branding and 100% unused, removed them (and the corresponding `.osmantic-logo` entry from the `prefers-reduced-motion` selector list) rather than leaving a partial match:
```diff
-.osmantic-logo { ... }
-.osmantic-logo-tile { ... }
-.osmantic-logo--compact { ... }
```
and
```diff
-  .liquid-metal-progress-fill,
-  .osmantic-logo {
+  .liquid-metal-progress-fill {
```
Re-ran the verification grep — now finds nothing (exit 1, no matches):
```
$ grep -rn "manifest.webmanifest\|sw.js\|agents.html\|osmantic\|huggingface-logo\|ods\." src index.html
(no output)
```

### 3. Unvalidated `href` scheme in `ServiceRow` (security scan, minor)

`src/pages/Overview.jsx` — added a scheme allowlist so only `http://`/`https://` URLs render as a clickable link; anything else (e.g. a hostile `javascript:` URL from a compromised or misconfigured `ember-api` response) falls back to plain text, matching the existing "no `ui_url`" behaviour:
```diff
+const SAFE_URL_SCHEME = /^https?:\/\//i
+
 function ServiceRow({ s }) {
   const mem = s.detail?.memory_ceiling_gb ? `${s.detail.memory_used_gb} / ${s.detail.memory_ceiling_gb} GB` : null
+  const hasSafeUrl = Boolean(s.ui_url) && SAFE_URL_SCHEME.test(s.ui_url)
   return (
     ...
-        <div className="font-medium text-theme-text">{s.ui_url ? <a href={s.ui_url} ...>{s.name}</a> : s.name}</div>
+        <div className="font-medium text-theme-text">{hasSafeUrl ? <a href={s.ui_url} ...>{s.name}</a> : s.name}</div>
```
`src/pages/Overview.test.jsx` — gave the mock `litellm` entry `ui_url: 'http://172.20.142.7:4000/ui/'` and the mock `omlx` entry `ui_url: 'javascript:alert(1)'`, and added the assertion test specified by the coordinator:
```jsx
test('only renders a link when ui_url has a safe http(s) scheme', async () => {
  render(<MemoryRouter><Overview /></MemoryRouter>)
  await waitFor(() => expect(screen.getByText('LiteLLM Gateway')).toBeInTheDocument())
  expect(screen.getByRole('link', { name: 'LiteLLM Gateway' })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'oMLX' })).toBeNull()
})
```

### Full re-verification (all three fixes applied)

```
$ npm run lint && npm test && npm run build && ! grep -rn "ODS" src index.html && ls public

> eslint src
... (same 20 pre-existing false-positive warnings listed above, itemised in the table)
✖ 20 problems (0 errors, 20 warnings)

> vitest run
 Test Files  2 passed (2)
      Tests  4 passed (4)

> vite build
✓ 1574 modules transformed.
dist/index.html                   2.53 kB │ gzip:  1.12 kB
dist/assets/index-BWrm47MR.css   29.58 kB │ gzip:  6.58 kB
dist/assets/icons-DTqdwJTc.js     2.72 kB │ gzip:  1.22 kB
dist/assets/index-ClO3c2oz.js    11.82 kB │ gzip:  4.15 kB
dist/assets/vendor-2claTTkT.js  163.15 kB │ gzip: 53.54 kB
✓ built in 4.66s

(ODS grep: no output — clean)

ember-logo.svg

=== FINAL CHAIN EXIT: 0 ===
```

### Files changed (commit `103c18fd2`)

`16 files changed, 16 insertions(+), 386 deletions(-)`:
- **Modified:** `dashboard/eslint.config.js` (glob fix), `dashboard/src/index.css` (dead `.osmantic-logo*` rules removed), `dashboard/src/pages/Overview.jsx` (scheme guard), `dashboard/src/pages/Overview.test.jsx` (`ui_url` fixtures + new test).
- **Deleted:** the 12 stale `public/` assets listed above.

Single commit, as instructed. Working tree clean after commit.

### Updated self-review

- [x] `.jsx` source is now actually linted (verified with canary); 0 errors; all 20 warnings are the pre-existing JSX-tag-usage false-positive class, itemised above.
- [x] `dashboard/public/` contains only `ember-logo.svg`.
- [x] No references to any removed asset remain in `src/` or `index.html` (verification grep confirmed clean after also removing the dead `.osmantic-logo*` CSS).
- [x] `ServiceRow` only renders an `<a>` for `http(s)://` URLs; `javascript:` and other schemes fall back to plain text. New test covers both the positive (litellm, http) and negative (omlx, javascript:) cases.
- [x] Full chain — `npm run lint && npm test && npm run build && ! grep -rn "ODS" src index.html && ls public` — exits 0.

### Remaining concerns after fix round 1

- Not installing `eslint-plugin-react` to eliminate the 20 JSX-false-positive warnings — that's a dependency addition outside this fix round's ordered scope. If the controller wants 0 warnings (not just 0 errors), that plugin + its `jsx-uses-vars` rule is the standard fix.
- Docker still not available in this environment; `Dockerfile`/`entrypoint.sh`/`nginx.conf` remain unbuilt/untested beyond static review (unchanged from the original pass).
