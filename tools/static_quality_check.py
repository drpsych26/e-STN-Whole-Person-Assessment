#!/usr/bin/env python3
"""Static checks for HTML JavaScript and the authoritative reconstructed Flutter v4 archive.
These checks do not establish runtime, clinical, privacy, security, or production readiness.
"""
from html.parser import HTMLParser
from pathlib import Path
import base64
import hashlib
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HTML_DIRS = [ROOT / "source" / "html", ROOT / "prototype", ROOT / "reference"]
PART_DIR = ROOT / "flutter" / "source-archives" / "parts"
EXPECTED_SHA256 = "4478e3e54131fdb94db943524a7aa00cef9239122e572eaad6d9e0d5ad95261c"
EXPECTED_B64_LENGTH = 18404

class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.external = False
        self.current = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self.in_script = True
            self.external = any(k.lower() == "src" for k, _ in attrs)
            self.current = []

    def handle_data(self, data):
        if self.in_script and not self.external:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.in_script:
            if not self.external:
                self.scripts.append("".join(self.current))
            self.in_script, self.external, self.current = False, False, []

def check_flutter_archive():
    parts = [PART_DIR / "part1.txt", PART_DIR / "part2.txt", PART_DIR / "part4.txt"]
    missing = [str(p) for p in parts if not p.is_file()]
    if missing:
        raise ValueError("Missing authoritative Flutter archive chunks: " + ", ".join(missing))
    encoded = b"".join(p.read_bytes().strip() for p in parts)
    if len(encoded) != EXPECTED_B64_LENGTH:
        raise ValueError(f"Encoded Flutter archive length mismatch: {len(encoded)}")
    archive = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(archive).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Flutter archive SHA-256 mismatch: {digest}")
    import io
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        bad = zf.testzip()
        if bad:
            raise ValueError("Corrupt Flutter ZIP member: " + bad)
        if not any(name.endswith("pubspec.yaml") for name in zf.namelist()):
            raise ValueError("Flutter archive does not contain pubspec.yaml")
        count = len(zf.namelist())
    print(f"PASS authoritative Flutter v4 archive: SHA-256 {digest}; {count} members")

def main():
    failed = False
    html_files = [p for d in HTML_DIRS if d.exists() for p in d.rglob("*.html")]
    if not html_files:
        print("ERROR: no HTML files found in expected paths")
        return 2
    for html in html_files:
        parser = ScriptParser()
        parser.feed(html.read_text(encoding="utf-8", errors="replace"))
        count, file_failed = 0, False
        for idx, script in enumerate(parser.scripts):
            if not script.strip():
                continue
            count += 1
            with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as tmp:
                tmp.write(script)
                temp_path = Path(tmp.name)
            try:
                result = subprocess.run(["node", "--check", str(temp_path)], text=True, capture_output=True)
                if result.returncode:
                    failed = file_failed = True
                    print(f"FAIL JS syntax: {html} script {idx}\\n{result.stderr}")
            finally:
                temp_path.unlink(missing_ok=True)
        print(f"{'FAIL' if file_failed else 'PASS'} HTML inline JS parse: {html} ({count} non-empty inline scripts checked)")
    try:
        check_flutter_archive()
    except Exception as exc:
        failed = True
        print(f"FAIL Flutter archive integrity: {exc}")
    print("NOTE: static checks do not test browser runtime, clinical correctness, security, privacy, or production readiness.")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
