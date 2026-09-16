#!/usr/bin/env python3
"""Render ember.yaml.tmpl by substituting ${VAR} from the environment. Fails on any missing variable."""
import os
import sys
from collections.abc import Mapping
from string import Template


def render(template_text: str, env: Mapping[str, str]) -> str:
    return Template(template_text).substitute(env)  # KeyError names the missing variable


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        rendered = render(f.read(), os.environ)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"rendered {src} -> {dst}")
