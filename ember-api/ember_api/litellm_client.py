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
