# Cloudflare

The tunnel lives on the **Proxmox host** (it routes the whole `172.20.142.0/24` range) —
nothing cloudflared-related ships in the Ember stack itself. Existing `omlx.vaxel.xyz` and
`hermes-dashboard.vaxel.xyz` (the mini's own, separate `cloudflared`) are unchanged.

## Required ingress

Add a public-hostname rule on the Proxmox tunnel:

```yaml
ingress:
  - hostname: llm.vaxel.xyz
    service: http://172.20.142.7:4000
  - hostname: ember.vaxel.xyz
    service: http://172.20.142.7:3001
```

`llm.vaxel.xyz` is required for remote/public LLM gateway access — the LAN URL
(`http://172.20.142.7:4000`) already works without it for anything on the local network.
`ember.vaxel.xyz` is optional; the dashboard also works purely over LAN.

## Dashboard-UI steps

1. In the Cloudflare Zero Trust dashboard, open the tunnel already routing
   `172.20.142.0/24` on the Proxmox host.
2. Add a **Public Hostname**: `llm.vaxel.xyz` → service `http://172.20.142.7:4000`.
3. Add a second **Public Hostname** (optional): `ember.vaxel.xyz` → service
   `http://172.20.142.7:3001`.
4. Save. No changes are needed on Docker01 or the mini — both hostnames route to the
   existing tunnel process on Proxmox.

## Access policy recommendation

`llm.vaxel.xyz` is a machine-to-machine API and should stay open to bearer-key auth only —
do not put Cloudflare Access in front of it, or OpenAI-compatible clients (Hermes, OpenCode,
n8n) will be unable to authenticate.

`ember.vaxel.xyz` is a human administration surface with no user auth of its own (see
[`docs/security.md`](security.md#auth-model)), so it is recommended to put it behind a
**Cloudflare Access** policy scoped to Jon's identity before exposing it publicly. Until an
Access policy is configured, prefer accessing the dashboard over LAN
(`http://172.20.142.7:3001`) rather than publishing `ember.vaxel.xyz`.
