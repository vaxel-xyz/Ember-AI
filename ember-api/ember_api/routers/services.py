from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from ..security import require_api_key

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


@router.post("/services/refresh")
async def refresh(request: Request):
    await request.app.state.registry.poll_once()
    return {"polled_at": datetime.now(UTC).isoformat()}


@router.get("/nodes")
async def nodes(request: Request):
    reg = request.app.state.registry
    groups = {"docker01": "control-plane", "jons-mac-mini": "inference-node"}
    return {"nodes": [{"id": n, "role": r, "services": [s.id for s in reg.services.values() if s.node == n]} for n, r in groups.items()]}
