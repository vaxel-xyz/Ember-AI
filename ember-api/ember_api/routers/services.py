from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, Request

from ..litellm_client import LiteLLMClient
from ..security import require_api_key
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


def _ui_url(svc) -> str | None:
    if not svc.external_link:
        return None
    base = svc.public_url or f"http://{svc.host}:{svc.external_port}"
    return base.rstrip("/") + svc.ui_path


@router.get("/services")
async def services(request: Request):
    reg = request.app.state.registry
    out = []
    for svc in reg.services.values():
        h = reg.health.get(svc.id)
        out.append({
            "id": svc.id, "name": svc.name, "node": svc.node, "role": svc.role, "managed": svc.managed,
            "type": svc.type, "category": svc.category, "capabilities": svc.capabilities,
            "state": h.state if h else "unknown", "reason": h.reason if h else "not polled yet",
            "latency_ms": h.latency_ms if h else None, "detail": h.detail if h else {}, "ui_url": _ui_url(svc),
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
