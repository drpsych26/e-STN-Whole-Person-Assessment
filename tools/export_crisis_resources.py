#!/usr/bin/env python3
"""Regenerate frontend/crisis-panel/crisis-resources.js from the backend register.

    python tools/export_crisis_resources.py          # write
    python tools/export_crisis_resources.py --check  # exit 1 if the bundled copy is out of date
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend" / "app" / "data" / "crisis_resources.json"
TARGET = ROOT / "frontend" / "crisis-panel" / "crisis-resources.js"
HEADER = "/* GENERATED from backend/app/data/crisis_resources.json by tools/export_crisis_resources.py. Do not edit. */\n"


def render() -> str:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    return HEADER + "window.STN_CRISIS_RESOURCES = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"


def main(argv: list[str]) -> int:
    expected = render()
    if "--check" in argv:
        if TARGET.read_text(encoding="utf-8") != expected:
            print("FAIL frontend/crisis-panel/crisis-resources.js is out of date; run tools/export_crisis_resources.py")
            return 1
        print("crisis-resources.js matches the backend register")
        return 0
    TARGET.write_text(expected, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
