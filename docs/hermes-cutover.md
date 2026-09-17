# Hermes cutover (Phase 5)

**This is Phase 5 work, not part of Phase 1.** Hermes keeps talking to oMLX directly
(`local-omlx` → `http://127.0.0.1:8000/v1`) as its fallback provider until Phase 1 is fully
validated on Docker01 (`bin/ember doctor` green, dashboard showing real 5-state health, the
mini-off drill behaving as documented) — see
[ADR 0009](adr/0009-hermes-cutover-after-validation.md). Nothing in this document should be
carried out until that validation is complete and Jon has approved moving to Phase 5.

## Cutover

On `jons-mac-mini`, edit `~/.hermes/config.yaml` and change the `local-omlx` provider's
`base_url` from `http://127.0.0.1:8000/v1` to Ember's LiteLLM gateway, with a LiteLLM virtual
key instead of the raw oMLX key, and point the model at the `local-smart` alias rather than a
concrete oMLX model id:

```yaml
providers:
  local-omlx:
    base_url: http://172.20.142.7:4000/v1
    api_key: <virtual key from `bin/ember keys create hermes`>
    model: local-smart
```

Hermes's primary provider (OpenRouter) can either stay as-is, or be switched to route through
Ember's `cloud-smart` alias instead of calling OpenRouter directly — both are acceptable;
whichever is chosen, `local-omlx` (renamed or not) becomes Ember-backed rather than
oMLX-direct.

Apply the change:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway
```

## Validation after cutover

Confirm Hermes can still reach a model through the new path (ask it something that requires
the local/fallback provider), and check Ember's dashboard Clients/Usage page for a `hermes`
virtual key showing real request volume — this is the point at which Hermes becomes a visible
Ember consumer rather than an invisible direct oMLX client.

## Rollback

Every cutover edit to `~/.hermes/config.yaml` should be preceded by a timestamped backup:

```bash
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak-$(date +%Y%m%d%H%M)
```

To roll back, restore the backup and kick the service:

```bash
cp ~/.hermes/config.yaml.bak-<timestamp> ~/.hermes/config.yaml
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway
```

This restores Hermes to talking to oMLX directly on `127.0.0.1:8000`, with no dependency on
Ember or Docker01 — the same fallback path Hermes uses today, before any cutover work begins.
Rolling back does not require any change to Ember itself; Ember's LiteLLM gateway keeps
serving other consumers unaffected either way.
