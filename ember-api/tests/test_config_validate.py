"""Required-env derivation: the LiteLLM template is the single source of truth."""
import json
from pathlib import Path
from string import Template

from ember_api.routers.config import (
    EXTRA_REQUIRED_ENV,
    required_env,
    template_identifiers,
    template_path,
)

ROOT = Path(__file__).resolve().parents[2]


def test_template_path_honours_env_override(monkeypatch, litellm_template):
    monkeypatch.setenv("EMBER_LITELLM_TEMPLATE", str(litellm_template))
    assert template_path() == litellm_template


def test_template_path_defaults_to_the_container_mount(monkeypatch):
    monkeypatch.delenv("EMBER_LITELLM_TEMPLATE", raising=False)
    assert str(template_path()) == "/app/config/litellm/ember.yaml.tmpl"


def test_required_env_superset_of_template_identifiers(monkeypatch, litellm_template):
    monkeypatch.setenv("EMBER_LITELLM_TEMPLATE", str(litellm_template))
    identifiers = set(Template(litellm_template.read_text(encoding="utf-8")).get_identifiers())
    assert identifiers, "template has no ${VAR} placeholders — derivation would silently pass"
    assert identifiers <= set(required_env())


def test_required_env_includes_non_placeholder_secrets(monkeypatch, litellm_template):
    monkeypatch.setenv("EMBER_LITELLM_TEMPLATE", str(litellm_template))
    assert set(EXTRA_REQUIRED_ENV) <= set(required_env())


def test_previously_optional_vars_are_now_required(monkeypatch, litellm_template):
    """OMLX_RERANK_MODEL and LITELLM_TURN_OFF_MESSAGE_LOGGING are load-bearing: render-config.py

    raises KeyError without them, so the gateway cannot start. They were not in the hand-written
    required list.
    """
    monkeypatch.setenv("EMBER_LITELLM_TEMPLATE", str(litellm_template))
    req = set(required_env())
    assert "OMLX_RERANK_MODEL" in req
    assert "LITELLM_TURN_OFF_MESSAGE_LOGGING" in req


def test_schema_required_covers_template_identifiers():
    req = set(json.loads((ROOT / ".env.schema.json").read_text())["required"])
    ids = Template((ROOT / "config/litellm/ember.yaml.tmpl").read_text()).get_identifiers()
    assert set(ids) <= req


def test_unreadable_template_is_reported_as_a_failed_check(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBER_LITELLM_TEMPLATE", str(tmp_path / "nope.tmpl"))
    assert template_identifiers() == []
    from ember_api.routers.config import run_checks
    check = next(c for c in run_checks() if c["name"] == "litellm_template_readable")
    assert check["ok"] is False
