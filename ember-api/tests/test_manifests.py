from ember_api.manifests import load_manifests


def test_loads_all_seven_services(services_dir, env):
    services = load_manifests(services_dir, env)
    assert set(services) == {"litellm", "litellm-postgres", "ember-api", "ember-dashboard", "omlx", "qdrant", "open-webui"}


def test_open_webui_is_an_external_consumer(services_dir, env):
    owui = load_manifests(services_dir, env)["open-webui"]
    assert owui.type == "external" and owui.role == "consumer" and owui.managed is False
    assert owui.node == "docker01" and owui.port == 3003 and owui.health_path == "/health"
    assert owui.public_url == "https://chat.vaxel.xyz"


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
