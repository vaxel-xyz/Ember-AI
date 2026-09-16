### Task 11: CI

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/secret-scan.yml`

- [ ] **Step 1: ci.yml**

```yaml
name: ci
on: { push: { branches: [main, "feature/**"] }, pull_request: {} }
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e './ember-api[dev]' jsonschema pyyaml
      - run: ruff check ember-api config/litellm scripts
      - run: cd ember-api && pytest -q
      - run: bash tests/test-manifests.sh
  dashboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20.19", cache: npm, cache-dependency-path: dashboard/package-lock.json }
      - run: cd dashboard && npm ci && npm run lint && npm test && npm run build
      - run: '! grep -rn "ODS" dashboard/src dashboard/index.html'
  compose-and-shell:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get install -y shellcheck
      - run: shellcheck -S error bin/ember tests/*.sh
      - run: bash tests/test-compose.sh
      - run: bash tests/test-doctor.sh
  images:
    runs-on: ubuntu-latest
    needs: [python, dashboard]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v6
        with: { context: ember-api, push: false, tags: ember-api:ci }
      - uses: docker/build-push-action@v6
        with: { context: dashboard, push: false, tags: ember-dashboard:ci }
```

- [ ] **Step 2: secret-scan.yml**

```yaml
name: secret-scan
on: [push, pull_request]
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
```

- [ ] **Step 3: Update pre-commit shellcheck paths** in `.pre-commit-config.yaml`: `files: ^(bin/ember|tests/.*\.sh)$` for both shellcheck hooks.

- [ ] **Step 4: Commit + push branch, confirm CI green**

```bash
git add .github .pre-commit-config.yaml
git commit -m "ci: python, dashboard, compose/shell and image build workflows"
git push -u origin feature/ember-lean-rebuild
gh run watch --exit-status || true
```

Expected: all four `ci` jobs + `secret-scan` green (fix and re-push if not).

---

