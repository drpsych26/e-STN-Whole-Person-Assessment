"""Static checks on prototype pages: a Content-Security-Policy is present and not weakened
beyond the documented exception (inline script, pending removal of inline handlers, D-014)."""
from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGES = sorted((ROOT / "prototype").glob("*.html"))
CSP_RE = re.compile(r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"', re.IGNORECASE)


def _policy(page: pathlib.Path) -> dict[str, list[str]]:
    match = CSP_RE.search(page.read_text(encoding="utf-8"))
    assert match, f"{page.name}: no Content-Security-Policy meta tag"
    directives = {}
    for part in match.group(1).split(";"):
        tokens = part.strip().split()
        if tokens:
            directives[tokens[0]] = tokens[1:]
    return directives


def test_prototype_pages_exist():
    assert PAGES, "no prototype pages found"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_csp_is_present_and_restrictive(page):
    d = _policy(page)
    assert d.get("default-src") == ["'self'"]
    assert d.get("object-src") == ["'none'"]
    assert d.get("base-uri") == ["'none'"]
    assert d.get("form-action") == ["'self'"]


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_csp_forbids_eval_and_wildcards(page):
    d = _policy(page)
    for directive, sources in d.items():
        assert "'unsafe-eval'" not in sources, f"{directive} allows eval"
        assert "*" not in sources, f"{directive} uses a wildcard"
        assert "data:" not in sources or directive == "img-src", f"{directive} allows data: URLs"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_no_external_script_or_frame(page):
    text = page.read_text(encoding="utf-8")
    assert not re.search(r"<script[^>]+src=[\"']https?://", text, re.IGNORECASE)
    assert not re.search(r"<iframe", text, re.IGNORECASE)
