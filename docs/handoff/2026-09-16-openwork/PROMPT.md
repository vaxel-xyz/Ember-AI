You are continuing the Ember-AI build for Jon Howard-Totham overnight. Work in /Users/jtotham/Projects/Ember-AI.

Start here, in order, and read them fully before any command:
1. docs/handoff/2026-09-16-openwork/HANDOFF.md  — rules, context, how to work, where Jon is needed
2. docs/handoff/2026-09-16-openwork/STATE.md    — verified state of repo, hosts and live stack
3. docs/handoff/2026-09-16-openwork/SPEC.md     — binding design for this branch
4. docs/handoff/2026-09-16-openwork/PLAN.md     — execute Tasks 0–6 in order

Non-negotiable: the repo is PUBLIC — no secrets, keys or remote-access URLs in git or in your report; never touch the n8n/Portainer stacks or Hermes; never merge a PR; never poll LiteLLM GET /health; never rename the ember-* aliases; Open WebUI is a separate stack at /opt/stacks/openwebui, not part of the Ember compose file.

Working style: one task at a time; tests before code where the plan gives tests; one conventional commit per task; push and wait for CI (`gh run watch --exit-status`) before the next task; fix root causes, never weaken a gate. Keep docs/handoff/2026-09-16-openwork/REPORT.md updated after every task (commit SHAs, test tail, redacted live evidence, deviations, questions). If you get stuck twice on the same thing, or a step needs a credential you don't have, stop, write it in REPORT.md, and move to the next independent task.

Finish by opening a DRAFT PR from feature/frontend-routing-adr to main whose body is REPORT.md, and print its URL as your last line.
