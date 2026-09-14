import os

from fastapi import APIRouter, Depends

from ..security import require_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])

REQUIRED_ENV = ["EMBER_API_KEY", "OMLX_BASE_URL", "OMLX_API_KEY", "OMLX_CHAT_MODEL", "OMLX_FAST_MODEL", "OMLX_CODE_MODEL",
                "OMLX_VISION_MODEL", "OMLX_EMBED_MODEL", "OMLX_STT_MODEL", "OMLX_TTS_MODEL", "OPENROUTER_THINK_MODEL",
                "LITELLM_MASTER_KEY"]


def run_checks() -> list[dict]:
    checks = [{"name": f"env:{k}", "ok": bool(os.environ.get(k)), "message": "set" if os.environ.get(k) else "missing"} for k in REQUIRED_ENV]
    base = os.environ.get("OMLX_BASE_URL", "")
    checks.append({"name": "omlx_base_url_is_lan_http", "ok": base.startswith(("http://172.", "http://10.", "http://192.168.")),
                   "message": base or "unset"})
    return checks


@router.get("/config/validate")
async def validate():
    checks = run_checks()
    return {"ok": all(c["ok"] for c in checks), "checks": checks}
