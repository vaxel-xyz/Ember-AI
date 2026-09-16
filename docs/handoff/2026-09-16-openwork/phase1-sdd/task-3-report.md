# Task 3 Report: LiteLLM config template + renderer

## What was done

Created three files per the brief plus the required test-package scaffold, following TDD (RED then GREEN):

- `config/litellm/ember.yaml.tmpl` — LiteLLM config template with `${VAR}` placeholders for the 9 model aliases (`ember-auto`, `ember-local`, `ember-fast`, `ember-code`, `ember-vision`, `ember-embed`, `ember-stt`, `ember-tts`, `ember-think`), router/general/litellm settings, and `os.environ/...` literals for secrets.
- `config/litellm/render-config.py` — `render(template_text, env) -> str` using `string.Template.substitute` (raises `KeyError` naming the missing var), plus a `python3 render-config.py <tmpl> <out>` CLI.
- `ember-api/tests/test_render_litellm.py` — the two tests from the brief, verbatim.
- `ember-api/tests/__init__.py` — empty, created per instructions so the test path works ahead of Task 4's `pyproject.toml`.

## Deviation from the brief (found via TDD RED, not guessed)

The brief's template header comment, taken verbatim, was:
```
# Rendered at container start by render-config.py. ${VAR} placeholders come from the environment.
```
This is a bug in the brief text itself: `string.Template.substitute` operates on the *entire* template text, including comments — it doesn't know `${VAR}` in a comment is meant as prose describing the syntax rather than an actual placeholder. Running the test first (as TDD requires) surfaced this immediately:

1. First attempt (comment left as-is) → `KeyError: 'VAR'` on both tests, because `VAR` isn't a real key in `ENV`.
2. I tried escaping it as `$${VAR}` (Template's escape for a literal `$`) — this fixed the `KeyError`, but then failed test 1's `assert "${" not in render_config.render(TMPL, ENV)`, because `$${VAR}` renders back to the literal string `${VAR}`, which still contains `${`.
3. Since the brief's own test asserts **zero** `${` survives in rendered output, no literal `${VAR}` text — escaped or not — can appear anywhere in the template, including comments. I reworded the comment to drop the `${VAR}` notation entirely:
   ```
   # Rendered at container start by render-config.py. Placeholders come from the environment.
   ```
   This preserves the comment's meaning without using template syntax literally. No other line was touched — the rest of the template (all 9 model blocks, `router_settings`, `general_settings`, `litellm_settings`) matches the brief exactly, character-for-character.

This is the only deviation from the brief. It was necessary because the brief's two hard requirements (no `KeyError` on real vars, zero leftover `${` post-render) are mutually incompatible with a comment that contains the literal substring `${VAR}` under Python's `string.Template` semantics — there is no way to satisfy both without changing the comment's wording.

## TDD evidence

### RED (module missing)
```
$ source .venv/bin/activate && cd ember-api && python3 -m pytest tests/test_render_litellm.py -q
==================================== ERRORS ====================================
________________ ERROR collecting tests/test_render_litellm.py _________________
tests/test_render_litellm.py:10: in <module>
    spec.loader.exec_module(render_config)
...
E   FileNotFoundError: [Errno 2] No such file or directory: '/Users/jtotham/Projects/Ember-AI/config/litellm/render-config.py'
=========================== short test summary info ============================
ERROR tests/test_render_litellm.py - FileNotFoundError: [Errno 2] No such fil...
1 error in 0.08s
```

### Intermediate RED (after writing template+renderer verbatim from brief — caught the comment bug)
```
F.                                                                       [100%]
FAILED ...::test_render_substitutes_all_placeholders_and_is_valid_yaml
E           KeyError: 'VAR'
FAILED ...::test_render_fails_loudly_on_missing_variable
E           Regex pattern did not match. Expected regex: 'OMLX_TTS_MODEL'. Actual message: "'VAR'"
2 failed in 0.04s
```

After escaping to `$${VAR}`:
```
F.                                                                       [100%]
FAILED ...::test_render_substitutes_all_placeholders_and_is_valid_yaml
E       assert "${" not in render_config.render(TMPL, ENV)
E       AssertionError: '${' is contained here: ...${VAR} placeholders come from the environment.
1 failed, 1 passed in 0.04s
```

### GREEN (after rewording the comment)
```
$ source .venv/bin/activate && cd ember-api && python3 -m pytest tests/test_render_litellm.py -q
..                                                                       [100%]
2 passed in 0.02s
```
Also confirmed from repo root (per the R3 fallback instruction):
```
$ source .venv/bin/activate && python3 -m pytest ember-api/tests/test_render_litellm.py -q
..                                                                       [100%]
2 passed in 0.02s
```
(No cwd/import issue was actually hit in this environment — both invocation styles pass — but both were verified as instructed.)

## CLI end-to-end run

```
$ env OMLX_BASE_URL="http://172.20.142.184:8000" OMLX_CHAT_MODEL="Ornith-1.5-9B-MLX-4bit" \
      OMLX_FAST_MODEL="Qwen2.5-3B-Instruct-4bit" OMLX_CODE_MODEL="gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4" \
      OMLX_VISION_MODEL="gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4" OMLX_EMBED_MODEL="bge-m3-mlx-8bit" \
      OMLX_STT_MODEL="parakeet-tdt-0.6b-v3" OMLX_TTS_MODEL="Kokoro-82M-bf16" \
      OPENROUTER_THINK_MODEL="z-ai/glm-5.3" LITELLM_TURN_OFF_MESSAGE_LOGGING="true" \
      python3 config/litellm/render-config.py config/litellm/ember.yaml.tmpl /tmp/.../ember-rendered.yaml
rendered config/litellm/ember.yaml.tmpl -> /tmp/.../ember-rendered.yaml
```
Parse check:
```
$ python3 -c "import yaml,sys; d=yaml.safe_load(open('.../ember-rendered.yaml')); print('parsed OK, model count:', len(d['model_list']))"
parsed OK, model count: 9
```
Rendered output inspected manually: all 9 `model_name` entries present in the required order, all `${...}` placeholders substituted, all `os.environ/...` strings preserved literally (`OMLX_API_KEY`, `OPENROUTER_API_KEY`, `LITELLM_MASTER_KEY`, `LITELLM_DATABASE_URL`), `turn_off_message_logging: true` rendered as a bare (boolean) YAML value.

## Files changed

- `config/litellm/ember.yaml.tmpl` (new)
- `config/litellm/render-config.py` (new)
- `ember-api/tests/test_render_litellm.py` (new)
- `ember-api/tests/__init__.py` (new, empty)

Commit: `114653a75` — "feat: LiteLLM ember.yaml template and renderer" (exact message from the brief).

## Self-review

- Alias order verified with `grep 'model_name:' config/litellm/ember.yaml.tmpl` — exact match to `ember-auto, ember-local, ember-fast, ember-code, ember-vision, ember-embed, ember-stt, ember-tts, ember-think`.
- No `${` survives after render — asserted by the test and independently confirmed on the manually-rendered CLI output.
- Missing-variable case raises `KeyError` naming the missing variable (test 2, matches `OMLX_TTS_MODEL` via regex).
- Only the files listed above were created; `ruff` was not installed, so lint was skipped per instructions, but code was kept minimal/PEP8-clean by inspection (renderer is the same file content as the brief, template only had its comment line changed).
- `git status --short` is clean after the commit — no stray files, no `ember-api` files beyond `tests/__init__.py` and the one test file, `pyproject.toml` intentionally not created (Task 4's job).

## Concerns

- The one deviation (rewording the template's header comment) is a genuine bug fix surfaced by following the brief's own TDD instructions to the letter — not a guess or a stylistic change. Flagging it explicitly in case downstream tasks (6, 8, 9) or reviewers expect the comment text verbatim from the original spec; the substituted wording preserves intent ("placeholders come from the environment") without breaking the render/test contract.
- No other blockers or open questions.
