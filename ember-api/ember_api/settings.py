import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    ember_api_key: str
    services_dir: Path
    omlx_base_url: str
    omlx_api_key: str
    litellm_base_url: str
    litellm_master_key: str
    llm_public_url: str
    llm_internal_url: str
    poll_interval_s: int


def _req(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


@lru_cache
def get_settings() -> Settings:
    return Settings(
        ember_api_key=_req("EMBER_API_KEY"),
        services_dir=Path(os.environ.get("EMBER_SERVICES_DIR", "/app/services")),
        omlx_base_url=_req("OMLX_BASE_URL").rstrip("/"),
        omlx_api_key=_req("OMLX_API_KEY"),
        litellm_base_url=os.environ.get("LITELLM_BASE_URL", "http://litellm:4000").rstrip("/"),
        litellm_master_key=_req("LITELLM_MASTER_KEY"),
        llm_public_url=os.environ.get("LLM_PUBLIC_URL", "https://llm.vaxel.xyz/v1"),
        llm_internal_url=os.environ.get("LLM_INTERNAL_URL", "http://172.20.142.7:4000/v1"),
        poll_interval_s=int(os.environ.get("EMBER_POLL_INTERVAL_S", "15")),
    )
