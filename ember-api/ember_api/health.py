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
    except (TimeoutError, OSError):
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
    try:
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    except ValueError:
        return ServiceHealth(service.id, "reachable-unhealthy", f"HTTP {r.status_code}, invalid JSON body", ms)
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
    except (httpx.HTTPError, ValueError) as exc:
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
