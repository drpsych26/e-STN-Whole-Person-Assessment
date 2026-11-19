"""Apply brand assets and font declarations to the generated Flutter project.

Run from the generated project root. Copies the maintained brand assets and
fonts into the project and adds their declarations to pubspec.yaml exactly
once. Idempotent: re-running does not duplicate declarations.
"""
import shutil
import sys
from pathlib import Path

PATCH = Path(__file__).resolve().parent
PROJECT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

FONT_FILES = {
    "Manrope": [
        (400, "Manrope_400Regular.ttf"),
        (500, "Manrope_500Medium.ttf"),
        (600, "Manrope_600SemiBold.ttf"),
        (700, "Manrope_700Bold.ttf"),
    ],
    "SourceSerif4": [
        (400, "SourceSerif4_400Regular.ttf"),
        (600, "SourceSerif4_600SemiBold.ttf"),
        (700, "SourceSerif4_700Bold.ttf"),
    ],
}
LOGO = "assets/brand/stn-logo-original.png"
MARK = "# STN-BRAND-ASSETS"

for src_dir, dst in [("assets/fonts", "assets/fonts"), ("assets/brand", "assets/brand")]:
    (PROJECT / dst).mkdir(parents=True, exist_ok=True)
    for f in (PATCH / src_dir).iterdir():
        if f.is_file():
            shutil.copy2(f, PROJECT / dst / f.name)

for licence in ["OFL-Manrope.txt", "OFL-SourceSerif4.txt"]:
    shutil.copy2(PATCH / "assets/fonts" / licence, PROJECT / "assets/fonts" / licence)

pubspec = PROJECT / "pubspec.yaml"
lines = pubspec.read_text(encoding="utf-8").splitlines()
if any(MARK in line for line in lines):
    print("pubspec already patched; nothing to do")
    sys.exit(0)

# Locate the top-level flutter: section (from its header to the next top-level key).
try:
    head = lines.index("flutter:")
except ValueError:
    head = None
if head is None:
    body_end = len(lines)
    kept = ["  uses-material-design: true"]
    lines = lines + [""]
    section_start = len(lines)
else:
    body_end = head + 1
    while body_end < len(lines) and (lines[body_end].strip() == "" or lines[body_end].startswith(" ")):
        body_end += 1
    kept = []
    for line in lines[head + 1:body_end]:
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip(" "))
        # Drop any previous assets/fonts entries (indent > 2) and the assets/fonts keys.
        if indent > 2:
            continue
        if line.strip() in ("assets:", "fonts:"):
            continue
        kept.append(line)
    if not any("uses-material-design" in k for k in kept):
        kept.insert(0, "  uses-material-design: true")

section = [MARK, "flutter:"] + kept + ["  assets:", f"    - {LOGO}",
           "    - assets/fonts/OFL-Manrope.txt", "    - assets/fonts/OFL-SourceSerif4.txt", "  fonts:"]
for family, files in FONT_FILES.items():
    section.append(f"    - family: {family}")
    section.append("      fonts:")
    for weight, name in files:
        section.append(f"        - asset: assets/fonts/{name}")
        section.append(f"          weight: {weight}")

if head is None:
    out = lines[:-1] + section + [""]
else:
    out = lines[:head] + section + lines[body_end:]
pubspec.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
print("pubspec flutter section written with brand assets and fonts")
