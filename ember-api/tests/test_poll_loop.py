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


async def test_run_continues_after_a_probe_raises(registry, monkeypatch, caplog):
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
        if registry.polled_at is not None:
            break
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await registry._http.aclose()

    assert len(calls) > len(registry.services), "loop stopped after the first failing iteration"
    assert registry.polled_at is not None, "second iteration never completed"
    assert all(h.state == "healthy" for h in registry.health.values())
    assert "poll failed" in caplog.text


async def test_poll_once_propagates_so_the_supervisor_can_log(registry, monkeypatch):
    async def boom(service, client, settings):
        raise RuntimeError("nope")

    monkeypatch.setattr(main_mod, "probe", boom)
    with pytest.raises(RuntimeError):
        await registry.poll_once()
    await registry._http.aclose()
