# Open WebUI — the human chat UI

Open WebUI is Vaxel's primary human-facing chat interface, at `https://chat.vaxel.xyz`
([ADR 0010](adr/0010-frontend-routing-voice.md) §1). It is a **separate stack** on Docker01 at
`/opt/stacks/openwebui` — not part of the Ember compose file. Ember's involvement is
deliberately thin: the dashboard shows it as an external **consumer** tile (health only), and
the gateway serves it like any other OpenAI-compatible client.

## Where it sits

```
browser ── chat.vaxel.xyz ── Cloudflare tunnel ──► Docker01 :3003 (open-webui container)
                                                      │
                                                      ▼  OpenAI-compatible, LAN, virtual key
                                              LiteLLM gateway :4000/v1  (ai.vaxel.xyz/v1)
                                                      │
                                                      ▼
                                    oMLX on jons-mac-mini  /  OpenRouter (cloud-glm)
```

- **Auth:** Open WebUI's own accounts (`WEBUI_AUTH=true`). It never sees provider keys — one
  LiteLLM **virtual key** minted for it (`bin/ember keys create open-webui`) is its only
  credential (ADR 0010 §13).
- **Models:** the picker shows the human-facing aliases `local-fast`, `local-smart`,
  `local-code`, `local-vision`, `cloud-fast`, `cloud-glm` and `cloud-gpt6` (plus the `ember-*` service aliases).
  `local-smart` is the default (`DEFAULT_MODELS`).
- **MCP:** configured inside Open WebUI (and Hermes) — never in ember-api (ADR 0010 §6).

## Hermes Agent backend

Alongside the Ember model aliases, Open WebUI has a **second, separate connection** to the
Hermes agent gateway on the mini (`http://172.20.142.184:8642/v1`, model `hermes-agent`) —
[ADR 0012](adr/0012-hermes-openwebui-backend.md). Hermes is an **execution agent**, not a
model: it is deliberately *not* routed through LiteLLM, keeps its own tool/terminal/browser
loop and its own model routing (OpenRouter primary, local oMLX fallback). Selecting
`hermes-agent` in the picker chats with the agent; turns can run long while it works.
Open WebUI's transcript and Hermes's own session store are both non-authoritative — durable
knowledge still belongs in the Projects workspace (shared-knowledge ADR). The Hermes
dashboard remains the administrative view of its sessions.

## Consumer tile

`services/open-webui/manifest.yaml` declares it `type: external`, `role: consumer`,
`managed: false`, probed at `http://<OPENWEBUI_HOST>:3003/health`. The dashboard groups it
under **Consumers**; `unreachable` there means the chat stack is down, and Ember will not
start or stop it. Reference deployment: [`deploy/openwebui/`](../deploy/openwebui/README.md).

## Install as a PWA

Open `https://chat.vaxel.xyz` in a browser, then use the browser's install option
(Safari: *File → Add to Dock*; Chrome/Edge: the install icon in the address bar). The app is
a PWA, so it gets its own window and dock icon.

## Backup

All state (users, chats, settings) lives in the `openwebui_open-webui-data` Docker volume on
Docker01. Back that volume up; nothing else in the stack is stateful.
