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
    from ember_api import health

    async def fake_tcp(host, port, timeout):
        return True
    monkeypatch.setattr(health, "_tcp_open", fake_tcp)
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm-postgres"], c, SETTINGS)
    assert h.state == "healthy" and h.reason == "tcp open"
