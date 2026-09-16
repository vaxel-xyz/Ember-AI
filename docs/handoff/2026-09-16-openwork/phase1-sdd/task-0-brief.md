### Task 0: Branch, remote, worktree, ADR relocation

**Files:**
- Create: `docs/adr/0001-vaxel-service-urls-ownership-network.md` (moved), `docs/adr/0002-stt-parakeet-via-omlx.md`

**Interfaces:**
- Produces: branch `feature/ember-lean-rebuild`; remote `upstream`.

- [ ] **Step 1: Branch + upstream remote**

```bash
cd /Users/jtotham/Projects/Ember-AI
git remote add upstream https://github.com/Osmantic/ODS.git || true
git fetch upstream --tags --quiet
git checkout -b feature/ember-lean-rebuild main
```

- [ ] **Step 2: Move Jon's URL ADR into docs/adr and add the STT ADR**

```bash
mkdir -p docs/adr
git mv "ADR — Vaxel Service URLs, Ownership and Network Architecture.md" docs/adr/0001-vaxel-service-urls-ownership-network.md
```

Create `docs/adr/0002-stt-parakeet-via-omlx.md` with the exact ADR text Jon supplied in chat (title "Use Parakeet v3 via oMLX for Ember-AI Speech-to-Text", Status Accepted, Date 2026-09-14). It is reproduced in spec §4.7 summary; the executor copies the full text from `/Users/jtotham/Projects/superpowers/specs/2026-09-14-ember-ai-design.md` §4.7 context and the chat transcript file if present at `docs/adr/` — if the full text is unavailable, write Context/Decision/Consequences from spec §4.7 verbatim and mark "Reconstructed from spec".

- [ ] **Step 3: Commit**

```bash
git add -A docs/adr
git commit -m "docs: relocate Vaxel URL/ownership ADR and add STT ADR"
```

---

