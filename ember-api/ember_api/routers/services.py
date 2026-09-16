from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, Request

from ..litellm_client import LiteLLMClient
from ..security import require_api_key
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


def _strip_api_suffix(base: str) -> str:
    """`LLM_PUBLIC_URL` is the OpenAI-shaped API root (`.../v1`); the UI lives beside it."""
    base = base.rstrip("/")
    return base.removesuffix("/v1")


def _ui_url(svc, settings: Settings) -> str | None:
    """A URL a browser can actually open.

    Container hostnames (`litellm`, `qdrant`) only resolve inside the compose network, so a
    Docker service without a public URL is addressed via the Docker VM's LAN address — taken
    from the host part of `LLM_INTERNAL_URL` — on its published port.
    """
    if not svc.external_link:
        return None
    if svc.public_url:
        base = _strip_api_suffix(svc.public_url)
    else:
        host = urlsplit(settings.llm_internal_url).hostname or svc.host
        base = f"http://{host}:{svc.external_port}"
    return base + svc.ui_path


@router.get("/services")
async def services(request: Request, settings: Settings = Depends(get_settings)):  # noqa: B008
    reg = request.app.state.registry
    out = []
    for svc in reg.services.values():
        h = reg.health.get(svc.id)
        out.append({
            "id": svc.id, "name": svc.name, "node": svc.node, "role": svc.role, "managed": svc.managed,
            "type": svc.type, "category": svc.category, "capabilities": svc.capabilities,
            "state": h.state if h else "unknown", "reason": h.reason if h else "not polled yet",
            "latency_ms": h.latency_ms if h else None, "detail": h.detail if h else {}, "ui_url": _ui_url(svc, settings),
        })
    return {"polled_at": reg.polled_at.isoformat() if reg.polled_at else None, "services": out}


async def _deep_gateway_check(request: Request, settings: Settings) -> dict:
    """Run LiteLLM's per-deployment ``GET /health`` once, on demand.

    This issues a live call per deployment, which is why it is never in the poll loop.
    """
    svc = request.app.state.registry.services.get("litellm")
    base = f"http://{svc.host}:{svc.port}" if svc else settings.litellm_base_url
    lite = LiteLLMClient(base, settings.litellm_master_key, request.app.state.http)
    try:
        dep = await lite.deployment_health()
    except (httpx.HTTPError, ValueError) as exc:
        return {"ok": False, "error": exc.__class__.__name__}
    return {
        "ok": not dep.get("unhealthy_count", 0),
        "healthy_count": dep.get("healthy_count", 0),
        "unhealthy_count": dep.get("unhealthy_count", 0),
        "healthy_endpoints": dep.get("healthy_endpoints", []),
        "unhealthy_endpoints": dep.get("unhealthy_endpoints", []),
    }


@router.post("/services/refresh")
async def refresh(request: Request, deep: bool = False, settings: Settings = Depends(get_settings)):  # noqa: B008
    """Re-poll every service. ``?deep=true`` additionally runs the gateway deep check."""
    await request.app.state.registry.poll_once()
    out: dict = {"polled_at": datetime.now(UTC).isoformat(), "deep": deep}
    if deep:
        out["gateway"] = await _deep_gateway_check(request, settings)
    return out


@router.get("/nodes")
async def nodes(request: Request):
    reg = request.app.state.registry
    groups = {"docker01": "control-plane", "jons-mac-mini": "inference-node"}
    return {"nodes": [{"id": n, "role": r, "services": [s.id for s in reg.services.values() if s.node == n]} for n, r in groups.items()]}
