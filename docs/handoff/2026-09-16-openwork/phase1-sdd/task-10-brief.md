### Task 10: Docs and ADRs

**Files:**
- Create: `README.md`, `docs/architecture.md`, `docs/deployment.md`, `docs/prox01.md`, `docs/mac-mini.md`, `docs/omlx.md`, `docs/litellm.md`, `docs/speech.md`, `docs/observability.md`, `docs/security.md`, `docs/cloudflare.md`, `docs/troubleshooting.md`, `docs/upstream-sync.md`, `docs/hermes-cutover.md`, `docs/adr/0003…0009`

Each doc is written from the spec sections named below; no placeholders. Mermaid where a diagram helps.

- [ ] **Step 1: README.md** — what Ember-AI is (spec §1, four-way split table), what it is not, quick start (`cp .env.example .env`, fill keys, `bin/ember up`, `bin/ember doctor`), URLs table (`llm.vaxel.xyz/v1`, `ember.vaxel.xyz`), alias table with current backing models, link to docs/ and DOWNSTREAM.md, attribution to ODS.

- [ ] **Step 2: docs/*.md**
  - `architecture.md` — spec §3 diagram as Mermaid + §4 component summaries + failure table §8.
  - `deployment.md` — Docker01 steps: `ssh vaxel-docker`, `git clone https://github.com/vaxel-xyz/Ember-AI /opt/stacks/ember`, `.env`, `bin/ember up`, `bin/ember doctor`, live validation procedure (chat, embed, stt with a WAV via `curl -F file=@… -F model=ember-stt $LLM/v1/audio/transcriptions`, tts via `/v1/audio/speech`), mini-off drill, rollback (`bin/ember down`; nothing else touched).
  - `prox01.md` — Docker01 facts (spec §2.1), RAM note (8 GB after reboot), stacks convention, ports.
  - `mac-mini.md` — oMLX DMG app, `~/.omlx/settings.json` (`server.host` now `0.0.0.0`, `auth.api_key`), `~/.omlx/bin/omlx restart`, models dir, rescan-on-restart, Hermes launchd labels, memory guidance (16 GB shared with desktop).
  - `omlx.md` — endpoints used, `/health` semantics → five states, model ids = folder names, downloading models with `uvx --from huggingface_hub hf download <repo> --local-dir ~/.omlx/models/<org>/<name>`.
  - `litellm.md` — template/render flow, alias table, virtual keys (`bin/ember keys create hermes`), `LLM_INTERNAL_URL` vs `LLM_PUBLIC_URL`, `turn_off_message_logging`.
  - `speech.md` — STT Parakeet v3, TTS Kokoro (blind-test result table from spec §4.7 run 1), voices (`/v1/audio/voices`), example requests.
  - `observability.md` — Phase 3 plan: Langfuse profile (donor compose at docs/donor), `LANGFUSE_ENABLED`, prompt-logging default off; today: LiteLLM spend logs.
  - `security.md` — spec §6.
  - `cloudflare.md` — spec §7; ingress fragment:

    ```yaml
    ingress:
      - hostname: llm.vaxel.xyz
        service: http://172.20.142.7:4000
      - hostname: ember.vaxel.xyz
        service: http://172.20.142.7:3001
    ```
    plus dashboard-UI steps and the Access-policy recommendation for `ember.`.
  - `troubleshooting.md` — each health state and what to do; `omlx restart`; LiteLLM 401/403; oMLX 401 (key mismatch); model not found (folder name vs repo id; restart to rescan).
  - `upstream-sync.md` — DOWNSTREAM.md procedure expanded.
  - `hermes-cutover.md` — Phase 5: change Hermes `~/.hermes/config.yaml` providers `local-omlx.base_url` → `http://172.20.142.7:4000/v1` with a virtual key, model `ember-local`; keep OpenRouter primary or switch to `ember-think`; rollback = restore `config.yaml.bak-*`; `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`.

- [ ] **Step 3: ADRs 0003–0009** (Context / Decision / Alternatives / Consequences each):
  - 0003 lean rebuild inside the fork, not overlay or fresh repo.
  - 0004 LiteLLM talks directly to LAN oMLX with bearer key; no model-router/switchboard/remote-provider/`LLM_BACKEND=external`.
  - 0005 external service model: manifests with `type: external` + `x_ember`, HTTP-only probing, no agent on the mini.
  - 0006 rerank routing — Status "Proposed" until Task 12 result; records that `bge-m3` is not a reranker (oMLX: "Use a SequenceClassification model").
  - 0007 TTS = Kokoro-82M-bf16 via oMLX (blind A/B numbers + Jon's verdict).
  - 0008 ember-api replaces dashboard-api/host-agent (20.8k + 12.8k lines → ≤2k, no Docker socket).
  - 0009 Hermes cutover only after Phase 1 validation, parallel integration first.

- [ ] **Step 4: Commit**

```bash
git add README.md docs
git commit -m "docs: Ember-AI architecture, deployment, operations and ADRs 0003-0009"
```

---

