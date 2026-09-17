# Open WebUI — reference deployment

Open WebUI is Vaxel's human-facing chat UI. It is a **separate stack** on Docker01 at
`/opt/stacks/openwebui` — deliberately **not** part of the Ember compose file
([ADR 0010](../../docs/adr/0010-frontend-routing-voice.md) §1). Ember only monitors it as an
external consumer (the `Consumers` tile on the dashboard); it never deploys or manages it.

Open WebUI never receives provider keys. It talks to the LiteLLM gateway over the LAN with a
single **virtual key** minted for it (`bin/ember keys create open-webui`), and sees the
human-facing aliases `local-fast`, `local-smart`, `local-code`, `local-vision` and
`cloud-fast`, `cloud-glm` and `cloud-gpt6` in its model picker.

## Deploy on Docker01

From the Ember checkout on Docker01 (`/opt/stacks/ember`):

```bash
mkdir -p /opt/stacks/openwebui
cp /opt/stacks/ember/deploy/openwebui/compose.yml /opt/stacks/openwebui/
cp /opt/stacks/ember/deploy/openwebui/.env.example /opt/stacks/openwebui/.env
```

(Or from the laptop: `scp -r deploy/openwebui vaxel-docker:/opt/stacks/openwebui`.)

Fill in `/opt/stacks/openwebui/.env` — two connections, one key per base URL
(ADR 0012):

```bash
cd /opt/stacks/openwebui
# 1st key: the LiteLLM virtual key (run from /opt/stacks/ember; capture without echoing)
k=$(bin/ember keys create open-webui --budget 20 | awk '/^key:/{print $2}')
# 2nd key: the Hermes API key, piped from the mini without echoing
h=$(ssh vaxel-mini 'grep "^API_SERVER_KEY=" ~/.hermes/.env' | cut -d= -f2)
sed -i "s|^OPENAI_API_KEYS=.*|OPENAI_API_KEYS=${k};${h}|" .env
sed -i "s|^WEBUI_SECRET_KEY=.*|WEBUI_SECRET_KEY=$(openssl rand -hex 32)|" .env
chmod 600 .env
docker compose up -d
```

The second connection is the **Hermes agent gateway** on the mini — a distinct agent backend,
deliberately not routed through LiteLLM ([ADR 0012](../../docs/adr/0012-hermes-openwebui-backend.md)).
It appears in the model picker as `hermes-agent`; agent turns can run long (the 1800 s
timeout matches Hermes's own gateway timeout).

Wait for the container to report healthy (`docker ps`), then check
`curl -s http://127.0.0.1:3003/health` returns 200.

## First admin, then lock signup

1. Open `https://chat.vaxel.xyz` (or `http://172.20.142.7:3003` over LAN) and create the
   first account — the first sign-up becomes the admin.
2. Then set `ENABLE_SIGNUP=false` in `.env` and `docker compose up -d` to apply.

## Operations

- **Backup:** the named volume `openwebui_open-webui-data` holds all state (users, chats,
  settings). Back it up like any Docker volume.
- **Model picker:** users see `local-fast`, `local-smart`, `local-code`, `local-vision` and
  `cloud-fast`/`cloud-glm`/`cloud-gpt6` (plus the `ember-*`
  aliases). `DEFAULT_MODELS: local-smart` makes the smart local model the default.
- **Keys:** if the LiteLLM virtual key needs rotating, mint a new one with
  `bin/ember keys create open-webui` and update the first `OPENAI_API_KEYS` entry +
  `docker compose up -d`. The Hermes key rotates on the mini (`~/.hermes/.env`) — update the
  second entry to match.
- **Ember's view:** the dashboard's `Consumers` group shows `open-webui` health, probed at
  `http://<OPENWEBUI_HOST>:3003/health`. It is `unreachable` when the stack is down — Ember
  does not start or stop it.
