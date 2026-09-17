# ADR 0002: Use Parakeet v3 via oMLX for Ember-AI Speech-to-Text

**Status:** Accepted
**Date:** 2026-09-14
**Project:** `vaxel-xyz/Ember-AI`

## Context

The original ODS-derived Ember-AI architecture assumed Whisper as the speech-to-text (STT) engine.

Vaxel has selected **Parakeet v3** as the preferred speech recognition model for conversational interaction.

Parakeet can be served through the existing **oMLX** deployment on `jons-mac-mini`. Therefore, Ember-AI should not introduce and maintain a separate Parakeet inference service.

The existing oMLX deployment should remain the common Apple Silicon inference layer.

## Decision

**Replace Whisper as the default Ember-AI STT implementation with Parakeet v3 served by oMLX.**

The architecture shall be:

```text
Microphone / Voice Satellite
          │
          ▼
       Ember-AI
          │
          ▼
        oMLX
          │
          ▼
    Parakeet v3
          │
      transcript
          ▼
    Hermes / Ember
```

For response speech:

```text
Hermes / Ember
      │
      ▼
   Ember-AI
      │
      ▼
   TTS model (see ADR 0007)
      │
      ▼
    Speaker
```

## oMLX Ownership

`jons-mac-mini` remains the Apple-Silicon inference host.

```text
jons-mac-mini
      │
     oMLX
      │
      ├── LLM inference
      │
      └── Parakeet v3 STT
```

Ember-AI SHALL NOT deploy a separate Parakeet runtime where oMLX provides the required functionality.

This avoids duplicate:

- MLX runtime management;
- model lifecycle management;
- inference service processes;
- authentication;
- network APIs;
- health monitoring;
- Apple Silicon integration.

## Ember-AI Integration

Ember-AI should treat STT as another capability provided by oMLX.

The preferred flow is:

```text
Client
  │
  ▼
Ember-AI API
  │
  ▼
oMLX API
  │
  ▼
Parakeet v3
```

Consumers such as Hermes should not need to know that Parakeet is the underlying model.

Where practical, Ember-AI should expose a standard/OpenAI-compatible STT interface such as:

```text
POST /v1/audio/transcriptions
```

and proxy/route this to the appropriate oMLX capability.

Avoid creating translation layers where oMLX already exposes a sufficiently compatible API.

## Whisper

Whisper is no longer a required Ember-AI component.

Existing ODS Whisper implementation should be treated as donor/reference code only.

Reusable generic components MAY be retained, including:

- microphone/audio capture;
- audio upload handling;
- format validation/conversion;
- API abstractions;
- streaming infrastructure;
- telemetry;
- health/status UI.

Whisper-specific runtime and model-management code should be removed where it provides no value.

Do not retain Whisper solely for compatibility with ODS.

## Fallback Engines

The Ember-AI API boundary should remain implementation-independent enough to permit another STT engine in future.

However, do not build unnecessary multi-engine routing now.

Current decision:

```text
STT
 │
 ▼
oMLX
 │
 ▼
Parakeet v3
```

is the supported/default path.

## Dashboard

The Ember-AI administrative dashboard should represent STT as an oMLX-provided capability rather than pretending Parakeet is an independent infrastructure service.

For example:

```text
Local Inference
────────────────────────────

oMLX                   Healthy
Host                    jons-mac-mini

Capabilities
LLM                     Available
STT                     Available

STT
Model                    Parakeet v3
Provider                 oMLX
Requests                 <telemetry>
Latency                  <telemetry>
```

## Architectural Boundary

The resulting voice pipeline is:

```text
               EMBER VOICE

                  Speech
                    │
                    ▼
             ┌────────────┐
             │    oMLX    │
             │ Parakeet v3│
             └─────┬──────┘
                   │ text
                   ▼
             ┌────────────┐
             │   Hermes   │
             │   Ember    │
             └─────┬──────┘
                   │ text
                   ▼
             ┌────────────┐
             │ TTS model  │
             └─────┬──────┘
                   │ audio
                   ▼
                 Speech
```

Responsibilities remain:

**oMLX + Parakeet v3** — local speech recognition / Ember's ears.

**Hermes** — reasoning, memory, tools, skills, proactive behaviour and agent orchestration / Ember's brain.

**TTS model via oMLX** — speech synthesis / Ember's voice (model selection: ADR 0007).

**Ember-AI** — infrastructure, routing, API abstraction, observability and administration.

## Consequences

This decision simplifies the Ember-AI stack by consolidating local MLX inference behind oMLX.

It avoids operating a second MLX inference service solely for STT and further supports the lean-rebuild approach adopted for Ember-AI.

Implementation should prefer direct integration with the existing oMLX Parakeet capability and remove inherited ODS Whisper/runtime architecture that is no longer required.

## Verification (2026-09-14)

`mlx-community/parakeet-tdt-0.6b-v3` is present in `~/.omlx/models` on `jons-mac-mini` and is listed by oMLX 0.6.4 `/v1/models` as `parakeet-tdt-0.6b-v3`. End-to-end transcription through LiteLLM is validated in the Phase 1 deployment receipt (`docs/deployment.md`).
