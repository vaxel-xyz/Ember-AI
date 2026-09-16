import httpx
import pytest
import respx

from ember_api.aliases import ALIAS_NAMES
from ember_api.health import probe
from ember_api.manifests import load_manifests
from ember_api.settings import Settings

SETTINGS = Settings(ember_api_key="k", services_dir=None, omlx_base_url="http://10.0.0.5:8000", omlx_api_key="omlx-k",
                    litellm_base_url="http://litellm:4000", litellm_master_key="sk-master",
                    llm_public_url="https://ai.vaxel.xyz/v1", llm_internal_url="http://172.20.142.7:4000/v1", poll_interval_s=15)


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
async def test_unreachable_on_remote_protocol_error(svc):
    """RemoteProtocolError is a TransportError, not a ConnectError — it used to escape the probe."""
    respx.get("http://10.0.0.5:8000/health").mock(side_effect=httpx.RemoteProtocolError("peer closed"))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "unreachable" and h.reason == "connect failed: RemoteProtocolError"


@respx.mock
async def test_omlx_null_engine_pool_is_degraded_not_a_crash(svc):
    respx.get("http://10.0.0.5:8000/health").mock(
        return_value=httpx.Response(200, json={"status": "healthy", "engine_pool": None}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "degraded" and "no model loaded" in h.reason
    assert h.detail["loaded_count"] is None


@respx.mock
async def test_omlx_non_object_json_body_is_reachable_unhealthy(svc):
    respx.get("http://10.0.0.5:8000/health").mock(return_value=httpx.Response(200, json=["unexpected"]))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "reachable-unhealthy" and "not an object" in h.reason


@respx.mock
async def test_generic_http_500_is_reachable_unhealthy(svc):
    respx.get("http://ember-dashboard:3001/").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["ember-dashboard"], c, SETTINGS)
    assert h.state == "reachable-unhealthy" and "HTTP 500" in h.reason


def _model_info(aliases):
    return {"data": [{"model_name": a, "litellm_params": {}} for a in aliases]}


@respx.mock
async def test_litellm_degraded_when_an_alias_is_missing(svc):
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(200, json={"status": "connected"}))
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json=_model_info([a for a in ALIAS_NAMES if a != "ember-rerank"])))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm"], c, SETTINGS)
    assert h.state == "degraded"
    assert h.detail["missing"] == ["ember-rerank"]
    assert h.detail["aliases_registered"] == len(ALIAS_NAMES) - 1
    assert h.detail["aliases_expected"] == len(ALIAS_NAMES)


@respx.mock
async def test_litellm_healthy_when_full_alias_set_registered(svc):
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(200, json={"status": "connected"}))
    respx.get("http://litellm:4000/model/info").mock(return_value=httpx.Response(200, json=_model_info(ALIAS_NAMES)))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm"], c, SETTINGS)
    assert h.state == "healthy"
    assert h.detail == {"aliases_registered": len(ALIAS_NAMES), "aliases_expected": len(ALIAS_NAMES), "missing": []}


@respx.mock
async def test_litellm_probe_never_calls_live_health_endpoint(svc):
    """C1 regression guard: LiteLLM GET /health runs a live inference call per deployment."""
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(200, json={"status": "connected"}))
    respx.get("http://litellm:4000/model/info").mock(return_value=httpx.Response(200, json=_model_info(ALIAS_NAMES)))
    deep = respx.get("http://litellm:4000/health").mock(return_value=httpx.Response(200, json={"healthy_count": 0}))
    async with httpx.AsyncClient() as c:
        await probe(svc["litellm"], c, SETTINGS)
    assert deep.called is False


@respx.mock
async def test_litellm_reachable_unhealthy_when_readiness_errors(svc):
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(503, json={"status": "error"}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm"], c, SETTINGS)
    assert h.state == "reachable-unhealthy" and "readiness HTTP 503" in h.reason


async def test_postgres_probe_uses_tcp(svc, monkeypatch):
    from ember_api import health

    async def fake_tcp(host, port, timeout):
        return True
    monkeypatch.setattr(health, "_tcp_open", fake_tcp)
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm-postgres"], c, SETTINGS)
    assert h.state == "healthy" and h.reason == "tcp open"


@respx.mock
async def test_omlx_invalid_json_body_is_reachable_unhealthy(svc):
    respx.get("http://10.0.0.5:8000/health").mock(
        return_value=httpx.Response(200, content=b"not json", headers={"content-type": "application/json"}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["omlx"], c, SETTINGS)
    assert h.state == "reachable-unhealthy" and "invalid JSON body" in h.reason


@respx.mock
async def test_litellm_invalid_json_body_is_degraded(svc):
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(200, json={"status": "connected"}))
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, content=b"not json", headers={"content-type": "application/json"}))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm"], c, SETTINGS)
    assert h.state == "degraded" and "JSONDecodeError" in h.reason


@respx.mock
async def test_litellm_non_object_model_info_body_is_degraded(svc):
    """model_info() raises ValueError on a non-dict body; _probe_litellm's except clause catches it."""
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(200, json={"status": "connected"}))
    respx.get("http://litellm:4000/model/info").mock(return_value=httpx.Response(200, json=["oops"]))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm"], c, SETTINGS)
    assert h.state == "degraded" and "ValueError" in h.reason


@respx.mock
async def test_litellm_model_info_http_error_is_degraded_with_status_code(svc):
    """model_info() raises httpx.HTTPStatusError; reason should surface the status code, not just the class name."""
    respx.get("http://litellm:4000/health/readiness").mock(return_value=httpx.Response(200, json={"status": "connected"}))
    respx.get("http://litellm:4000/model/info").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as c:
        h = await probe(svc["litellm"], c, SETTINGS)
    assert h.state == "degraded" and "HTTP 500" in h.reason
