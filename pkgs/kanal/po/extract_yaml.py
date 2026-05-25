#!/usr/bin/env python3
"""Append msgid entries from default.yaml to a .pot file (or print to stdout)."""
import sys
from pathlib import Path

import yaml

_TRANSLATABLE_KEYS = {"title", "subtitle", "description", "label"}

_YAML = Path(__file__).parent.parent / "src" / "kanal" / "default.yaml"


def _walk(obj, seen: set, out: list) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _TRANSLATABLE_KEYS and isinstance(v, str) and v not in seen:
                seen.add(v)
                out.append(v)
            else:
                _walk(v, seen, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, seen, out)


def main() -> None:
    data = yaml.safe_load(_YAML.read_text())
    seen: set = set()
    strings: list = []
    _walk(data, seen, strings)

    lines = [
        "",
        "# Strings extracted from default.yaml",
    ]
    for s in strings:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'msgid "{escaped}"')
        lines.append('msgstr ""')
        lines.append("")

    output = "\n".join(lines)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "a") as f:
            f.write(output)
        print(f"Appended {len(strings)} strings to {sys.argv[1]}")
    else:
        print(output)


if __name__ == "__main__":
    main()
