### Task 5: Health state machine and probes

**Files:**
- Create: `ember-api/ember_api/health.py`, `ember-api/ember_api/omlx.py`, `ember-api/ember_api/litellm_client.py`, `ember-api/tests/test_health.py`

**Interfaces:**
- Produces:
  - `health.State = Literal["healthy","degraded","starting","reachable-unhealthy","unreachable"]`
  - `health.ServiceHealth` dataclass: `id, state: State, reason: str, latency_ms: float | None, detail: dict`
  - `health.probe(service: Service, client: httpx.AsyncClient, settings: Settings) -> ServiceHealth`
  - `omlx.OmlxClient(base_url, api_key, client)`: `health() -> dict`, `models_status() -> list[dict]`
  - `litellm_client.LiteLLMClient(base_url, master_key, client)`: `readiness() -> dict`, `model_info() -> list[dict]`, `deployment_health() -> dict`

- [ ] **Step 1: Failing tests**

`ember-api/tests/test_health.py`:

```python
import httpx
import pytest
import respx

from ember_api.health import probe
from ember_api.manifests import load_manifests
from ember_api.settings import Settings

SETTINGS = Settings(ember_api_key="k", services_dir=None, omlx_base_url="http://10.0.0.5:8000", omlx_api_key="omlx-k",
                    litellm_base_url="http://litellm:4000", litellm_master_key="sk-master",
                    llm_public_url="https://llm.vaxel.xyz/v1", llm_internal_url="http://172.20.142.7:4000/v1", poll_interval_s=15)


@pytest.fixture
def svc(services_dir, env):
    return load_manifests(services_dir, env)


@respx.mock
async def test_omlx_healthy_with_loaded_model(svc):
    respx.get("http://10.0.0.5:8000/health").mock(return_value=httpx.Response(200, json={
        "status": "healthy", "default_model": "Ornith-1.5-9B-MLX-4bit",
        "engine_pool": {"model_count": 7, "loaded_count": 1, "final_ceiling": 10_000_000_000, "current_model_memory": 5_290_069_221}}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "healthy" and h.detail["loaded_count"] == 1 and h.detail["memory_used_gb"] == 5.29


@respx.mock
async def test_omlx_degraded_when_no_model_loaded(svc):
    respx.get("http://10.0.0.5:8000/health").mock(return_value=httpx.Response(200, json={
        "status": "healthy", "default_model": "x", "engine_pool": {"model_count": 7, "loaded_count": 0, "final_ceiling": 1, "current_model_memory": 0}}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "degraded" and "no model loaded" in h.reason


@respx.mock
async def test_omlx_starting_on_503_loading(svc):
    respx.get("http://10.0.0.5:8000/health").mock(return_value=httpx.Response(503, json={"status": "loading"}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "starting"


@respx.mock
async def test_unreachable_on_connect_error(svc):
    respx.get("http://10.0.0.5:8000/health").mock(side_effect=httpx.ConnectError("refused"))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "unreachable" and h.latency_ms is None


@respx.mock
async def test_generic_http_500_is_reachable_unhealthy(svc):
    respx.get("http://ember-dashboard:3001/").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["ember-dashboard"], c, SETTINGS)
    assert h.state == "reachable-unhealthy" and "HTTP 500" in h.reason


@respx.mock
async def test_litellm_degraded_when_a_deployment_is_unhealthy(svc):
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(200, json={"status": "connected"}))
    respx.get("http://litellm:4000/health").mock(return_value=httpx.Response(200, json={
        "healthy_endpoints": [{"model": "openrouter/z-ai/glm-5.3"}], "unhealthy_endpoints": [{"model": "openai/Ornith-1.5-9B-MLX-4bit", "error": "connect"}],
        "healthy_count": 1, "unhealthy_count": 1}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm"], c, SETTINGS)
    assert h.state == "degraded" and h.detail["unhealthy_count"] == 1


async def test_postgres_probe_uses_tcp(svc, monkeypatch):
    import ember_api.health as health

    async def fake_tcp(host, port, timeout):
        return True
    monkeypatch.setattr(health, "_tcp_open", fake_tcp)
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm-postgres"], c, SETTINGS)
    assert h.state == "healthy" and h.reason == "tcp open"
```

Run: `cd ember-api && python3 -m pytest tests/test_health.py -q` → Expected: FAIL (ImportError).

- [ ] **Step 2: Clients**

`ember-api/ember_api/omlx.py`:

```python
import httpx


class OmlxClient:
    def __init__(self, base_url: str, api_key: str, client: httpx.AsyncClient):
        self._base, self._key, self._c = base_url.rstrip("/"), api_key, client

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}"}

    async def health(self, timeout: float = 5.0) -> httpx.Response:
        return await self._c.get(f"{self._base}/health", timeout=timeout)

    async def models_status(self, timeout: float = 10.0) -> list[dict]:
        r = await self._c.get(f"{self._base}/v1/models/status", headers=self._auth(), timeout=timeout)
        r.raise_for_status()
        body = r.json()
        return body.get("data") or body.get("models") or []

    async def voices(self, model: str, timeout: float = 10.0) -> list[str]:
        r = await self._c.get(f"{self._base}/v1/audio/voices", params={"model": model}, headers=self._auth(), timeout=timeout)
        r.raise_for_status()
        return list(r.json().get("voices", []))
```

`ember-api/ember_api/litellm_client.py`:

```python
import httpx


class LiteLLMClient:
    def __init__(self, base_url: str, master_key: str, client: httpx.AsyncClient):
        self._base, self._key, self._c = base_url.rstrip("/"), master_key, client

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}"}

    async def readiness(self, timeout: float = 5.0) -> httpx.Response:
        return await self._c.get(f"{self._base}/health/readiness", timeout=timeout)

    async def deployment_health(self, timeout: float = 30.0) -> dict:
        r = await self._c.get(f"{self._base}/health", headers=self._auth(), timeout=timeout)
        r.raise_for_status()
        return r.json()

    async def model_info(self, timeout: float = 10.0) -> list[dict]:
        r = await self._c.get(f"{self._base}/model/info", headers=self._auth(), timeout=timeout)
        r.raise_for_status()
        return r.json().get("data", [])
```

- [ ] **Step 3: health.py**

`ember-api/ember_api/health.py`:

```python
import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal

import httpx

from .litellm_client import LiteLLMClient
from .manifests import Service
from .omlx import OmlxClient
from .settings import Settings

State = Literal["healthy", "degraded", "starting", "reachable-unhealthy", "unreachable"]


@dataclass
class ServiceHealth:
    id: str
    state: State
    reason: str
    latency_ms: float | None = None
    detail: dict = field(default_factory=dict)


async def _tcp_open(host: str, port: int, timeout: float) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    return True


def _url(service: Service) -> str:
    return f"http://{service.host}:{service.port}{service.health_path}"


async def _probe_http(service: Service, client: httpx.AsyncClient) -> ServiceHealth:
    t0 = time.perf_counter()
    try:
        r = await client.get(_url(service), timeout=service.health_timeout)
    except httpx.ConnectError as exc:
        return ServiceHealth(service.id, "unreachable", f"connect failed: {exc.__class__.__name__}")
    except httpx.TimeoutException:
        return ServiceHealth(service.id, "unreachable", f"timeout after {service.health_timeout}s")
    ms = round((time.perf_counter() - t0) * 1000, 1)
    if r.status_code < 400:
        return ServiceHealth(service.id, "healthy", f"HTTP {r.status_code}", ms)
    return ServiceHealth(service.id, "reachable-unhealthy", f"HTTP {r.status_code}", ms)


async def _probe_omlx(service: Service, client: httpx.AsyncClient, settings: Settings) -> ServiceHealth:
    omlx = OmlxClient(f"http://{service.host}:{service.port}", settings.omlx_api_key, client)
    t0 = time.perf_counter()
    try:
        r = await omlx.health(service.health_timeout)
    except httpx.ConnectError:
        return ServiceHealth(service.id, "unreachable", "connect failed")
    except httpx.TimeoutException:
        return ServiceHealth(service.id, "unreachable", f"timeout after {service.health_timeout}s")
    ms = round((time.perf_counter() - t0) * 1000, 1)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code == 503 and body.get("status") == "loading":
        return ServiceHealth(service.id, "starting", "oMLX preloading pinned models", ms, body)
    if r.status_code >= 400:
        return ServiceHealth(service.id, "reachable-unhealthy", f"HTTP {r.status_code}", ms, body)
    pool = body.get("engine_pool", {})
    detail = {
        "default_model": body.get("default_model"),
        "model_count": pool.get("model_count"), "loaded_count": pool.get("loaded_count"),
        "memory_used_gb": round(pool.get("current_model_memory", 0) / 1e9, 2),
        "memory_ceiling_gb": round(pool.get("final_ceiling", 0) / 1e9, 2),
    }
    if pool.get("loaded_count", 0) == 0:
        return ServiceHealth(service.id, "degraded", "server up, no model loaded (loads on first request)", ms, detail)
    return ServiceHealth(service.id, "healthy", f"{detail['loaded_count']} model(s) resident", ms, detail)


async def _probe_litellm(service: Service, client: httpx.AsyncClient, settings: Settings) -> ServiceHealth:
    lite = LiteLLMClient(f"http://{service.host}:{service.port}", settings.litellm_master_key, client)
    t0 = time.perf_counter()
    try:
        r = await lite.readiness(service.health_timeout)
    except httpx.ConnectError:
        return ServiceHealth(service.id, "unreachable", "connect failed")
    except httpx.TimeoutException:
        return ServiceHealth(service.id, "unreachable", f"timeout after {service.health_timeout}s")
    ms = round((time.perf_counter() - t0) * 1000, 1)
    if r.status_code >= 400:
        return ServiceHealth(service.id, "reachable-unhealthy", f"readiness HTTP {r.status_code}", ms)
    try:
        dep = await lite.deployment_health()
    except httpx.HTTPError as exc:
        return ServiceHealth(service.id, "degraded", f"readiness ok, /health failed: {exc.__class__.__name__}", ms)
    detail = {"healthy_count": dep.get("healthy_count", 0), "unhealthy_count": dep.get("unhealthy_count", 0),
              "unhealthy": [e.get("model") for e in dep.get("unhealthy_endpoints", [])]}
    if detail["unhealthy_count"]:
        return ServiceHealth(service.id, "degraded", f"{detail['unhealthy_count']} deployment(s) unhealthy", ms, detail)
    return ServiceHealth(service.id, "healthy", f"{detail['healthy_count']} deployment(s) healthy", ms, detail)


async def _probe_postgres(service: Service) -> ServiceHealth:
    ok = await _tcp_open(service.host, service.port, service.health_timeout)
    return ServiceHealth(service.id, "healthy" if ok else "unreachable", "tcp open" if ok else "tcp closed")


async def probe(service: Service, client: httpx.AsyncClient, settings: Settings) -> ServiceHealth:
    if service.health_probe == "omlx":
        return await _probe_omlx(service, client, settings)
    if service.health_probe == "litellm":
        return await _probe_litellm(service, client, settings)
    if service.health_probe == "postgres":
        return await _probe_postgres(service)
    return await _probe_http(service, client)
```

- [ ] **Step 4: Run + commit**

Run: `cd ember-api && python3 -m pytest -q` → Expected: all pass (13).

```bash
git add ember-api
git commit -m "feat(ember-api): five-state health probes for oMLX, LiteLLM, Postgres, HTTP"
```

---

