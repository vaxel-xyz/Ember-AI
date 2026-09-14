import os

import httpx
from fastapi import APIRouter, Depends, Request

from ..omlx import OmlxClient
from ..security import require_api_key
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])

ALIASES: list[tuple[str, str, str]] = [  # alias, provider, env var holding model id
    ("ember-auto", "omlx", "OMLX_CHAT_MODEL"), ("ember-local", "omlx", "OMLX_CHAT_MODEL"), ("ember-fast", "omlx", "OMLX_FAST_MODEL"),
    ("ember-code", "omlx", "OMLX_CODE_MODEL"), ("ember-vision", "omlx", "OMLX_VISION_MODEL"), ("ember-embed", "omlx", "OMLX_EMBED_MODEL"),
    ("ember-stt", "omlx", "OMLX_STT_MODEL"), ("ember-tts", "omlx", "OMLX_TTS_MODEL"), ("ember-think", "openrouter", "OPENROUTER_THINK_MODEL"),
]
CAPABILITY_ENV = {"llm": "OMLX_CHAT_MODEL", "vision": "OMLX_VISION_MODEL", "embeddings": "OMLX_EMBED_MODEL",
                  "rerank": "OMLX_RERANK_MODEL", "stt": "OMLX_STT_MODEL", "tts": "OMLX_TTS_MODEL"}


async def _omlx_models(request: Request, settings: Settings) -> list[dict]:
    client: httpx.AsyncClient = request.app.state.http
    omlx = OmlxClient(settings.omlx_base_url, settings.omlx_api_key, client)
    try:
        return await omlx.models_status()
    except httpx.HTTPError:
        return []


@router.get("/models")
async def models(request: Request, settings: Settings = Depends(get_settings)):  # noqa: B008
    omlx_models = await _omlx_models(request, settings)
    by_id = {m.get("id"): m for m in omlx_models}
    aliases = []
    for alias, provider, env_key in ALIASES:
        model = os.environ.get(env_key, "")
        m = by_id.get(model) if provider == "omlx" else None
        aliases.append({
            "alias": alias, "provider": provider, "model": model,
            "resident": (bool(m.get("loaded")) if m else (False if provider == "omlx" and omlx_models else None)),
            "estimated_size_gb": round(m["estimated_size"] / 1e9, 2) if m and m.get("estimated_size") else None,
        })
    return {"aliases": aliases, "omlx_models": [{"id": m.get("id"), "loaded": bool(m.get("loaded")),
             "estimated_size_gb": round(m["estimated_size"] / 1e9, 2) if m.get("estimated_size") else None} for m in omlx_models]}


@router.get("/capabilities")
async def capabilities(request: Request):
    reg = request.app.state.registry
    omlx_state = reg.health["omlx"].state if "omlx" in reg.health else "unknown"
    return {"capabilities": {cap: {"provider": "omlx", "state": omlx_state, "model": os.environ.get(env_key, "")}
                             for cap, env_key in CAPABILITY_ENV.items() if os.environ.get(env_key)}}
