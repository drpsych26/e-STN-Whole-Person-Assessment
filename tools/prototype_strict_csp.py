#!/usr/bin/env python3
"""Remove inline event handlers from the prototype pages and pin their single inline script by hash.

    python tools/prototype_strict_csp.py           # rewrite the prototype pages
    python tools/prototype_strict_csp.py --check   # exit 1 if a page has inline handlers, 'unsafe-inline'
                                                   # in script-src, or a script hash that doesn't match

Every on*="..." attribute becomes data-action / data-change, handled by one delegated listener
(an allow-list of function names; no eval). Each page keeps exactly one inline script, permitted
by its SHA-256 in the Content-Security-Policy instead of 'unsafe-inline'. Style attributes and
<style> blocks still need style-src 'unsafe-inline' (lower risk; tracked separately).
"""
from __future__ import annotations

import base64
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["prototype/index.html", "prototype/STN-Whole-Person-Assessment-Standalone.html",
         "prototype/follow-up-assessment.html"]
MARK = "/* STN strict-CSP dispatcher */"

STATIC = {
    "onclick=\"location.assign(&quot;follow-up-assessment.html&quot;)\"": 'data-action="goFollowUp"',
    "onclick=\"saveData();show('safety')\"": 'data-action="saveDataThenSafety"',
    'onclick="window.print()"': 'data-action="print"',
}
GENERATED = {
    # handlers built inside JavaScript strings
    """ onchange="setAnswer(&quot;'+q[0]+'&quot;,this.value)\"""": """ data-change="setAnswer" data-q="'+q[0]+'\"""",
    """ onclick="setRisk(&quot;'+q[0]+'&quot;,&quot;'+value+'&quot;)\"""": """ data-action="setRisk" data-q="'+q[0]+'" data-value="'+value+'\"""",
}
SHOW = re.compile(r"""onclick="show\('([a-z]+)'\)\"""")
CALL = re.compile(r'onclick="([A-Za-z]+)\(\)"')

DISPATCHER = MARK + """
(function(){
  var actions={
    show:function(t){show(t.getAttribute('data-arg'));},
    goFollowUp:function(){location.assign('follow-up-assessment.html');},
    saveDataThenSafety:function(){saveData();show('safety');},
    print:function(){window.print();},
    setRisk:function(t){setRisk(t.getAttribute('data-q'),t.getAttribute('data-value'));}
  };
  var changes={setAnswer:function(t){setAnswer(t.getAttribute('data-q'),t.value);}};
%s
  if(typeof document.addEventListener!=='function'){return;}
  document.addEventListener('click',function(e){
    var t=e.target&&e.target.closest?e.target.closest('[data-action]'):null;
    if(!t){return;}
    var fn=actions[t.getAttribute('data-action')];
    if(fn){fn(t);}
  });
  document.addEventListener('change',function(e){
    var t=e.target;
    if(!t||!t.getAttribute){return;}
    var fn=changes[t.getAttribute('data-change')];
    if(fn){fn(t);}
  });
})();
"""


def _script(html: str) -> re.Match:
    scripts = list(re.finditer(r"<script>([\s\S]*?)</script>", html))
    if len(scripts) != 1:
        raise SystemExit(f"expected exactly one inline script, found {len(scripts)}")
    return scripts[0]


def _hash(js: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(js.encode("utf-8")).digest()).decode() + "'"


def rewrite(html: str) -> str:
    for old, new in {**STATIC, **GENERATED}.items():
        html = html.replace(old, new)
    html = SHOW.sub(r'data-action="show" data-arg="\1"', html)
    names = sorted(set(CALL.findall(html)))
    html = CALL.sub(r'data-action="\1"', html)
    m = _script(html)
    js = m.group(1)
    if MARK not in js:
        bind = "\n".join(f"  if(typeof {n}==='function'){{actions.{n}=function(){{{n}();}};}}" for n in names)
        js = js.rstrip() + "\n" + DISPATCHER % bind + "\n"
        html = html[:m.start(1)] + js + html[m.end(1):]
    js = _script(html).group(1)
    html = re.sub(r"script-src [^;\"]*", "script-src " + _hash(js), html, count=1)
    return html


def problems(html: str) -> list[str]:
    out = []
    if re.search(r"""\son[a-z]+=["']""", html) or re.search(r"""\son[a-z]+=&quot;""", html):
        out.append("inline event handler present")
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]*)"', html)
    if not csp:
        out.append("no Content-Security-Policy")
    else:
        script_src = re.search(r"script-src ([^;]*)", csp.group(1)).group(1)
        if "unsafe-inline" in script_src:
            out.append("script-src allows 'unsafe-inline'")
        if _hash(_script(html).group(1)) not in script_src:
            out.append("script-src hash does not match the inline script")
    return out


def main(argv: list[str]) -> int:
    failed = False
    for rel in PAGES:
        path = ROOT / rel
        html = path.read_text(encoding="utf-8")
        if "--check" not in argv:
            html = rewrite(html)
            path.write_text(html, encoding="utf-8")
        issues = problems(html)
        print(("FAIL " if issues else "ok   ") + rel + (": " + "; ".join(issues) if issues else ""))
        failed |= bool(issues)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
