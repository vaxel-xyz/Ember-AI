### Task 4: ember-api scaffold, settings, security, manifest loader

**Files:**
- Create: `ember-api/pyproject.toml`, `ember-api/ember_api/__init__.py`, `ember-api/ember_api/settings.py`, `ember-api/ember_api/security.py`, `ember-api/ember_api/manifests.py`, `ember-api/tests/conftest.py`, `ember-api/tests/test_manifests.py`

**Interfaces:**
- Produces:
  - `settings.Settings` (pydantic-settings-free dataclass) fields: `ember_api_key: str`, `services_dir: Path`, `omlx_base_url: str`, `omlx_api_key: str`, `litellm_base_url: str`, `litellm_master_key: str`, `llm_public_url: str`, `llm_internal_url: str`, `poll_interval_s: int`; `get_settings() -> Settings` (env-driven, cached).
  - `manifests.Service` dataclass: `id, name, host, port, external_port, health_path, health_timeout, type, category, ui_path, external_link, public_url, node, role, managed, capabilities: list[str], health_probe`.
  - `manifests.load_manifests(services_dir: Path, env: Mapping[str,str]) -> dict[str, Service]`.
  - `security.require_api_key` FastAPI dependency.

- [ ] **Step 1: pyproject**

`ember-api/pyproject.toml`:

```toml
[project]
name = "ember-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115,<1", "uvicorn[standard]>=0.30,<1", "httpx>=0.27,<1", "PyYAML>=6,<7", "jsonschema>=4.21,<5"]
[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "respx>=0.21", "ruff>=0.5"]
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
[tool.ruff]
line-length = 120
target-version = "py312"
```

`ember-api/ember_api/__init__.py`: `__version__ = "0.1.0"`.

- [ ] **Step 2: Failing manifest tests**

`ember-api/tests/conftest.py`:

```python
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def env():
    return {
        "EMBER_API_KEY": "test-key", "OMLX_HOST": "10.0.0.5", "OMLX_BASE_URL": "http://10.0.0.5:8000", "OMLX_API_KEY": "omlx-k",
        "LITELLM_MASTER_KEY": "sk-master", "LLM_PUBLIC_URL": "https://llm.vaxel.xyz/v1", "LLM_INTERNAL_URL": "http://172.20.142.7:4000/v1",
        "OMLX_PUBLIC_URL": "https://omlx.vaxel.xyz",
    }


@pytest.fixture
def services_dir():
    return ROOT / "services"
```

`ember-api/tests/test_manifests.py`:

```python
from ember_api.manifests import load_manifests


def test_loads_all_six_services(services_dir, env):
    services = load_manifests(services_dir, env)
    assert set(services) == {"litellm", "litellm-postgres", "ember-api", "ember-dashboard", "omlx", "qdrant"}


def test_host_env_overrides_default_host(services_dir, env):
    omlx = load_manifests(services_dir, env)["omlx"]
    assert omlx.host == "10.0.0.5" and omlx.port == 8000 and omlx.type == "external"
    assert omlx.node == "jons-mac-mini" and omlx.managed is False and omlx.health_probe == "omlx"
    assert "stt" in omlx.capabilities and omlx.public_url == "https://omlx.vaxel.xyz"


def test_defaults_when_env_missing(services_dir):
    omlx = load_manifests(services_dir, {})["omlx"]
    assert omlx.host == "172.20.142.184" and omlx.public_url is None


def test_docker_service_shape(services_dir, env):
    lite = load_manifests(services_dir, env)["litellm"]
    assert lite.health_path == "/health/readiness" and lite.external_port == 4000 and lite.role == "gateway"
    assert lite.capabilities == [] and lite.health_probe == "litellm"
```

Run: `cd ember-api && pip install -e '.[dev]' -q && python3 -m pytest tests/test_manifests.py -q` → Expected: FAIL (ImportError).

- [ ] **Step 3: settings.py, security.py, manifests.py**

`ember-api/ember_api/settings.py`:

```python
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
```

`ember-api/ember_api/security.py`:

```python
import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import Settings, get_settings

_scheme = HTTPBearer(auto_error=False)


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    if not secrets.compare_digest(credentials.credentials.encode(), settings.ember_api_key.encode()):
        raise HTTPException(status_code=403, detail="Invalid API key")
```

`ember-api/ember_api/manifests.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import yaml


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    host: str
    port: int
    external_port: int
    health_path: str
    health_timeout: int
    type: str
    category: str
    ui_path: str
    external_link: bool
    public_url: str | None
    node: str
    role: str
    managed: bool
    capabilities: list[str] = field(default_factory=list)
    health_probe: str = "http"


def _service_from_manifest(data: dict, env: Mapping[str, str]) -> Service:
    s = data["service"]
    x = s.get("x_ember", {})
    host_env = s.get("host_env")
    host = env.get(host_env, s.get("default_host", "localhost")) if host_env else s.get("default_host", "localhost")
    ext_env = s.get("external_port_env")
    ext_default = int(s.get("external_port_default", s["port"]))
    external_port = int(env.get(ext_env, ext_default)) if ext_env else ext_default
    pub_env = s.get("public_url_env")
    public_url = env.get(pub_env) or None if pub_env else None
    return Service(
        id=s["id"], name=s["name"], host=host, port=int(s["port"]), external_port=external_port,
        health_path=s.get("health", ""), health_timeout=int(s.get("health_timeout", 10)), type=s["type"],
        category=s["category"], ui_path=s.get("ui_path", "/"), external_link=bool(s.get("external_link", True)),
        public_url=public_url, node=x["node"], role=x["role"], managed=bool(x["managed"]),
        capabilities=list(x.get("capabilities", [])), health_probe=x.get("health_probe", "http"),
    )


def load_manifests(services_dir: Path, env: Mapping[str, str]) -> dict[str, Service]:
    services: dict[str, Service] = {}
    for path in sorted(services_dir.glob("*/manifest.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "ods.services.v1":
            raise ValueError(f"{path}: unsupported schema_version")
        svc = _service_from_manifest(data, env)
        services[svc.id] = svc
    return services
```

- [ ] **Step 4: Run + commit**

Run: `cd ember-api && python3 -m pytest -q` → Expected: 6 passed (incl. Task 3 tests).

```bash
git add ember-api
git commit -m "feat(ember-api): settings, bearer auth, manifest loader"
```

---

