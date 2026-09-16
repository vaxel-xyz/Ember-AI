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
