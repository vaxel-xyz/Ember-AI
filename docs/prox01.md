# Prox01 / Docker01

Prox01 is the Proxmox host. Ember-AI deploys to the existing **Docker VM** on Prox01
("Docker01"), as another Compose stack alongside n8n and Portainer. Home Assistant runs on a
separate VM and is not touched by Ember.

## Host facts (verified 2026-09-14, SSH, read-only)

| Fact | Value |
|---|---|
| Host | `root@172.20.142.7` |
| OS | Debian 13, kernel 6.12 |
| CPU | 4 vCPU |
| RAM | 3.8 GiB today; raised to ≥ 8 GB in Proxmox, applies on next VM reboot |
| Swap | 4 G |
| Free disk | 63 G |
| Docker | 29.8.0 |
| Compose | v5.5.1 |

## RAM note

The Phase 1 stack (LiteLLM + Postgres + ember-api + ember-dashboard, ~1–1.5 GB) fits in the
3.8 GiB available today. The Langfuse profile (Phase 3: ClickHouse + Postgres + Redis + MinIO
+ worker, 7 containers) will not fit alongside n8n until the VM is rebooted onto the 8 GB
allocation — the 8 GB change is set in Proxmox but only takes effect on the next reboot, so
the observability profile stays disabled until then.

## Stacks convention

Each stack lives at `/opt/stacks/<name>/compose.yml` (or `docker-compose.yml`). Existing:
`/opt/stacks/n8n/`, `/opt/stacks/portainer/`. Ember deploys to `/opt/stacks/ember/`.

Running today: n8n 2.38.5 (+ worker, runners, Postgres 18, Redis), n8n-mcp on host `:3000`,
Portainer `:9443`.

## Ports

| Port | Service | Notes |
|---|---|---|
| 3001 | `ember-dashboard` | `EMBER_DASHBOARD_PORT` |
| 3002 | `ember-api` | `EMBER_API_PORT` |
| 4000 | `litellm` | `LITELLM_PORT` |
| 6333 | `qdrant` | `QDRANT_PORT`, profile `qdrant` only |

These four ports were free on Docker01 before Ember was deployed. There is no `cloudflared`
on Docker01 — the Cloudflare tunnel that fronts `llm.vaxel.xyz` and `ember.vaxel.xyz` runs on
the Proxmox host itself and routes the whole `172.20.142.0/24` range. See
[`docs/cloudflare.md`](cloudflare.md).
