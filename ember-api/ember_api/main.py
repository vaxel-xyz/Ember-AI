import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

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
        self.polled_at = datetime.now(UTC)

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
