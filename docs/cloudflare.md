# Cloudflare

The tunnel lives on the **Proxmox host** (it routes the whole `172.20.142.0/24` range) —
nothing cloudflared-related ships in the Ember stack itself. Existing `omlx.vaxel.xyz` and
`hermes-dashboard.vaxel.xyz` (the mini's own, separate `cloudflared`) are unchanged.

## Required ingress

Add a public-hostname rule on the Proxmox tunnel:

```yaml
ingress:
  - hostname: ai.vaxel.xyz
    service: http://172.20.142.7:4000
  - hostname: chat.vaxel.xyz
    service: http://172.20.142.7:3003
  - hostname: ember.vaxel.xyz
    service: http://172.20.142.7:3001
```

`ai.vaxel.xyz` is required for remote/public LLM gateway access — the LAN URL
(`http://172.20.142.7:4000`) already works without it for anything on the local network.
`chat.vaxel.xyz` fronts the Open WebUI stack (separate from Ember; see
[`docs/open-webui.md`](open-webui.md) and [ADR 0010](adr/0010-frontend-routing-voice.md)).
`ember.vaxel.xyz` is optional; the dashboard also works purely over LAN.

Note: `ai.vaxel.xyz` was previously reserved for a separate OpenWork frontend; that plan is
dropped — the hostname now fronts the LiteLLM gateway ([ADR 0010](adr/0010-frontend-routing-voice.md)).

## Dashboard-UI steps

1. In the Cloudflare Zero Trust dashboard, open the tunnel already routing
   `172.20.142.0/24` on the Proxmox host.
2. Add a **Public Hostname**: `ai.vaxel.xyz` → service `http://172.20.142.7:4000`.
3. Add a second **Public Hostname**: `chat.vaxel.xyz` → service `http://172.20.142.7:3003`.
4. Add a third **Public Hostname** (optional): `ember.vaxel.xyz` → service
   `http://172.20.142.7:3001`.
5. Save. No changes are needed on Docker01 or the mini — all hostnames route to the
   existing tunnel process on Proxmox.

## Access policy recommendation

`ai.vaxel.xyz` is a machine-to-machine API and should stay open to bearer-key auth only —
do not put Cloudflare Access in front of it, or OpenAI-compatible clients (Hermes, OpenCode,
n8n) will be unable to authenticate.

`ember.vaxel.xyz` is a human administration surface with no user auth of its own (see
[`docs/security.md`](security.md#auth-model)), so it is recommended to put it behind a
**Cloudflare Access** policy scoped to Jon's identity before exposing it publicly. Until an
Access policy is configured, prefer accessing the dashboard over LAN
(`http://172.20.142.7:3001`) rather than publishing `ember.vaxel.xyz`.
