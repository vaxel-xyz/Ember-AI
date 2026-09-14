# jons-mac-mini

`jons-mac-mini` (Apple M4, 16 GB, macOS 26.6.2, `Mac16,10`) is the inference node. It runs
**oMLX 0.6.4** and **Hermes Agent** under launchd, with its own `cloudflared`. There is **no
Docker on the mini**, and Ember never deploys anything here — it is external and unmanaged
from Ember's point of view (`x_ember.managed: false` in `services/omlx/manifest.yaml`).

## oMLX

oMLX runs as the **DMG menu-bar app** (launchd label `application.app.omlx.*`), not a
service you `systemctl` or `docker` manage.

- Settings: `~/.omlx/settings.json` — `server.host` is now `0.0.0.0` (was `127.0.0.1` until
  the Phase 1 prerequisite P1 was applied on 2026-09-14), `auth.api_key` holds the bearer key
  LiteLLM authenticates with. `server_aliases` already lists `172.20.142.184`.
- Models directory: `~/.omlx/models/<org>/<name>`. The model id oMLX reports over `/v1/models`
  is the **folder name**, not the full `org/name` repo id.
- Restart / rescan: `~/.omlx/bin/omlx restart`. A restart is required for oMLX to pick up a
  newly downloaded model directory.
- Backup of the pre-P1 settings file: `~/.omlx/settings.json.bak-ember-20260914`.

Models on disk (2026-09-14): `srv-sngh/gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4`
(6.8 G), `ornith-ai/Ornith-1.5-9B-MLX-4bit` (4.7 G, default), `mlx-community/Qwen2.5-3B-Instruct-4bit`,
`mlx-community/parakeet-tdt-0.6b-v3` (STT), plus the embedding and TTS models added for Phase 1
(`bge-m3-mlx-8bit`, `Kokoro-82M-bf16`) — see [`docs/speech.md`](speech.md) and
[`docs/omlx.md`](omlx.md).

## Hermes

Hermes runs as two launchd services on the mini, independent of Ember:

- `ai.hermes.gateway` — LAN `:8642`.
- `ai.hermes.dashboard` — `127.0.0.1:9119`.

Config: `~/.hermes/config.yaml`. Primary provider is OpenRouter; fallback provider
`local-omlx` points at `http://127.0.0.1:8000/v1`, model Ornith. Ember does not manage or
restart Hermes — the only planned change to Hermes is the Phase 5 cutover, see
[`docs/hermes-cutover.md`](hermes-cutover.md).

## cloudflared

`cloudflared` runs locally on the mini as a system daemon, publishing `omlx.vaxel.xyz` and
`hermes-dashboard.vaxel.xyz`. This is separate from the Proxmox-host tunnel that fronts
`llm.vaxel.xyz` and `ember.vaxel.xyz` — see [`docs/cloudflare.md`](cloudflare.md).

## Memory guidance

The mini has 16 GB shared between oMLX, Hermes and Jon's desktop use — it is not a dedicated
inference box. oMLX's engine ceiling (`final_ceiling` in `/health`) is set well below the
nominal 16 GB for this reason: the TTS model choice for `ember-tts` was made partly on this
basis (Qwen3-TTS 1.7B was ruled out as too heavy alongside desktop workloads — see
[`docs/adr/0007-tts-via-omlx-model-open.md`](adr/0007-tts-via-omlx-model-open.md)). Before
loading a new model for evaluation, check `/health`'s `current_model_memory` and
`final_ceiling` rather than assuming headroom.
