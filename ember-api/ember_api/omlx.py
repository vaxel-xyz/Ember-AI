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
