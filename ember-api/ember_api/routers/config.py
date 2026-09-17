import os
from pathlib import Path
from string import Template

from fastapi import APIRouter, Depends

from ..security import require_api_key

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])

TEMPLATE_PATH_ENV = "EMBER_LITELLM_TEMPLATE"
DEFAULT_TEMPLATE_PATH = "/app/config/litellm/ember.yaml.tmpl"

# Secrets LiteLLM resolves via `os.environ/NAME` instead of a ${} placeholder, plus
# ember-api's own bearer. The template cannot advertise these, so they stay explicit.
EXTRA_REQUIRED_ENV = ("EMBER_API_KEY", "OMLX_API_KEY", "LITELLM_MASTER_KEY")


def template_path() -> Path:
    return Path(os.environ.get(TEMPLATE_PATH_ENV) or DEFAULT_TEMPLATE_PATH)


def template_identifiers(path: Path | None = None) -> list[str]:
    """Every ``${VAR}`` the LiteLLM config template interpolates.

    Derived rather than hand-listed: `render-config.py` raises `KeyError` on any missing
    placeholder, so a variable in the template is load-bearing by construction and must
    appear in the required set automatically.
    """
    try:
        text = (path or template_path()).read_text(encoding="utf-8")
    except OSError:
        return []
    return sorted(set(Template(text).get_identifiers()))


def required_env() -> list[str]:
    return sorted(set(template_identifiers()) | set(EXTRA_REQUIRED_ENV))


def run_checks() -> list[dict]:
    tmpl = template_path()
    identifiers = template_identifiers(tmpl)
    checks = [{"name": "litellm_template_readable", "ok": bool(identifiers),
               "message": f"{tmpl} ({len(identifiers)} variables)" if identifiers else f"{tmpl} unreadable or has no ${{VAR}} placeholders"}]
    checks += [{"name": f"env:{k}", "ok": bool(os.environ.get(k)), "message": "set" if os.environ.get(k) else "missing"}
               for k in required_env()]
    base = os.environ.get("OMLX_BASE_URL", "")
    checks.append({"name": "omlx_base_url_is_lan_http", "ok": base.startswith(("http://172.", "http://10.", "http://192.168.")),
                   "message": base or "unset"})
    return checks


@router.get("/config/validate")
async def validate():
    checks = run_checks()
    return {"ok": all(c["ok"] for c in checks), "checks": checks}
