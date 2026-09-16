"""The poll loop is a supervisor: a probe that raises must not stop future polls."""
import asyncio

import httpx
import pytest

import ember_api.main as main_mod
from ember_api.health import ServiceHealth
from ember_api.main import Registry
from ember_api.settings import Settings

SETTINGS = Settings(ember_api_key="k", services_dir=None, omlx_base_url="http://10.0.0.5:8000", omlx_api_key="omlx-k",
                    litellm_base_url="http://litellm:4000", litellm_master_key="sk-master",
                    llm_public_url="https://llm.vaxel.xyz/v1", llm_internal_url="http://172.20.142.7:4000/v1", poll_interval_s=15)


@pytest.fixture
def registry(services_dir, env):
    from ember_api.manifests import load_manifests
    return Registry(load_manifests(services_dir, env), SETTINGS, httpx.AsyncClient())


async def test_run_continues_after_a_probe_raises(registry, monkeypatch):
    """Even a cycle where every probe raises is absorbed into per-service 'unreachable'
    states by poll_once rather than propagating, so run() keeps polling on schedule."""
    calls = []

    async def flaky(service, client, settings):
        calls.append(service.id)
        if len(calls) <= len(registry.services):
            raise RuntimeError("probe blew up")
        return ServiceHealth(service.id, "healthy", "stubbed")

    monkeypatch.setattr(main_mod, "probe", flaky)
    task = asyncio.create_task(registry.run(0.01))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if registry.health and all(h.state == "healthy" for h in registry.health.values()):
            break
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await registry._http.aclose()

    assert len(calls) > len(registry.services), "loop stopped after the first failing cycle"
    assert registry.polled_at is not None, "second cycle never completed"
    assert all(h.state == "healthy" for h in registry.health.values())


async def test_poll_once_isolates_a_raising_probe(registry, monkeypatch, caplog):
    """A single probe raising must not stop other services from getting fresh states in the same cycle."""
    async def flaky_or_healthy(service, client, settings):
        if service.id == "omlx":
            raise RuntimeError("nope")
        return ServiceHealth(service.id, "healthy", "stubbed")

    monkeypatch.setattr(main_mod, "probe", flaky_or_healthy)
    await registry.poll_once()
    await registry._http.aclose()

    assert registry.polled_at is not None
    assert registry.health["omlx"].state == "unreachable"
    assert "probe error: RuntimeError" in registry.health["omlx"].reason
    assert "omlx" in caplog.text and "RuntimeError" in caplog.text
    others = [s for s in registry.services if s != "omlx"]
    assert others, "fixture must include at least one other service"
    assert all(registry.health[s].state == "healthy" for s in others)
