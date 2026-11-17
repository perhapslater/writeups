"""Validate publication output without making network requests.

Optional PUBLICATION_DENY_TERMS is a JSON list used only by a local audit. Do not
put private identities in this script or in public workflow configuration.
"""
from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PROJECT = re.search(r"^repo_url: https://github.com/perhapslater/([a-z-]+)$", (ROOT / "mkdocs.yml").read_text(), re.M).group(1)
BASE = os.environ.get("SITE_URL", f"https://perhapslater.com/{PROJECT}/").rstrip("/") + "/"
PUBLICATIONS = {"red-team-runbook", "writeups"}


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path, self.ids, self.links, self.meta, self.canonicals = path, set(), [], {}, []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        if tag == "meta":
            self.meta[a.get("property", a.get("name", ""))] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonicals.append(a.get("href", ""))
        for name in ("href", "src", "poster"):
            if name in a:
                self.links.append((tag, name, a[name]))
        if "srcset" in a:
            self.links.extend((tag, "src", item.strip().split()[0]) for item in a["srcset"].split(",") if item.strip())


def main():
    errors = []
    if not SITE.is_dir():
        print("Build the site before running this audit.")
        return 1
    pages = {p.relative_to(SITE).as_posix(): Page(p) for p in SITE.rglob("*.html")}
    base = urlsplit(BASE)
    checked = 0
    for relative, page in pages.items():
        page_url = urljoin(BASE, relative[:-10] if relative.endswith("index.html") else relative)
        for tag, attr, raw in page.links:
            if not raw or raw.startswith(("mailto:", "tel:", "data:", "javascript:")):
                continue
            target = urlsplit(urljoin(page_url, raw))
            if target.scheme not in ("http", "https") or target.netloc != base.netloc:
                continue
            if not target.path.startswith(base.path):
                # Shared publication switch and account-level home live outside this build.
                if target.path in {"/", *(f"/{p}/" for p in PUBLICATIONS)}:
                    continue
                errors.append(f"{relative}: URL escapes publication prefix: {raw}")
                continue
            local = unquote(target.path[len(base.path):])
            file = SITE / local
            if file.is_dir():
                file /= "index.html"
            if not file.is_file():
                errors.append(f"{relative}: missing {attr}: {raw}")
                continue
            checked += 1
            key = file.relative_to(SITE).as_posix()
            if target.fragment and key in pages and unquote(target.fragment) not in pages[key].ids:
                errors.append(f"{relative}: missing anchor: {raw}")
        if relative == "404.html":
            continue
        # Hand-authored redirects intentionally canonicalize to the replacement page.
        redirect = "http-equiv=\"refresh\"" in page.path.read_text(encoding="utf-8").lower()
        if not redirect:
            if page.canonicals != [page_url]:
                errors.append(f"{relative}: incorrect canonical: {page.canonicals!r}; expected {page_url}")
            if page.meta.get("og:url") != page_url:
                errors.append(f"{relative}: incorrect Open Graph URL")
            if page.meta.get("author") != "PerhapsLater":
                errors.append(f"{relative}: unexpected author")
            if page.meta.get("og:image") != BASE + "assets/social-card.png":
                errors.append(f"{relative}: incorrect social image prefix")
    search = json.loads((SITE / "search/search_index.json").read_text(encoding="utf-8"))
    if not search.get("docs"):
        errors.append("Search index is empty")
    for item in search.get("docs", []):
        location = item["location"].split("#", 1)[0]
        file = SITE / unquote(location)
        if file.is_dir():
            file /= "index.html"
        if not file.is_file():
            errors.append(f"Search target is missing: {location}")
    sitemap = ET.parse(SITE / "sitemap.xml")
    for loc in sitemap.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
        if not (loc.text or "").startswith(BASE):
            errors.append(f"Incorrect sitemap URL: {loc.text}")
    if f"Sitemap: {BASE}sitemap.xml" not in (SITE / "robots.txt").read_text():
        errors.append("Incorrect robots.txt sitemap")
    if not (SITE / ".nojekyll").exists():
        errors.append("Missing .nojekyll")
    if (ROOT / "CNAME").exists() or (ROOT / "docs/CNAME").exists() or (SITE / "CNAME").exists():
        errors.append("A project repository must inherit the account domain, without its own CNAME")
    denied = json.loads(os.environ.get("PUBLICATION_DENY_TERMS", "[]"))
    for directory in (ROOT / "docs", ROOT / "overrides", ROOT / "hooks", ROOT / "scripts", ROOT / ".github", SITE):
        for file in directory.rglob("*"):
            if not file.is_file() or file.suffix.lower() in {".png", ".jpg", ".jpeg", ".gz", ".woff", ".woff2", ".pyc"}:
                continue
            try:
                text = file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for term in denied:
                if term.casefold() in text.casefold():
                    errors.append(f"{file.relative_to(ROOT)}: forbidden identity term")
            if re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", text):
                errors.append(f"{file.relative_to(ROOT)}: private key material")
    for file in ROOT.iterdir():
        if file.is_file():
            try:
                text = file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for term in denied:
                if term.casefold() in text.casefold():
                    errors.append(f"{file.name}: forbidden identity term")
    if errors:
        print("Publication audit failed:\n" + "\n".join(f"- {e}" for e in sorted(set(errors))))
        return 1
    print(f"Publication audit passed: {len(pages)} HTML pages, {checked} local references, {len(search['docs'])} search entries; base {BASE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
