"""Check the actual production output: routes, search, images and internal links."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.ids = set()
        self.cards = []
        self.text = []
        self.h1_count = 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if "machine-card" in attrs.get("class", "").split():
            self.cards.append(attrs)

    def handle_data(self, text):
        self.text.append(text)


def validate(site):
    catalog = yaml.safe_load((ROOT / "data/machines.yml").read_text(encoding="utf-8"))
    errors = []
    pages = {p.relative_to(site).as_posix(): Page(p.read_text(encoding="utf-8"))
             for p in site.rglob("*.html")}
    if "index.html" not in pages:
        return ["Build the site before running this check"]
    # Read the build's canonical URL so SITE_URL overrides are checked too.
    home_source = (site / "index.html").read_text(encoding="utf-8")
    canonical = re.search(r'<link[^>]+href="([^"]+)"[^>]+rel="canonical"', home_source)
    if canonical is None:
        canonical = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', home_source)
    if canonical is None:
        return ["Homepage canonical URL is missing"]
    base = urlsplit(canonical[1])
    prefix = base.path.rstrip("/") + "/"
    homepage = pages["index.html"]
    expected_cards = {machine["path"].removesuffix(".md") + "/" for machine in catalog}
    actual_cards = {card["href"] for card in homepage.cards}
    if len(homepage.cards) != len(catalog) or actual_cards != expected_cards:
        errors.append("Machine library and catalog differ")
    search = json.loads((site / "search/search_index.json").read_text(encoding="utf-8"))
    search_locations = {item["location"].split("#")[0] for item in search["docs"]}
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    for machine in catalog:
        route = machine["path"].removesuffix(".md") + "/"
        if route + "index.html" not in pages:
            errors.append(f"Missing route: {route}")
        elif pages[route + "index.html"].h1_count != 1:
            errors.append(f"Unexpected article heading/code rendering: {route}")
        if route not in search_locations:
            errors.append(f"Missing search entry: {route}")
        if urljoin(canonical[1], route) not in sitemap:
            errors.append(f"Missing sitemap entry: {route}")
    for name, page in pages.items():
        source = (site / name).read_text(encoding="utf-8")
        if re.search(r"taylorelder\.com|linkedin\.com/in/taylor-elder|github\.com/aelder202", source, re.I):
            errors.append(f"Professional identity link in {name}")
        if re.search(r"!\[\[|\{\{ (?:machine_|difficulty_|preview_|investigation_)", source):
            errors.append(f"Unresolved source markup in {name}")
        for link in page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                if parsed.netloc != base.netloc:
                    continue
            if parsed.path.startswith("/"):
                if not parsed.path.startswith(prefix):
                    # Existing links to the PerhapsLater runbook are intentional.
                    if parsed.path.startswith("/red-team-runbook/"):
                        continue
                    errors.append(f"Unexpected site-root link: {name}: {link}")
                    continue
                target = unquote(parsed.path[len(prefix):])
            else:
                target = urlsplit(urljoin("https://local/" + name, parsed.path)).path.lstrip("/")
                target = unquote(target)
            if not target or target.endswith("/"):
                target += "index.html"
            candidate = site / target
            if candidate.is_dir():
                candidate = candidate / "index.html"
                target = candidate.relative_to(site).as_posix()
            if not candidate.is_file():
                errors.append(f"Broken link/image: {name}: {link}")
                continue
            if parsed.fragment and target in pages and unquote(parsed.fragment) not in pages[target].ids:
                errors.append(f"Missing anchor: {name}: {link}")
    # Incomplete or uncertain machines must have neither routes nor search text.
    for slug in ("connected", "servmon", "devel", "certified", "streamio", "silentium", "support"):
        if any(path.split("/")[-2:-1] == [slug] for path in pages):
            errors.append(f"Excluded route exists: {slug}")
        if re.search(rf'"(?:linux|windows|active-directory)/{slug}/', json.dumps(search)):
            errors.append(f"Excluded search entry exists: {slug}")
    print(f"Checked {len(catalog)} machines, {len(pages)} HTML pages, search, sitemap, images and internal links.")
    return sorted(set(errors))


if __name__ == "__main__":
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "site"
    issues = validate(output)
    if issues:
        print("\n".join(issues))
        sys.exit(1)
    print("Site validation passed.")
