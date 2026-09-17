### Task 6: ember-api app, routers, poll loop, Dockerfile

**Files:**
- Create: `ember-api/ember_api/main.py`, `ember-api/ember_api/routers/__init__.py`, `ember-api/ember_api/routers/services.py`, `ember-api/ember_api/routers/models.py`, `ember-api/ember_api/routers/providers.py`, `ember-api/ember_api/routers/config.py`, `ember-api/Dockerfile`, `ember-api/tests/test_api.py`

**Interfaces:**
- Produces HTTP (all under `/api`, bearer `EMBER_API_KEY` except `/api/health`):
  - `GET /api/health` → `{"status":"ok","version":"0.1.0"}`
  - `GET /api/services` → `{"polled_at": iso, "services": [ {id,name,node,role,managed,type,category,state,reason,latency_ms,detail,ui_url} ]}`
  - `GET /api/nodes` → `{"nodes": [{"id":"docker01","role":"control-plane","services":[ids]},{"id":"jons-mac-mini","role":"inference-node","services":[ids]}]}`
  - `GET /api/capabilities` → `{"capabilities": {"llm": {"provider":"omlx","state":...,"model":OMLX_CHAT_MODEL}, "stt": {...,"model":OMLX_STT_MODEL}, ...}}`
  - `GET /api/models` → `{"aliases": [{alias, provider, model, resident: bool|null, estimated_size_gb: float|null}], "omlx_models": [...]}`
  - `GET /api/providers` → `{"providers":[{"id":"omlx","configured":true,"base_url":...},{"id":"openrouter","configured":bool}]}` (never echo keys)
  - `GET /api/config/validate` → `{"ok": bool, "checks": [{name, ok, message}]}`

- [ ] **Step 1: Failing API tests**

`ember-api/tests/test_api.py`:

```python
import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import ember_api.main as main_mod


@pytest.fixture
def client(monkeypatch, env, services_dir):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("EMBER_SERVICES_DIR", str(services_dir))
    monkeypatch.setenv("OMLX_CHAT_MODEL", "Ornith-1.5-9B-MLX-4bit")
    monkeypatch.setenv("OMLX_STT_MODEL", "parakeet-tdt-0.6b-v3")
    monkeypatch.setenv("OMLX_TTS_MODEL", "Kokoro-82M-bf16")
    monkeypatch.setenv("OMLX_EMBED_MODEL", "bge-m3-mlx-8bit")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("EMBER_POLL_ON_START", "false")
    main_mod.get_settings.cache_clear()
    app = main_mod.create_app()
    with TestClient(app) as c:
        yield c


AUTH = {"Authorization": "Bearer test-key"}


def test_health_is_public(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_services_requires_key(client):
    assert client.get("/api/services").status_code == 401
    assert client.get("/api/services", headers={"Authorization": "Bearer nope"}).status_code == 403


@respx.mock
def test_services_and_nodes(client):
    respx.get("http://10.0.0.5:8000/health").mock(return_value=httpx.Response(200, json={"status": "healthy", "default_model": "m",
        "engine_pool": {"model_count": 1, "loaded_count": 1, "final_ceiling": 1e10, "current_model_memory": 5e9}}))
    respx.get(url__regex=r"http://(litellm|ember-api|ember-dashboard|qdrant):.*").mock(side_effect=httpx.ConnectError("x"))
    respx.get("http://litellm:4000/health").mock(side_effect=httpx.ConnectError("x"))
    client.post("/api/services/refresh", headers=AUTH)
    body = client.get("/api/services", headers=AUTH).json()
    by_id = {s["id"]: s for s in body["services"]}
    assert by_id["omlx"]["state"] == "healthy" and by_id["omlx"]["node"] == "jons-mac-mini"
    assert by_id["litellm"]["state"] == "unreachable"
    assert by_id["omlx"]["ui_url"] == "https://omlx.vaxel.xyz/docs"
    nodes = client.get("/api/nodes", headers=AUTH).json()["nodes"]
    assert {n["id"] for n in nodes} == {"docker01", "jons-mac-mini"}


@respx.mock
def test_capabilities_and_models(client):
    respx.get("http://10.0.0.5:8000/health").mock(return_value=httpx.Response(200, json={"status": "healthy", "default_model": "m",
        "engine_pool": {"model_count": 1, "loaded_count": 1, "final_ceiling": 1e10, "current_model_memory": 5e9}}))
    respx.get(url__regex=r"http://(litellm|ember-api|ember-dashboard|qdrant):.*").mock(side_effect=httpx.ConnectError("x"))
    respx.get("http://10.0.0.5:8000/v1/models/status").mock(return_value=httpx.Response(200, json={"data": [
        {"id": "Kokoro-82M-bf16", "loaded": False, "estimated_size": 343470909},
        {"id": "Ornith-1.5-9B-MLX-4bit", "loaded": True, "estimated_size": 5290069221}]}))
    client.post("/api/services/refresh", headers=AUTH)
    caps = client.get("/api/capabilities", headers=AUTH).json()["capabilities"]
    assert caps["stt"] == {"provider": "omlx", "state": "healthy", "model": "parakeet-tdt-0.6b-v3"}
    models = client.get("/api/models", headers=AUTH).json()
    auto = next(a for a in models["aliases"] if a["alias"] == "ember-auto")
    assert auto == {"alias": "ember-auto", "provider": "omlx", "model": "Ornith-1.5-9B-MLX-4bit", "resident": True, "estimated_size_gb": 5.29}
    think = next(a for a in models["aliases"] if a["alias"] == "ember-think")
    assert think["provider"] == "openrouter" and think["resident"] is None


def test_providers_never_echo_keys(client):
    body = client.get("/api/providers", headers=AUTH).json()
    assert {p["id"]: p["configured"] for p in body["providers"]} == {"omlx": True, "openrouter": True}
    assert "omlx-k" not in str(body) and "or-key" not in str(body)


def test_config_validate_reports_missing_alias_model(client, monkeypatch):
    monkeypatch.delenv("OMLX_TTS_MODEL")
    body = client.get("/api/config/validate", headers=AUTH).json()
    assert body["ok"] is False
    assert any(c["name"] == "env:OMLX_TTS_MODEL" and not c["ok"] for c in body["checks"])
```

Run: `cd ember-api && python3 -m pytest tests/test_api.py -q` → Expected: FAIL (no `main`).

- [ ] **Step 2: Routers**

`ember-api/ember_api/routers/__init__.py`: empty.

`ember-api/ember_api/routers/services.py`:

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from ..security import require_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


def _ui_url(svc, state_detail: dict) -> str | None:
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
            "latency_ms": h.latency_ms if h else None, "detail": h.detail if h else {}, "ui_url": _ui_url(svc, {}),
        })
    return {"polled_at": reg.polled_at.isoformat() if reg.polled_at else None, "services": out}


@router.post("/services/refresh")
async def refresh(request: Request):
    await request.app.state.registry.poll_once()
    return {"polled_at": datetime.now(timezone.utc).isoformat()}


@router.get("/nodes")
async def nodes(request: Request):
    reg = request.app.state.registry
    groups = {"docker01": "control-plane", "jons-mac-mini": "inference-node"}
    return {"nodes": [{"id": n, "role": r, "services": [s.id for s in reg.services.values() if s.node == n]} for n, r in groups.items()]}
```

`ember-api/ember_api/routers/models.py`:

```python
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
async def models(request: Request, settings: Settings = Depends(get_settings)):
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
```

`ember-api/ember_api/routers/providers.py`:

```python
import os

from fastapi import APIRouter, Depends

from ..security import require_api_key
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


@router.get("/providers")
async def providers(settings: Settings = Depends(get_settings)):
    return {"providers": [
        {"id": "omlx", "name": "oMLX (jons-mac-mini)", "configured": bool(settings.omlx_api_key), "base_url": settings.omlx_base_url},
        {"id": "openrouter", "name": "OpenRouter", "configured": bool(os.environ.get("OPENROUTER_API_KEY")),
         "model": os.environ.get("OPENROUTER_THINK_MODEL", "")},
    ], "gateway": {"public_url": settings.llm_public_url, "internal_url": settings.llm_internal_url}}
```

`ember-api/ember_api/routers/config.py`:

```python
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
    checks.append({"name": "omlx_base_url_is_lan_http", "ok": base.startswith("http://172.") or base.startswith("http://10.") or base.startswith("http://192.168."),
                   "message": base or "unset"})
    return checks


@router.get("/config/validate")
async def validate():
    checks = run_checks()
    return {"ok": all(c["ok"] for c in checks), "checks": checks}
```

- [ ] **Step 3: main.py with registry + poll loop**

`ember-api/ember_api/main.py`:

```python
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from . import __version__
from .health import ServiceHealth, probe
from .manifests import Service, load_manifests
from .routers import config, models, providers, services
from .settings import Settings, get_settings

log = logging.getLogger("ember-api")


class Registry:
    def __init__(self, services: dict[str, Service], settings: Settings, http: httpx.AsyncClient):
        self.services, self._settings, self._http = services, settings, http
        self.health: dict[str, ServiceHealth] = {}
        self.polled_at: datetime | None = None

    async def poll_once(self) -> None:
        results = await asyncio.gather(*(probe(s, self._http, self._settings) for s in self.services.values()))
        self.health = {r.id: r for r in results}
        self.polled_at = datetime.now(timezone.utc)

    async def run(self, interval_s: int) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(interval_s)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = get_settings()
    app.state.http = httpx.AsyncClient()
    app.state.registry = Registry(load_manifests(settings.services_dir, os.environ), settings, app.state.http)
    task = None
    if os.environ.get("EMBER_POLL_ON_START", "true") == "true":
        task = asyncio.create_task(app.state.registry.run(settings.poll_interval_s))
    yield
    if task:
        task.cancel()
    await app.state.http.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="Ember API", version=__version__, lifespan=_lifespan)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    for r in (services.router, models.router, providers.router, config.router):
        app.include_router(r)
    return app


app = create_app()
```

- [ ] **Step 4: Dockerfile**

`ember-api/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY ember_api ./ember_api
RUN pip install --no-cache-dir . && useradd -m -u 1000 ember
USER ember
ENV EMBER_SERVICES_DIR=/app/services
EXPOSE 3002
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3002/api/health', timeout=4)"
CMD ["uvicorn", "ember_api.main:app", "--host", "0.0.0.0", "--port", "3002"]
```

- [ ] **Step 5: Run tests, ruff, commit**

Run: `cd ember-api && python3 -m pytest -q && ruff check .` → Expected: all pass, ruff clean.

```bash
git add ember-api
git commit -m "feat(ember-api): services/nodes/capabilities/models/providers/config routes and poll loop"
```

---

