### Task 3: LiteLLM config template + renderer

**Files:**
- Create: `config/litellm/ember.yaml.tmpl`, `config/litellm/render-config.py`, `ember-api/tests/test_render_litellm.py` (tests live with the Python suite for one pytest run)

**Interfaces:**
- Produces: `render(template_text: str, env: Mapping[str,str]) -> str` and CLI `python3 render-config.py <tmpl> <out>`; env keys listed in Step 1.

- [ ] **Step 1: Template**

`config/litellm/ember.yaml.tmpl`:

```yaml
# Rendered at container start by render-config.py. ${VAR} placeholders come from the environment.
model_list:
  - model_name: ember-auto
    litellm_params: {model: "openai/${OMLX_CHAT_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-local
    litellm_params: {model: "openai/${OMLX_CHAT_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-fast
    litellm_params: {model: "openai/${OMLX_FAST_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-code
    litellm_params: {model: "openai/${OMLX_CODE_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-vision
    litellm_params: {model: "openai/${OMLX_VISION_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-embed
    litellm_params: {model: "openai/${OMLX_EMBED_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-stt
    litellm_params: {model: "openai/${OMLX_STT_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-tts
    litellm_params: {model: "openai/${OMLX_TTS_MODEL}", api_base: "${OMLX_BASE_URL}/v1", api_key: "os.environ/OMLX_API_KEY"}
  - model_name: ember-think
    litellm_params: {model: "openrouter/${OPENROUTER_THINK_MODEL}", api_key: "os.environ/OPENROUTER_API_KEY"}

router_settings:
  num_retries: 1
  timeout: 300

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/LITELLM_DATABASE_URL
  store_model_in_db: false

litellm_settings:
  drop_params: true
  request_timeout: 300
  turn_off_message_logging: ${LITELLM_TURN_OFF_MESSAGE_LOGGING}
```

- [ ] **Step 2: Failing test**

`ember-api/tests/test_render_litellm.py`:

```python
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("render_config", ROOT / "config/litellm/render-config.py")
render_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_config)

ENV = {
    "OMLX_BASE_URL": "http://172.20.142.184:8000", "OMLX_CHAT_MODEL": "Ornith-1.5-9B-MLX-4bit",
    "OMLX_FAST_MODEL": "Qwen2.5-3B-Instruct-4bit", "OMLX_CODE_MODEL": "gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4",
    "OMLX_VISION_MODEL": "gemma-4-12B-agentic-fable5-composer2.5-v2-nvfp4", "OMLX_EMBED_MODEL": "bge-m3-mlx-8bit",
    "OMLX_STT_MODEL": "parakeet-tdt-0.6b-v3", "OMLX_TTS_MODEL": "Kokoro-82M-bf16",
    "OPENROUTER_THINK_MODEL": "z-ai/glm-5.3", "LITELLM_TURN_OFF_MESSAGE_LOGGING": "true",
}
TMPL = (ROOT / "config/litellm/ember.yaml.tmpl").read_text()


def test_render_substitutes_all_placeholders_and_is_valid_yaml():
    out = yaml.safe_load(render_config.render(TMPL, ENV))
    names = [m["model_name"] for m in out["model_list"]]
    assert names == ["ember-auto", "ember-local", "ember-fast", "ember-code", "ember-vision",
                     "ember-embed", "ember-stt", "ember-tts", "ember-think"]
    auto = out["model_list"][0]["litellm_params"]
    assert auto == {"model": "openai/Ornith-1.5-9B-MLX-4bit", "api_base": "http://172.20.142.184:8000/v1", "api_key": "os.environ/OMLX_API_KEY"}
    assert out["litellm_settings"]["turn_off_message_logging"] is True
    assert "${" not in render_config.render(TMPL, ENV)


def test_render_fails_loudly_on_missing_variable():
    with pytest.raises(KeyError, match="OMLX_TTS_MODEL"):
        render_config.render(TMPL, {k: v for k, v in ENV.items() if k != "OMLX_TTS_MODEL"})
```

Run: `cd ember-api && python3 -m pytest tests/test_render_litellm.py -q` → Expected: FAIL (module missing). (Create `ember-api/` dir and an empty `tests/__init__.py` first if needed.)

- [ ] **Step 3: Renderer**

`config/litellm/render-config.py`:

```python
#!/usr/bin/env python3
"""Render ember.yaml.tmpl by substituting ${VAR} from the environment. Fails on any missing variable."""
import os
import sys
from string import Template
from typing import Mapping


def render(template_text: str, env: Mapping[str, str]) -> str:
    return Template(template_text).substitute(env)  # KeyError names the missing variable


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        rendered = render(f.read(), os.environ)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"rendered {src} -> {dst}")
```

- [ ] **Step 4: Run + commit**

Run: `cd ember-api && python3 -m pytest tests/test_render_litellm.py -q` → Expected: 2 passed.

```bash
git add config ember-api/tests
git commit -m "feat: LiteLLM ember.yaml template and renderer"
```

---

