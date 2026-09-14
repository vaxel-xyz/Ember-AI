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
into the Ember stack when it is enabled. Docker01's RAM increase has landed — 7.8 GiB total,
~5.9 GiB available with the Phase 1 stack up (see [`docs/prox01.md`](prox01.md#ram-note)) — so
ClickHouse now fits alongside n8n. The profile stays disabled because Phase 3 has not started.

None of the variables below exist in `.env.example`, `.env.schema.json` or the code today —
they are the planned Phase 3 design, not a present feature. Verify with `git show
HEAD:.env.example` before assuming any of them are configurable yet. When Phase 3 lands, the
plan is:

- `LANGFUSE_ENABLED=true` (planned) would make the LiteLLM entrypoint append
  `success_callback: ["langfuse"]` to the rendered config.
- Prompt logging would stay off by default: a planned `EMBER_LOG_PROMPTS=false` (mirroring
  the current `LITELLM_TURN_OFF_MESSAGE_LOGGING=true` default) would keep
  `turn_off_message_logging: true` set, so only metadata is sent to Langfuse, not
  prompt/response content.
- Request correlation: LiteLLM already returns `x-litellm-call-id` to clients today; a
  client-supplied `x-request-id` would be forwarded as the Langfuse `trace_id` where
  supported.
- Hermes-side tracing (memory, tool calls, agent loops) is Hermes's own concern — Ember's
  Langfuse project would only see the LiteLLM hop, not what Hermes does with the response.

## Out of scope

Ember does not implement bespoke per-consumer dashboards, alerting or log shipping beyond
what LiteLLM's spend logs and (Phase 3) Langfuse provide. If Langfuse is down, LiteLLM keeps
serving requests — callback failures are non-blocking, and the dashboard simply shows
Langfuse as unhealthy.
