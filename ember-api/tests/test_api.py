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
    # LLM_PUBLIC_URL is the API root (.../v1); the LiteLLM UI sits beside it, not under it
    assert by_id["litellm"]["ui_url"] == "https://llm.vaxel.xyz/ui/"
    # qdrant has no public URL: the container hostname would not resolve in a browser
    assert by_id["qdrant"]["ui_url"] == "http://172.20.142.7:6333/dashboard"
    # ember-api sets external_link: false
    assert by_id["ember-api"]["ui_url"] is None
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


@respx.mock
def test_shallow_refresh_does_not_deep_check(client):
    respx.get("http://10.0.0.5:8000/health").mock(side_effect=httpx.ConnectError("x"))
    respx.get(url__regex=r"http://(litellm|ember-api|ember-dashboard|qdrant):.*").mock(side_effect=httpx.ConnectError("x"))
    deep = respx.get("http://litellm:4000/health").mock(return_value=httpx.Response(200, json={"healthy_count": 1}))
    body = client.post("/api/services/refresh", headers=AUTH).json()
    assert body["deep"] is False and "gateway" not in body
    assert deep.called is False


@respx.mock
def test_deep_refresh_runs_deployment_health(client):
    respx.get("http://10.0.0.5:8000/health").mock(side_effect=httpx.ConnectError("x"))
    respx.get("http://litellm:4000/health/readiness").mock(side_effect=httpx.ConnectError("x"))
    respx.get(url__regex=r"http://(ember-api|ember-dashboard|qdrant):.*").mock(side_effect=httpx.ConnectError("x"))
    respx.get("http://litellm:4000/health").mock(return_value=httpx.Response(200, json={
        "healthy_endpoints": [{"model": "openai/Ornith-1.5-9B-MLX-4bit"}],
        "unhealthy_endpoints": [{"model": "openrouter/z-ai/glm-5.3", "error": "401"}],
        "healthy_count": 1, "unhealthy_count": 1}))
    body = client.post("/api/services/refresh?deep=true", headers=AUTH).json()
    assert body["deep"] is True
    assert body["gateway"]["ok"] is False
    assert body["gateway"]["healthy_count"] == 1
    assert body["gateway"]["unhealthy_endpoints"] == [{"model": "openrouter/z-ai/glm-5.3", "error": "401"}]


def test_deep_refresh_requires_key(client):
    assert client.post("/api/services/refresh?deep=true").status_code == 401
