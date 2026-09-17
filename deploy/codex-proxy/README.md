# Codex Proxy — ChatGPT-subscription bridge for `cloud-gpt6`

`codex-proxy` ([thezillo/codex-proxy](https://github.com/thezillo/codex-proxy), Apache-2.0,
pinned `v0.2.6`) exposes an OpenAI-compatible `/v1` backed by the **ChatGPT Codex
subscription** (OAuth, not platform API billing). Ember's gateway reaches it as an ordinary
OpenAI-compatible provider; the `cloud-gpt6` alias routes through it
([ADR 0011](../../docs/adr/0011-codex-subscription-provider.md)).

It is a **separate stack** on Docker01 at `/opt/stacks/codex-proxy` — not part of the Ember
compose file. Ember only monitors it (the `codex-proxy` tile) and calls it over the LAN.

## Deploy on Docker01

```bash
mkdir -p /opt/stacks/codex-proxy/data
cp /opt/stacks/ember/deploy/codex-proxy/compose.yml /opt/stacks/codex-proxy/
cp /opt/stacks/ember/deploy/codex-proxy/.env.example /opt/stacks/codex-proxy/.env
```

Seed the ChatGPT credentials (run on a machine with a logged-in Codex CLI, e.g. the mini;
the file travels over an ssh pipe and is never echoed):

```bash
ssh vaxel-docker 'cat > /opt/stacks/codex-proxy/data/auth.json && chmod 600 /opt/stacks/codex-proxy/data/auth.json' < ~/.codex/auth.json
```

Generate the client key and start:

```bash
cd /opt/stacks/codex-proxy
sed -i "s|^CODEX_PROXY_KEY=.*|CODEX_PROXY_KEY=$(openssl rand -hex 24)|" .env && chmod 600 .env
docker compose up -d
curl -s http://127.0.0.1:8787/health          # → 200, no auth
```

Then set the **same key** as `CODEX_PROXY_KEY` in `/opt/stacks/ember/.env` (plus
`CODEX_BASE_URL=http://172.20.142.7:8787` and `CODEX_GPT6_MODEL=gpt-6`) and
`bin/ember restart` so the gateway renders the `cloud-gpt6` route.

## Rules and caveats (ADR 0011)

- **Exactly one proxy instance per `data/`.** Two processes sharing `auth.json` rotate the
  refresh token against each other and produce intermittent 401s.
- **The Docker01 `data/auth.json` becomes the canonical credential** once seeded. Do not run
  the Codex CLI on the mini against the same account afterwards — the rotated refresh token
  on Docker01 wins, and the mini's copy goes stale.
- **Unofficial backend.** The proxy speaks to `chatgpt.com/backend-api`; that is outside
  OpenAI's ToS — worst case the account is flagged or rate-limited. Don't route anything
  irreplaceable through it.
- **Subscription quota is the ceiling.** Codex usage caps now bound everything sent to
  `cloud-gpt6`.
- **No audio.** The subscription covers the text Responses API only; `ember-stt`/`ember-tts`
  stay on oMLX.
- LAN-only by design (no Cloudflare hostname); the client key guards the API. Metrics stay
  on the container's loopback (not published).

## Operations

- **Ember's view:** the dashboard's docker01 group shows the `codex-proxy` tile, probed at
  `http://172.20.142.7:8787/health`. `unreachable` there means `cloud-gpt6` is down.
- **Model:** `CODEX_GPT6_MODEL` (default `gpt-6`; the proxy maps it to the current flagship
  slug). Available slugs are listed at `GET /v1/models` on the proxy.
- **Re-auth:** if the refresh token dies (account password change, session revocation),
  re-run `codex login` on the mini and re-seed `data/auth.json` (stop the container first —
  single-instance rule applies to the seed too).
