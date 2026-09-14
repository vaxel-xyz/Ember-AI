# Observability

## Today: LiteLLM spend logs

Without the `observability` profile, LiteLLM's own Postgres (`litellm-postgres`) already
provides usage telemetry: `/spend/logs` and `/key/info` give requests, tokens, latency and
errors per virtual key and per alias. The dashboard's Clients/Usage view is built entirely on
this — no separate telemetry pipeline is needed for basic usage visibility.

## Phase 3 plan: Langfuse

The `observability` compose profile is not part of the Phase 1 stack. Its donor compose
fragment lives at [`docs/donor/langfuse-compose.yaml`](donor/langfuse-compose.yaml) (Langfuse
web + worker + Postgres + ClickHouse + Redis + MinIO, pinned versions) and will be adapted
into the Ember stack when it is enabled. It is gated on Docker01's RAM increase — see
[`docs/prox01.md`](prox01.md#ram-note) — since ClickHouse does not fit in the 3.8 GiB
available today alongside n8n.

When enabled:

- `LANGFUSE_ENABLED=true` makes the LiteLLM entrypoint append
  `success_callback: ["langfuse"]` to the rendered config.
- Prompt logging stays off by default: `EMBER_LOG_PROMPTS=false` (the current
  `LITELLM_TURN_OFF_MESSAGE_LOGGING=true` default) means `turn_off_message_logging: true` is
  set, so only metadata is sent to Langfuse, not prompt/response content.
- Request correlation: LiteLLM returns `x-litellm-call-id` to clients; a client-supplied
  `x-request-id` is forwarded as the Langfuse `trace_id` where supported.
- Hermes-side tracing (memory, tool calls, agent loops) is Hermes's own concern — Ember's
  Langfuse project only sees the LiteLLM hop, not what Hermes does with the response.

## Out of scope

Ember does not implement bespoke per-consumer dashboards, alerting or log shipping beyond
what LiteLLM's spend logs and (Phase 3) Langfuse provide. If Langfuse is down, LiteLLM keeps
serving requests — callback failures are non-blocking, and the dashboard simply shows
Langfuse as unhealthy.
