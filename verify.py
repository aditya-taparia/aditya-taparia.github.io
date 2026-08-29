#!/usr/bin/env python3
"""Post-build checks for aditya-taparia.github.io.

Run after build.py. Exits non-zero on any failure so CI catches a broken
build before it reaches GitHub Pages.

Usage:  python3 verify.py
"""

import hashlib
import html.parser
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))

GENERATED = ["index.html", "papers/index.html", "404.html",
             "llms.txt", "sitemap.xml", "robots.txt"]

# Claims that were never verified at source and must not appear anywhere.
FORBIDDEN = ["Qualcomm", "Outstanding Student Award"]

failures = []
checks = 0


def check(name, condition, detail=""):
    global checks
    checks += 1
    if condition:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s%s" % (name, (": " + detail) if detail else ""))
        failures.append(name + ((": " + detail) if detail else ""))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def all_html():
    """Generated pages only. `pages/` holds hand-edited fragments that have no
    <head> of their own, and google*.html are search-engine verification files
    whose content is fixed by Google; both are checked separately."""
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".github", "node_modules",
                                    "docs", "pages")]
        for fn in filenames:
            if fn.endswith(".html") and not fn.startswith("google"):
                out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    return sorted(out)


def verification_files():
    return sorted(f for f in os.listdir(ROOT)
                  if f.startswith("google") and f.endswith(".html"))


def fragments():
    d = os.path.join(ROOT, "pages")
    if not os.path.isdir(d):
        return []
    return sorted("pages/" + f for f in os.listdir(d) if f.endswith(".html"))


# ------------------------------------------------------------- 1. parses ---

class Parser(html.parser.HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.links = []
        self.ld = []
        self._in_ld = False
        self._ld_buf = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in ("a", "link"):
            if d.get("href"):
                self.links.append(d["href"])
        if tag in ("img", "script", "source") and d.get("src"):
            self.links.append(d["src"])
        if tag == "script" and d.get("type") == "application/ld+json":
            self._in_ld = True
            self._ld_buf = ""
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ld.append(self._ld_buf)
            self._in_ld = False
        if tag in self.VOID:
            return
        if not self.stack:
            self.errors.append("stray </%s>" % tag)
        elif self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errors.append("unclosed <%s>" % self.stack.pop())
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append("stray </%s>" % tag)

    def handle_data(self, data):
        if self._in_ld:
            self._ld_buf += data


print("\nHTML structure")
pages = all_html()
for frag in fragments():
    p = Parser()
    p.feed(read(frag))
    leftover = [t for t in p.stack if t not in ("html", "body")]
    check("%s (source fragment) parses" % frag, not p.errors and not leftover,
          "; ".join(p.errors + ["unclosed <%s>" % t for t in leftover])[:200])

parsers = {}
for page in pages:
    p = Parser()
    p.feed(read(page))
    leftover = [t for t in p.stack if t not in ("html", "body")]
    parsers[page] = p
    check("%s parses" % page, not p.errors and not leftover,
          "; ".join(p.errors + ["unclosed <%s>" % t for t in leftover])[:200])


# --------------------------------------------------------------- 2. links ---

print("\nInternal links and assets")
for page, p in parsers.items():
    page_dir = os.path.dirname(os.path.join(ROOT, page))
    bad = []
    for href in p.links:
        if re.match(r"^(https?:|mailto:|data:|#|javascript:)", href):
            continue
        target = href.split("#")[0].split("?")[0]
        if not target:
            continue
        if target.startswith("/"):
            resolved = os.path.join(ROOT, target.lstrip("/"))
        else:
            resolved = os.path.normpath(os.path.join(page_dir, target))
        if os.path.isdir(resolved):
            resolved = os.path.join(resolved, "index.html")
        if not os.path.exists(resolved):
            bad.append(href)
    check("%s links resolve" % page, not bad, ", ".join(bad[:5]))


# -------------------------------------------------------------- 3. JSON-LD ---

print("\nStructured data")
ld_count = 0
for page, p in parsers.items():
    for blob in p.ld:
        ld_count += 1
        try:
            json.loads(blob)
        except ValueError as exc:
            check("%s JSON-LD parses" % page, False, str(exc)[:120])
            break
    else:
        if p.ld:
            check("%s JSON-LD parses (%d block/s)" % (page, len(p.ld)), True)
check("JSON-LD present on every page", ld_count >= len(pages) - 1,
      "%d blocks across %d pages" % (ld_count, len(pages)))


# --------------------------------------------------------------- 4. BibTeX ---

print("\nBibTeX")
pubs = json.loads(read("data/publications.json"))
for pub in pubs:
    bib = pub["bibtex"]
    ok = True
    detail = ""
    m = re.match(r"^@(\w+)\{([^,}]+),", bib)
    if not m:
        ok, detail = False, "header is not @type{key,  -> %r" % bib[:40]
    elif bib.count("{") != bib.count("}"):
        ok, detail = False, "unbalanced braces (%d open, %d close)" % (
            bib.count("{"), bib.count("}"))
    elif not bib.rstrip().endswith("}"):
        ok, detail = False, "does not end with }"
    check("bibtex %s" % pub["slug"], ok, detail)


# --------------------------------------------------------------- 5. sitemap ---

print("\nSitemap")
try:
    tree = ET.fromstring(read("sitemap.xml"))
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in tree.findall(".//s:loc", ns)]
    check("sitemap.xml is well-formed", True)
    check("sitemap has %d urls" % len(locs), len(locs) == len(pubs) + 3,
          "expected %d, got %d" % (len(pubs) + 3, len(locs)))
    missing = []
    for loc in locs:
        rel = loc.replace("https://aditya-taparia.github.io", "").lstrip("/")
        path = os.path.join(ROOT, rel) if rel else os.path.join(ROOT, "index.html")
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if not rel:
            path = os.path.join(ROOT, "index.html")
        if not os.path.exists(path):
            missing.append(loc)
    check("every sitemap url exists on disk", not missing, ", ".join(missing[:3]))
except ET.ParseError as exc:
    check("sitemap.xml is well-formed", False, str(exc))


# ------------------------------------------------------------ 6. inventory ---

print("\nContent inventory")
index = read("index.html")
n_conf = sum(1 for p in pubs if p["category"] == "conference")
n_pre = sum(1 for p in pubs if p["category"] == "preprint")

check("publications load (%d)" % len(pubs), len(pubs) > 0)
check("tab counts sum to the total (%d = %d + %d)" % (len(pubs), n_conf, n_pre),
      n_conf + n_pre == len(pubs),
      "%d conference + %d preprint != %d total" % (n_conf, n_pre, len(pubs)))
check("homepage tab labels match the real counts",
      all(('(%d)' % n) in index for n in (len(pubs), n_conf, n_pre)),
      "expected (%d) (%d) (%d)" % (len(pubs), n_conf, n_pre))

orphans = []
if os.path.isdir(os.path.join(ROOT, "papers")):
    slugs = {p["slug"] for p in pubs}
    orphans = [d for d in os.listdir(os.path.join(ROOT, "papers"))
               if os.path.isdir(os.path.join(ROOT, "papers", d)) and d not in slugs]
check("no orphaned paper pages", not orphans,
      "delete papers/%s/" % ", papers/".join(orphans))

missing_titles = [p["slug"] for p in pubs
                  if p["title"].split(":")[0][:40] not in index]
check("every paper appears on the homepage", not missing_titles,
      ", ".join(missing_titles))

missing_pages = [p["slug"] for p in pubs
                 if not os.path.exists(os.path.join(ROOT, "papers", p["slug"], "index.html"))]
check("every paper has a landing page", not missing_pages, ", ".join(missing_pages))

for pub in pubs:
    page = read("papers/%s/index.html" % pub["slug"])
    n_authors = page.count('name="citation_author"')
    if n_authors != len(pub["authors"]):
        check("citation_author count for %s" % pub["slug"], False,
              "expected %d, got %d" % (len(pub["authors"]), n_authors))
check("citation_* tags on all paper pages", True)

check("homepage says second-year", "second-year" in index)
check("no client-side fetch of content", "fetch('pages/" not in index
      and 'fetch("pages/' not in index)
check("no jQuery", "jquery" not in index.lower())

# The original bug: <table width="900"> forced horizontal scrolling on phones
# regardless of the viewport meta tag.
print("\nResponsive layout")
for page in pages:
    src = read(page)
    fixed = re.findall(r'<(?:table|div|td)[^>]*\swidth="(\d{3,})"', src)
    check("%s has no fixed pixel widths" % page, not fixed,
          "width=" + ", ".join(fixed[:3]))
check("viewport meta on every page",
      all('name="viewport"' in read(p) for p in pages))
check("charset is first meta on every page",
      all(re.search(r'<head>\s*<meta charset="utf-8">', read(p)) for p in pages))


# ----------------------------------------------------------- 7. forbidden ---

print("\nSearch engine verification")
vfiles = verification_files()
check("a Google verification file is present", bool(vfiles),
      "expected google<token>.html at the repo root")
for vf in vfiles:
    # Google fetches this file and requires its body to name the file itself.
    body = read(vf).strip()
    check("%s content matches its filename" % vf,
          body == "google-site-verification: " + vf, "body is %r" % body[:60])
    check("%s is at the site root" % vf,
          os.path.exists(os.path.join(ROOT, vf)))
    # It must never be pruned or rewritten by the build.
    check("%s survives a rebuild" % vf, os.path.getsize(os.path.join(ROOT, vf)) > 0)

print("\nUnverified claims must not appear")
for term in FORBIDDEN:
    hits = [p for p in pages + ["llms.txt"] if term.lower() in read(p).lower()]
    check("%r absent from output" % term, not hits, ", ".join(hits))


# --------------------------------------------------------- 8. idempotency ---

print("\nIdempotency")


def snapshot():
    digest = {}
    for page in all_html() + ["llms.txt", "sitemap.xml", "robots.txt"]:
        with open(os.path.join(ROOT, page), "rb") as fh:
            digest[page] = hashlib.sha256(fh.read()).hexdigest()
    return digest


before = snapshot()
result = subprocess.run([sys.executable, os.path.join(ROOT, "build.py")],
                        capture_output=True, text=True, cwd=ROOT)
check("rebuild exits 0", result.returncode == 0, result.stderr[-200:])
after = snapshot()
changed = [k for k in before if before.get(k) != after.get(k)]
check("rebuild produces identical output", not changed, ", ".join(changed[:5]))


# ------------------------------------------------------------------ done ---

print("\n%d checks, %d failed" % (checks, len(failures)))
if failures:
    print("\nFailures:")
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("All checks passed.")
