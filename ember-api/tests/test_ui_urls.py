"""Dashboard links must be openable in a browser, not container-internal."""
import pytest

from ember_api.manifests import load_manifests
from ember_api.routers.services import _strip_api_suffix, _ui_url
from ember_api.settings import Settings

SETTINGS = Settings(ember_api_key="k", services_dir=None, omlx_base_url="http://10.0.0.5:8000", omlx_api_key="omlx-k",
                    litellm_base_url="http://litellm:4000", litellm_master_key="sk-master",
                    llm_public_url="https://llm.vaxel.xyz/v1", llm_internal_url="http://172.20.142.7:4000/v1", poll_interval_s=15)


@pytest.fixture
def svc(services_dir, env):
    return load_manifests(services_dir, env)


@pytest.mark.parametrize(("raw", "expected"), [
    ("https://llm.vaxel.xyz/v1", "https://llm.vaxel.xyz"),
    ("https://llm.vaxel.xyz/v1/", "https://llm.vaxel.xyz"),
    ("https://omlx.vaxel.xyz", "https://omlx.vaxel.xyz"),
    ("https://ember.vaxel.xyz/", "https://ember.vaxel.xyz"),
    ("http://172.20.142.7:4000/v1", "http://172.20.142.7:4000"),
])
def test_strip_api_suffix(raw, expected):
    assert _strip_api_suffix(raw) == expected


def test_gateway_ui_is_not_nested_under_v1(svc):
    assert _ui_url(svc["litellm"], SETTINGS) == "https://llm.vaxel.xyz/ui/"


def test_container_only_service_uses_the_lan_host_and_published_port(svc):
    assert _ui_url(svc["qdrant"], SETTINGS) == "http://172.20.142.7:6333/dashboard"


def test_public_url_without_v1_is_untouched(svc):
    assert _ui_url(svc["omlx"], SETTINGS) == "https://omlx.vaxel.xyz/docs"
    assert _ui_url(svc["ember-dashboard"], SETTINGS) == "https://ember.vaxel.xyz/"


def test_docker_service_falls_back_to_lan_when_its_public_url_is_unset(services_dir, env):
    without = load_manifests(services_dir, {k: v for k, v in env.items() if k != "EMBER_PUBLIC_URL"})
    assert _ui_url(without["ember-dashboard"], SETTINGS) == "http://172.20.142.7:3001/"


def test_services_opting_out_have_no_link(svc):
    assert _ui_url(svc["ember-api"], SETTINGS) is None
    assert _ui_url(svc["litellm-postgres"], SETTINGS) is None


def test_falls_back_to_the_manifest_host_when_internal_url_is_unparseable(svc):
    settings = Settings(**{**SETTINGS.__dict__, "llm_internal_url": "not-a-url"})
    assert _ui_url(svc["qdrant"], settings) == "http://qdrant:6333/dashboard"
