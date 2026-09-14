# Speech

STT and TTS are both **oMLX capabilities**, exposed by Ember only as `ember-stt` / `ember-tts`
through LiteLLM's OpenAI-compatible `/v1/audio/transcriptions` and `/v1/audio/speech`
passthrough. There is no `voice.vaxel.xyz`, no separate voice service, and no Ember
translation layer — see [ADR 0002](adr/0002-stt-parakeet-via-omlx.md).

## STT: Parakeet v3

`mlx-community/parakeet-tdt-0.6b-v3`, model id `parakeet-tdt-0.6b-v3`. Already on the mini,
verified end-to-end through oMLX and then through LiteLLM (`ember-stt`).

## TTS: Kokoro-82M-bf16

Decided by a blind A/B test between `mlx-community/Kokoro-82M-bf16` and
`mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16` (the 1.7B Qwen3-TTS variant was dropped
before testing — the mini also carries desktop workloads, so the effective ceiling is below
the nominal ~10 GB). Protocol: `tools/tts-blind-test.py`, run on the mini, stdlib only, key
read from `~/.omlx/settings.json`; 6 home-assistant-style sentences synthesised through each
model via `/v1/audio/speech`; per-model load time, memory delta (`/health`), per-sentence
latency and chars/s recorded; clips relabelled A/B with a per-sentence shuffle, mapping sealed
until scored; `--reveal` prints the mapping and median latency.

**Run 1 (2026-09-14, oMLX 0.6.4, voices `af_heart` vs `serena`):**

| Model | Resident memory | Latency per ~85-char sentence | Throughput |
|---|---|---|---|
| Kokoro-82M-bf16 | 0.34 GB | 0.36–0.44 s | ~200 chars/s |
| Qwen3-TTS-12Hz-0.6B | 1.90 GB | 3.7–5.0 s | ~19 chars/s (≈ real-time) |

Both served cleanly via `/v1/audio/speech` (WAV). Blind listen (Jon, same day): strong
preference for Kokoro on sentences 0/1/3/5; Qwen3 `serena` was described as accented and
choppy. The preference held across all sentences including the inverted 2/4 pair.

**Decision:** `Kokoro-82M-bf16`, default voice `af_heart` (British `bf_*`/`bm_*` voices also
available). `OMLX_TTS_MODEL=Kokoro-82M-bf16` in `.env`. Qwen3-TTS 0.6B stays on disk, unloaded,
as a possible future alias target. Full rationale in
[ADR 0007](adr/0007-tts-via-omlx-model-open.md).

## Voices

```bash
curl -s -H "Authorization: Bearer $OMLX_API_KEY" \
  "$OMLX_BASE_URL/v1/audio/voices?model=Kokoro-82M-bf16"
```

`/v1/audio/voices` reads Kokoro-style voice directories and Qwen3-TTS speaker tables, so both
model shapes are supported without a translation layer.

## Example requests

Through LiteLLM (`$LLM` = `http://172.20.142.7:4000` or `https://llm.vaxel.xyz/v1`):

```bash
# Transcription (ember-stt)
curl -s -F file=@sample.wav -F model=ember-stt \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  "$LLM/v1/audio/transcriptions"

# Speech synthesis (ember-tts)
curl -s "$LLM/v1/audio/speech" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"ember-tts","input":"Ember is online.","voice":"af_heart"}' \
  --output reply.wav
```
