"""Logical model aliases Ember publishes through the LiteLLM gateway.

Lives in its own module so the health probe can compare the gateway's
registered alias set against it without importing the routers package.
"""

ALIASES: list[tuple[str, str, str]] = [  # alias, provider, env var holding model id
    ("ember-auto", "omlx", "OMLX_CHAT_MODEL"), ("ember-local", "omlx", "OMLX_CHAT_MODEL"), ("ember-fast", "omlx", "OMLX_FAST_MODEL"),
    ("ember-code", "omlx", "OMLX_CODE_MODEL"), ("ember-vision", "omlx", "OMLX_VISION_MODEL"), ("ember-embed", "omlx", "OMLX_EMBED_MODEL"),
    ("ember-rerank", "omlx", "OMLX_RERANK_MODEL"),
    ("ember-stt", "omlx", "OMLX_STT_MODEL"), ("ember-tts", "omlx", "OMLX_TTS_MODEL"), ("ember-think", "openrouter", "OPENROUTER_THINK_MODEL"),
    ("local-fast", "omlx", "OMLX_FAST_MODEL"), ("local-smart", "omlx", "OMLX_CHAT_MODEL"), ("heavy", "openrouter", "OPENROUTER_THINK_MODEL"),
]

ALIAS_NAMES: list[str] = [a for a, _, _ in ALIASES]
