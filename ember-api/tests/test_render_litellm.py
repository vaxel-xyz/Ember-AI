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
    "OMLX_STT_MODEL": "parakeet-tdt-0.6b-v3", "OMLX_TTS_MODEL": "Kokoro-82M-bf16", "OMLX_RERANK_MODEL": "bge-reranker-v2-m3",
    "OPENROUTER_THINK_MODEL": "z-ai/glm-5.3", "LITELLM_TURN_OFF_MESSAGE_LOGGING": "true",
}
TMPL = (ROOT / "config/litellm/ember.yaml.tmpl").read_text()


def test_render_substitutes_all_placeholders_and_is_valid_yaml():
    out = yaml.safe_load(render_config.render(TMPL, ENV))
    names = [m["model_name"] for m in out["model_list"]]
    assert names == ["ember-auto", "ember-local", "ember-fast", "ember-code", "ember-vision",
                     "ember-embed", "ember-rerank", "ember-stt", "ember-tts", "ember-think",
                     "local-fast", "local-smart", "heavy"]
    auto = out["model_list"][0]["litellm_params"]
    assert auto == {"model": "openai/Ornith-1.5-9B-MLX-4bit", "api_base": "http://172.20.142.184:8000/v1", "api_key": "os.environ/OMLX_API_KEY"}
    assert out["litellm_settings"]["turn_off_message_logging"] is True
    assert "${" not in render_config.render(TMPL, ENV)


def test_non_chat_aliases_declare_their_mode():
    """Without model_info.mode LiteLLM's deep health check falls back to a chat completion,

    which is what let the poll loop thrash the mini (see the C1 fix). Defence in depth:
    even an accidental deep check now hits the right endpoint per alias.
    """
    out = yaml.safe_load(render_config.render(TMPL, ENV))
    modes = {m["model_name"]: m.get("model_info", {}).get("mode") for m in out["model_list"]}
    assert modes["ember-embed"] == "embedding"
    assert modes["ember-rerank"] == "rerank"
    assert modes["ember-stt"] == "audio_transcription"
    assert modes["ember-tts"] == "audio_speech"
    tts = next(m for m in out["model_list"] if m["model_name"] == "ember-tts")
    assert tts["model_info"]["health_check_voice"] == "af_heart"
    for chat in ("ember-auto", "ember-local", "ember-fast", "ember-code", "ember-vision", "ember-think",
                 "local-fast", "local-smart", "heavy"):
        assert modes[chat] is None, f"{chat} is a chat route; it needs no explicit mode"


def test_human_aliases_share_targets_with_ember_aliases():
    out = yaml.safe_load(render_config.render(TMPL, ENV))
    by = {m["model_name"]: m["litellm_params"] for m in out["model_list"]}
    assert by["local-fast"] == by["ember-fast"]
    assert by["local-smart"] == by["ember-auto"]
    assert by["heavy"] == by["ember-think"]


def test_render_fails_loudly_on_missing_variable():
    with pytest.raises(KeyError, match="OMLX_TTS_MODEL"):
        render_config.render(TMPL, {k: v for k, v in ENV.items() if k != "OMLX_TTS_MODEL"})
