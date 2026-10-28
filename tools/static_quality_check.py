#!/usr/bin/env python3
"""Static checks only: inline JS syntax and ZIP integrity. Not an E2E/clinical safety test."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess, sys, tempfile, zipfile

ROOT = Path(__file__).resolve().parents[1]
HTML_DIRS = [ROOT / "source" / "html", ROOT / "prototype", ROOT / "reference"]
ZIP_DIRS = [ROOT / "source" / "flutter", ROOT / "flutter"]

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
                    print(f"FAIL JS syntax: {html} script {idx}\n{result.stderr}")
            finally:
                temp_path.unlink(missing_ok=True)
        print(f"{'FAIL' if file_failed else 'PASS'} HTML inline JS parse: {html} ({count} non-empty inline scripts checked)")
    zip_files = [p for d in ZIP_DIRS if d.exists() for p in d.rglob("*.zip")]
    for archive in zip_files:
        try:
            with zipfile.ZipFile(archive) as zf:
                bad = zf.testzip()
            if bad:
                failed = True
                print(f"FAIL ZIP integrity: {archive}: {bad}")
            else:
                print(f"PASS ZIP integrity: {archive}")
        except Exception as exc:
            failed = True
            print(f"FAIL ZIP integrity: {archive}: {exc}")
    print("NOTE: static checks do not test browser runtime, clinical correctness, security, privacy, or production readiness.")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
