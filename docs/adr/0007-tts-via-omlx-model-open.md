# ADR 0007: TTS model — Kokoro-82M-bf16 via oMLX

**Status:** Accepted
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

[ADR 0001](0001-vaxel-service-urls-ownership-network.md) §4 deliberately left the TTS model
choice open, pending benchmarking between candidate oMLX-supported models: `Kokoro-82M-bf16`,
`Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16`, and `Qwen3-TTS-12Hz-1.7B`. The 1.7B variant was dropped
before testing began — `jons-mac-mini` has 16 GB shared between oMLX, Hermes and Jon's desktop
use, so the effective usable ceiling is below the nominal ~10 GB the 1.7B model would need,
making it an impractical choice regardless of quality.

## Decision

**`Kokoro-82M-bf16`**, default voice `af_heart`. Chosen by a sighted-latency, blind-quality A/B
test (`tools/tts-blind-test.py`) between Kokoro and Qwen3-TTS 0.6B, run on the mini on
2026-09-14 against oMLX 0.6.4:

| Model | Resident memory | Latency per ~85-char sentence | Throughput |
|---|---|---|---|
| Kokoro-82M-bf16 | 0.34 GB | 0.36–0.44 s | ~200 chars/s |
| Qwen3-TTS-12Hz-0.6B | 1.90 GB | 3.7–5.0 s (≈ real-time) | ~19 chars/s |

Both models served cleanly via `/v1/audio/speech` (WAV) — this was not a viability filter, both
worked. The deciding factor was Jon's blind listening pass over 6 home-assistant-style
sentences with clip labels sealed until scored: a strong, consistent preference for Kokoro on
sentences 0, 1, 3 and 5, with Qwen3's `serena` voice specifically described as accented and
choppy. The preference held even with the mapping inverted for sentences 2 and 4, ruling out
position bias. `OMLX_TTS_MODEL=Kokoro-82M-bf16` is now the `.env.example` default, feeding
`ember-tts` through `config/litellm/ember.yaml.tmpl`.

## Alternatives

- **Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16.** Rejected on both axes: roughly 5.6× the memory
  footprint of Kokoro and roughly 10× the latency, for a result Jon judged less natural and
  more accented in blind listening. Kept unloaded on disk as a possible future alias target,
  not deleted, in case a different voice profile or use case favours it later.
- **Qwen3-TTS-12Hz-1.7B.** Rejected before benchmarking — memory footprint alone made it
  impractical on a 16 GB host shared with desktop workloads.
- **Deferring the decision further / running additional benchmark rounds.** Rejected: the
  preference in run 1 was strong and consistent across all six sentences including the
  inverted pair; further rounds would not change the outcome and would only delay Phase 1.

## Consequences

Ember ships no TTS model choice of its own — `OMLX_TTS_MODEL` is a plain `.env` value, and the
dashboard shows "TTS · Kokoro-82M-bf16 · oMLX" rather than an Ember-branded voice identity.
`/v1/audio/voices` continues to support both Kokoro-style voice directories and Qwen3-TTS
speaker tables without any Ember-side translation layer, so switching `OMLX_TTS_MODEL` later
(e.g. to try Qwen3-TTS again for a different use case) remains a one-line `.env` change, not a
code change.
