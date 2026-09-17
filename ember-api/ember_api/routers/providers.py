import os

from fastapi import APIRouter, Depends

from ..security import require_api_key
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


@router.get("/providers")
async def providers(settings: Settings = Depends(get_settings)):  # noqa: B008
    return {"providers": [
        {"id": "omlx", "name": "oMLX (jons-mac-mini)", "configured": bool(settings.omlx_api_key), "base_url": settings.omlx_base_url},
        {"id": "openrouter", "name": "OpenRouter", "configured": bool(os.environ.get("OPENROUTER_API_KEY")),
         "model": os.environ.get("OPENROUTER_GLM_MODEL", "")},
    ], "gateway": {"public_url": settings.llm_public_url, "internal_url": settings.llm_internal_url}}
