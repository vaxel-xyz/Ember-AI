### Task 13: Finish the branch

- [ ] **Step 1: Run the full local suite**: `bash tests/run.sh` → `ALL OK`.
- [ ] **Step 2: Self-review against spec §11 acceptance criteria** — tick each of the 9 items in the PR body with evidence (receipt table rows).
- [ ] **Step 3: Open PR (no merge)**

```bash
gh pr create --base main --head feature/ember-lean-rebuild --title "Ember-AI Phase 1: lean rebuild, LiteLLM→oMLX gateway, ember-api, dashboard" \
  --body-file <(printf '%s\n' "## Summary" "Lean rebuild of the ODS fork into Ember-AI shared AI infrastructure (see DOWNSTREAM.md, docs/adr)." "" "## Acceptance (spec §11)" "- [x] …(fill from receipt)" "" "🤖 Generated with [Claude Code](https://claude.com/claude-code)")
```

Report the PR URL. Do not merge.

---

## Self-review notes

- Spec coverage: §1–3 (Tasks 1, 2, 8), §4.1 (3, 8), §4.2 (4–6), §4.3–4.4 (2, 5), §4.5 (7), §4.6 (docs only — Phase 3 plan), §4.7 (3, 12), §4.8 (8 profile), §4.9 (9), §5 (1, 10), §6 (8, 11), §7 (10), §8 (5, 12 drill), §9 (3–9, 11), §10 Phase 1+2, §11 (12, 13), §12 verify-first items (12). Hermes cutover intentionally not executed (Phase 5).
- Types: `Service` fields used identically in Tasks 4–6; `ServiceHealth.state` values match `StatusBadge` keys; alias list in `routers/models.py` matches `ember.yaml.tmpl` (rerank added only in Task 12).
- Known dependency on live infra: Task 12 only. Tasks 0–11 run offline.
