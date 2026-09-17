### Task 12: Live deployment to Docker01 and validation

**Files:**
- Modify: `docs/deployment.md` (append "Validation receipt 2026-09-xx" table), `docs/adr/0006-rerank-routing.md` (status → Accepted with result)

**Interfaces:**
- Consumes: branch pushed (Task 11). Host access via ssh aliases `vaxel-docker`, `vaxel-mini`.

- [ ] **Step 1: Clone stack on Docker01 and create .env**

```bash
ssh vaxel-docker 'mkdir -p /opt/stacks && cd /opt/stacks && git clone -b feature/ember-lean-rebuild https://github.com/vaxel-xyz/Ember-AI ember && cd ember && cp .env.example .env && \
  sed -i "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)|; s|^EMBER_API_KEY=.*|EMBER_API_KEY=$(openssl rand -hex 24)|; s|^LITELLM_DB_PASSWORD=.*|LITELLM_DB_PASSWORD=$(openssl rand -hex 16)|" .env && chmod 600 .env && grep -c CHANGE_ME .env'
```

Expected: `2` (only `OMLX_API_KEY` and `OPENROUTER_API_KEY` remain). Then set them without echoing: read the oMLX key on the mini with `ssh vaxel-mini "python3 -c 'import json;print(json.load(open(\"/Users/jtotham/.omlx/settings.json\"))[\"auth\"][\"api_key\"])'"` and write it into `/opt/stacks/ember/.env` via `ssh vaxel-docker "sed -i 's|^OMLX_API_KEY=.*|OMLX_API_KEY=<value>|' /opt/stacks/ember/.env"` in one piped command so the value never lands in the transcript. Ask Jon for the OpenRouter key (or he pastes it into `.env` himself) — do not proceed to `ember-think` checks without it; everything else works.

- [ ] **Step 2: Bring the stack up**

```bash
ssh vaxel-docker 'cd /opt/stacks/ember && bin/ember up && sleep 40 && bin/ember status'
```

Expected: 4 containers `Up (healthy)` (postgres, litellm, ember-api, ember-dashboard). Memory check: `ssh vaxel-docker 'free -m; docker stats --no-stream --format "{{.Name}} {{.MemUsage}}"'` — total under the VM's available RAM.

- [ ] **Step 3: Doctor + live probes**

```bash
ssh vaxel-docker 'cd /opt/stacks/ember && bin/ember doctor'
```

Expected: all checks pass incl. `ember-auto completion` and `ember-embed vector length 1024`. Then from the laptop:

```bash
ssh vaxel-docker 'cd /opt/stacks/ember && set -a && . ./.env && set +a && \
 curl -s http://127.0.0.1:4000/v1/audio/speech -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
   -d "{\"model\":\"ember-tts\",\"input\":\"Ember is online.\",\"voice\":\"af_heart\",\"response_format\":\"wav\"}" -o /tmp/ember-tts.wav && ls -la /tmp/ember-tts.wav && \
 curl -s http://127.0.0.1:4000/v1/audio/transcriptions -H "Authorization: Bearer $LITELLM_MASTER_KEY" -F file=@/tmp/ember-tts.wav -F model=ember-stt'
```

Expected: WAV > 20 KB; transcription JSON containing "Ember is online". If LiteLLM rejects the audio route for the `openai/` custom base, record the exact error, then fall back to documenting direct oMLX `/v1/audio/*` for `ember-stt`/`ember-tts` in `docs/speech.md` and open an ADR note — do not build a proxy in this task.

- [ ] **Step 4: Dashboard + mini-off drill**

Open `http://172.20.142.7:3001` (Jon, or `curl -s http://172.20.142.7:3001/ | grep -o "<title>[^<]*"` → `Ember AI`). API via nginx: `curl -s http://172.20.142.7:3001/api/services | python3 -m json.tool | head -40` → omlx `healthy`/`degraded`, litellm `healthy`.

Drill (Jon approves timing): `ssh vaxel-mini '~/.omlx/bin/omlx stop'`; within 20 s `curl -s http://172.20.142.7:3001/api/services` shows omlx `unreachable` and litellm `degraded` (unhealthy deployments listed), dashboard still serves; `ssh vaxel-mini '~/.omlx/bin/omlx start'` → back to `degraded` then `healthy` after first request.

- [ ] **Step 5: Rerank probe (ADR 0006)**

On the mini: `uvx --from huggingface_hub hf download BAAI/bge-reranker-v2-m3 --local-dir ~/.omlx/models/BAAI/bge-reranker-v2-m3 && ~/.omlx/bin/omlx restart`. Then POST `/v1/rerank` with `{"model":"bge-reranker-v2-m3","query":"when do bins go out","documents":["Bins go out tonight.","Coffee is ready."],"top_n":1}` using the oMLX key. If 200 with `results`: set `OMLX_RERANK_MODEL=bge-reranker-v2-m3`, add to `ember.yaml.tmpl` an `ember-rerank` entry as `model: "jina_ai/${OMLX_RERANK_MODEL}", api_base: "${OMLX_BASE_URL}/v1"`, restart LiteLLM, probe `POST /rerank` on LiteLLM; if LiteLLM cannot route it, ADR 0006 records "ember-rerank served directly by oMLX `/v1/rerank`; LiteLLM route deferred". If oMLX rejects the model, ADR 0006 records that and leaves `ember-rerank` absent. Delete the model dir if unusable.

- [ ] **Step 6: Receipt + commit**

Append to `docs/deployment.md` a receipt table (date, branch sha, Docker01 RAM, containers, doctor output summary, chat/embed/stt/tts/rerank results, drill result). Update ADR 0006 status.

```bash
git add docs
git commit -m "docs: Phase 1 validation receipt and rerank ADR result"
git push
```

---

