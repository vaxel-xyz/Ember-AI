from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

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
