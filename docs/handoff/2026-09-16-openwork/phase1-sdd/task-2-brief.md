### Task 2: Manifest schema, service manifests, validator

**Files:**
- Modify: `services/schema/service-manifest.v1.json`
- Create: `services/{litellm,litellm-postgres,ember-api,ember-dashboard,omlx,qdrant}/manifest.yaml`, `scripts/validate-manifests.py`, `tests/test-manifests.sh`

**Interfaces:**
- Produces: manifest fields consumed by `ember_api.manifests.load_manifests()` (Task 4): `service.id, name, host_env, default_host, port, health, health_timeout, type ∈ {docker, external}, category, ui_path, external_link, public_url_env, x_ember.{node, role, managed, capabilities[], health_probe ∈ {http, omlx, litellm, postgres}}`.

- [ ] **Step 1: Extend the schema**

In `services/schema/service-manifest.v1.json`, under `properties.service.properties`:
- change `"type"` enum to `["docker", "external"]` (find the existing `type` property; if it has `enum: ["docker","host-systemd"]` replace it).
- add:

```json
"x_ember": {
  "type": "object",
  "required": ["node", "role", "managed"],
  "properties": {
    "node": {"type": "string", "enum": ["docker01", "jons-mac-mini"]},
    "role": {"type": "string", "enum": ["gateway", "control", "inference", "storage", "observability"]},
    "managed": {"type": "boolean"},
    "capabilities": {"type": "array", "items": {"type": "string", "enum": ["llm", "vision", "embeddings", "rerank", "stt", "tts"]}},
    "health_probe": {"type": "string", "enum": ["http", "omlx", "litellm", "postgres"], "default": "http"}
  },
  "additionalProperties": false
}
```

Remove `features` from `required`/properties if present at top level (keep schema otherwise intact).

- [ ] **Step 2: Write the six manifests**

`services/omlx/manifest.yaml`:

```yaml
schema_version: ods.services.v1
service:
  id: omlx
  name: oMLX
  host_env: OMLX_HOST
  default_host: 172.20.142.184
  port: 8000
  health: /health
  health_timeout: 5
  ui_path: /docs
  public_url_env: OMLX_PUBLIC_URL
  type: external
  category: core
  x_ember:
    node: jons-mac-mini
    role: inference
    managed: false
    capabilities: [llm, vision, embeddings, rerank, stt, tts]
    health_probe: omlx
```

`services/litellm/manifest.yaml`:

```yaml
schema_version: ods.services.v1
service:
  id: litellm
  name: LiteLLM Gateway
  host_env: LITELLM_HOST
  default_host: litellm
  port: 4000
  external_port_env: LITELLM_PORT
  external_port_default: 4000
  health: /health/readiness
  health_timeout: 5
  ui_path: /ui/
  public_url_env: LLM_PUBLIC_URL
  type: docker
  category: core
  x_ember: {node: docker01, role: gateway, managed: true, health_probe: litellm}
```

`services/litellm-postgres/manifest.yaml`:

```yaml
schema_version: ods.services.v1
service:
  id: litellm-postgres
  name: LiteLLM Postgres
  default_host: litellm-postgres
  port: 5432
  health: ""
  type: docker
  category: core
  external_link: false
  x_ember: {node: docker01, role: storage, managed: true, health_probe: postgres}
```

`services/ember-api/manifest.yaml`:

```yaml
schema_version: ods.services.v1
service:
  id: ember-api
  name: Ember API
  default_host: ember-api
  port: 3002
  external_port_env: EMBER_API_PORT
  external_port_default: 3002
  health: /api/health
  type: docker
  category: core
  external_link: false
  x_ember: {node: docker01, role: control, managed: true, health_probe: http}
```

`services/ember-dashboard/manifest.yaml`:

```yaml
schema_version: ods.services.v1
service:
  id: ember-dashboard
  name: Ember Dashboard
  default_host: ember-dashboard
  port: 3001
  external_port_env: EMBER_DASHBOARD_PORT
  external_port_default: 3001
  health: /
  ui_path: /
  public_url_env: EMBER_PUBLIC_URL
  type: docker
  category: core
  x_ember: {node: docker01, role: control, managed: true, health_probe: http}
```

`services/qdrant/manifest.yaml`:

```yaml
schema_version: ods.services.v1
service:
  id: qdrant
  name: Qdrant
  default_host: qdrant
  port: 6333
  external_port_env: QDRANT_PORT
  external_port_default: 6333
  health: /healthz
  ui_path: /dashboard
  type: docker
  category: optional
  x_ember: {node: docker01, role: storage, managed: true, health_probe: http}
```

- [ ] **Step 3: Write the failing validator test**

`tests/test-manifests.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/validate-manifests.py services >/dev/null
# negative case: a manifest with a bad x_ember.node must fail
tmp=$(mktemp -d); mkdir -p "$tmp/bad"
sed 's/node: docker01/node: laptop/' services/litellm/manifest.yaml > "$tmp/bad/manifest.yaml"
if python3 scripts/validate-manifests.py "$tmp" >/dev/null 2>&1; then echo "FAIL: bad node accepted"; exit 1; fi
echo "manifests OK"
```

Run: `bash tests/test-manifests.sh` → Expected: FAIL (`scripts/validate-manifests.py` missing).

- [ ] **Step 4: Write the validator**

`scripts/validate-manifests.py`:

```python
#!/usr/bin/env python3
"""Validate every services/<id>/manifest.yaml against services/schema/service-manifest.v1.json."""
import json
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "services" / "schema" / "service-manifest.v1.json").read_text())


def validate_dir(services_dir: Path) -> list[str]:
    errors: list[str] = []
    for manifest in sorted(services_dir.glob("*/manifest.yaml")):
        data = yaml.safe_load(manifest.read_text())
        try:
            jsonschema.validate(data, SCHEMA)
        except jsonschema.ValidationError as exc:
            errors.append(f"{manifest}: {exc.message}")
            continue
        if data["service"]["id"] != manifest.parent.name:
            errors.append(f"{manifest}: service.id must equal directory name")
    return errors


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "services"
    problems = validate_dir(target)
    for p in problems:
        print(p, file=sys.stderr)
    print(f"validated {len(list(target.glob('*/manifest.yaml')))} manifests, {len(problems)} errors")
    sys.exit(1 if problems else 0)
```

- [ ] **Step 5: Run test, commit**

Run: `pip install --quiet jsonschema pyyaml && bash tests/test-manifests.sh` → Expected: `manifests OK`.

```bash
git add services scripts tests/test-manifests.sh
git commit -m "feat: Ember service manifests with x_ember extension and validator"
```

---

