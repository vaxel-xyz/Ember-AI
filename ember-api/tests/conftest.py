from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LITELLM_TEMPLATE = ROOT / "config/litellm/ember.yaml.tmpl"


@pytest.fixture
def env():
    return {
        "EMBER_API_KEY": "test-key", "OMLX_HOST": "10.0.0.5", "OMLX_BASE_URL": "http://10.0.0.5:8000", "OMLX_API_KEY": "omlx-k",
        "LITELLM_MASTER_KEY": "sk-master", "LLM_PUBLIC_URL": "https://ai.vaxel.xyz/v1", "LLM_INTERNAL_URL": "http://172.20.142.7:4000/v1",
        "OMLX_PUBLIC_URL": "https://omlx.vaxel.xyz", "EMBER_PUBLIC_URL": "https://ember.vaxel.xyz",
        "OPENWEBUI_HOST": "172.20.142.7", "CHAT_PUBLIC_URL": "https://chat.vaxel.xyz",
        "EMBER_LITELLM_TEMPLATE": str(LITELLM_TEMPLATE),
    }


@pytest.fixture
def services_dir():
    return ROOT / "services"


@pytest.fixture
def litellm_template():
    return LITELLM_TEMPLATE
