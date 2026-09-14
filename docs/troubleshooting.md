# Troubleshooting

## Health states

| State | What it means | What to do |
|---|---|---|
| `healthy` | Reachable and functional. | Nothing. |
| `degraded` | Reachable but not functional — oMLX has `loaded_count == 0`, or LiteLLM readiness is fine but zero deployments are healthy. | For oMLX: usually harmless, the next request triggers an on-demand load. If it persists after a request, check `~/.omlx/bin/omlx restart` and confirm the model id in `.env` matches a folder under `~/.omlx/models`. For LiteLLM: check `docker compose logs litellm` for the deployment-specific error. |
| `starting` | oMLX returned HTTP 503 with `status: "loading"` (preloading pinned models). | Wait and re-poll; this should clear within the load time of the pinned models. |
| `reachable-unhealthy` | HTTP ≥ 400 outside the states above, or a non-JSON body. | Check the status code and body in `docker compose logs` (LiteLLM) or a manual `curl` against the service's health path; usually an auth or config error, not a network one. |
| `unreachable` | Connect failure, DNS failure, or timeout. | Confirm the host is up (`ping`/`ssh`), the port is open, and `OMLX_HOST`/`OMLX_BASE_URL` in `.env` match the mini's actual LAN IP. |

## Deep gateway check (on demand)

The `/api/services` poll loop only does a **shallow** gateway probe (`/health/readiness` +
`/model/info`) because LiteLLM's `GET /health` issues a live call per deployment. When you
need per-deployment truth, ask for it explicitly:

```bash
curl -sf -X POST "http://172.20.142.7:3002/api/services/refresh?deep=true" \
  -H "Authorization: Bearer $EMBER_API_KEY" | python3 -m json.tool
```

The `gateway` object in the response carries LiteLLM's `healthy_endpoints` /
`unhealthy_endpoints` lists. Expect non-chat deployments (embed, rerank, audio) to be
reported accurately only because the template pins `model_info.mode` on each of them; a
deployment reported unhealthy there is still worth confirming with a real request before
changing config. `bin/ember doctor` is the other deep path — it makes real `ember-auto` and
`ember-embed` calls.

Do not poll either of these on a timer. Doing so is what caused the Phase 1 incident where a
15 s loop fired ~10 inference requests at the mini every ~30 s.

## `omlx restart`

```bash
ssh jtotham@172.20.142.184
~/.omlx/bin/omlx restart
```

Use this whenever oMLX needs to rescan its models directory (after downloading a new model),
or after editing `~/.omlx/settings.json` (e.g. `server.host`, `auth.api_key`).

## LiteLLM 401 / 403

- **401** — no `Authorization` header, or the wrong key was sent as a virtual key when a
  master-key-only route was called. Confirm you are sending `Authorization: Bearer
  $LITELLM_MASTER_KEY` for admin routes (`/key/generate`, `/health` with auth) or a valid
  virtual key for `/v1/*` routes.
- **403** — a virtual key was recognised but is not permitted to call the requested model or
  has hit its budget/rate limit. Check `key_alias`/`max_budget` via `/key/info`, or mint a
  fresh key with `bin/ember keys create <client>`.

## oMLX 401 (key mismatch)

oMLX returns 401 on `/v1/*` when the bearer key does not match `auth.api_key` in
`~/.omlx/settings.json`. This usually means `OMLX_API_KEY` in Ember's `.env` is stale relative
to a key that was rotated on the mini. Compare the two directly (SSH into the mini and read
`~/.omlx/settings.json`) rather than guessing; update `.env` and re-run `bin/ember doctor`.

## Model not found

oMLX model ids are **folder names** under `~/.omlx/models/<org>/<name>`, not Hugging Face repo
ids. If `.env` has `OMLX_CHAT_MODEL=ornith-ai/Ornith-1.5-9B-MLX-4bit` instead of
`Ornith-1.5-9B-MLX-4bit`, LiteLLM will get a model-not-found error from oMLX. Check
`GET $OMLX_BASE_URL/v1/models` for the exact id oMLX reports, and if a model was recently
downloaded but isn't listed yet, run `~/.omlx/bin/omlx restart` to force a rescan.

## `ember doctor` failures

`bin/ember doctor` prints a plain reason for each failed check (missing env var, compose
config invalid, Qdrant running without a real API key, oMLX/LiteLLM/ember-api unreachable, or
a failed `ember-auto`/`ember-embed` call). Fix the specific reason it prints — it does not
aggregate beyond that.
