"""Apply the clinician API code to the generated Flutter project.

Usage (from CI, in the generated project root):
    python3 <patch_root>/apply_clinician_api.py . --variant default
    python3 <patch_root>/apply_clinician_api.py . --variant api

default  Copies the API layer, the clinician screens and their tests. Platform
         files are offline stubs, so the build has no sign-in plugin, no HTTP
         client, no new dependency, no new Android permission and no redirect
         activity. pubspec.yaml and AndroidManifest.xml are left untouched. With
         STN_API_ENABLED off (the default) the sign-in entry is not shown.
api      Everything in default, then swaps in the AppAuth sign-in adapter and the
         package:http transport (api_variant/), adds http and flutter_appauth to
         pubspec.yaml, sets the AppAuth redirect scheme
         (network.supportivetherapy.app) in android/app/build.gradle(.kts), and
         adds the INTERNET permission to the main AndroidManifest.xml.

Idempotent: re-running does not duplicate any change.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

PATCH = Path(__file__).resolve().parent
MARK = "STN-CLINICIAN-API"
REDIRECT_SCHEME = "network.supportivetherapy.app"
DEPENDENCIES = {"http": "^1.6.0", "flutter_appauth": "^13.0.0"}


def copy_tree(src: Path, dst: Path) -> list[str]:
    copied = []
    dst.mkdir(parents=True, exist_ok=True)
    for file in sorted(src.glob("*.dart")):
        shutil.copy2(file, dst / file.name)
        copied.append(str(dst / file.name))
    return copied


def copy_common(project: Path) -> None:
    copy_tree(PATCH / "lib/api", project / "lib/api")
    copy_tree(PATCH / "lib/screens/clinician", project / "lib/screens/clinician")
    (project / "test").mkdir(exist_ok=True)
    for test in sorted((PATCH / "test").glob("clinician_*_test.dart")):
        shutil.copy2(test, project / "test" / test.name)


def add_dependencies(pubspec: Path) -> None:
    text = pubspec.read_text(encoding="utf-8")
    if MARK in text:
        return
    lines = text.splitlines()
    try:
        index = lines.index("dependencies:")
    except ValueError:
        sys.exit("pubspec.yaml has no top-level 'dependencies:' section")
    block = [f"  # {MARK}: clinician API build variant only"]
    block += [f"  {name}: {version}" for name, version in DEPENDENCIES.items()]
    lines[index + 1:index + 1] = block
    pubspec.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_redirect_scheme(android_app: Path) -> None:
    kts, groovy = android_app / "build.gradle.kts", android_app / "build.gradle"
    if kts.exists():
        target, snippet = kts, (
            f"        // {MARK}: AppAuth redirect scheme (clinician API build variant only)\n"
            f'        manifestPlaceholders.putAll(mapOf("appAuthRedirectScheme" to "{REDIRECT_SCHEME}"))\n'
        )
    elif groovy.exists():
        target, snippet = groovy, (
            f"        // {MARK}: AppAuth redirect scheme (clinician API build variant only)\n"
            f"        manifestPlaceholders += [appAuthRedirectScheme: '{REDIRECT_SCHEME}']\n"
        )
    else:
        sys.exit(f"No Android app build file under {android_app}")
    text = target.read_text(encoding="utf-8")
    if MARK in text:
        return
    match = re.search(r"^\s*defaultConfig\s*\{\s*\n", text, flags=re.MULTILINE)
    if not match:
        sys.exit(f"No defaultConfig block in {target}")
    target.write_text(text[:match.end()] + snippet + text[match.end():], encoding="utf-8")


def add_internet_permission(manifest: Path) -> None:
    text = manifest.read_text(encoding="utf-8")
    if "android.permission.INTERNET" in text:
        return
    match = re.search(r"<manifest\b[^>]*>\s*\n", text)
    if not match:
        sys.exit(f"No <manifest> element in {manifest}")
    line = f'    <!-- {MARK}: clinician API build variant only -->\n' \
           '    <uses-permission android:name="android.permission.INTERNET"/>\n'
    manifest.write_text(text[:match.end()] + line + text[match.end():], encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--variant", choices=("default", "api"), required=True)
    args = parser.parse_args()
    project = Path(args.project).resolve()
    if not (project / "pubspec.yaml").exists():
        sys.exit(f"{project} is not a Flutter project")

    copy_common(project)
    if args.variant == "default":
        pubspec = (project / "pubspec.yaml").read_text(encoding="utf-8")
        for name in DEPENDENCIES:
            if re.search(rf"^\s+{name}:", pubspec, flags=re.MULTILINE):
                sys.exit(f"default variant must not depend on {name}")
        for name in ("oidc_platform.dart", "transport_platform.dart"):
            source = (project / "lib/api" / name).read_text(encoding="utf-8")
            if re.search(r"""^\s*import\s+["']package:""", source, flags=re.MULTILINE):
                sys.exit(f"default variant lib/api/{name} must be the offline stub")
        print("clinician API code applied (default variant: offline stubs, no new dependencies)")
        return 0

    for name in ("oidc_platform.dart", "transport_platform.dart"):
        shutil.copy2(PATCH / "api_variant" / name, project / "lib/api" / name)
    add_dependencies(project / "pubspec.yaml")
    android_app = project / "android/app"
    if android_app.exists():
        add_redirect_scheme(android_app)
        add_internet_permission(android_app / "src/main/AndroidManifest.xml")
    print("clinician API code applied (api variant: AppAuth + package:http)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
