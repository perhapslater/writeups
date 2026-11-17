"""Build navigation and the existing machine library from a reviewed catalog."""
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import yaml
from mkdocs.exceptions import ConfigurationError


PLATFORMS = ("Active Directory", "Windows", "Linux")
SYMBOLS = {
    "Active Directory": '<rect x="8" y="3" width="8" height="6" rx="1"/><path d="M12 9v5M5 14h14M5 14v3m14-3v3"/><rect x="2" y="17" width="6" height="4" rx="1"/><rect x="16" y="17" width="6" height="4" rx="1"/>',
    "Windows": '<path d="m3 5 8-1v7H3V5Zm10-1 8-1v8h-8V4ZM3 13h8v7l-8-1v-6Zm10 0h8v8l-8-1v-7Z"/>',
    "Linux": '<path d="m8 8-5 4 5 4m8-8 5 4-5 4M14 4l-4 16"/>',
}
_machines = []


def load_catalog(root):
    """Fail closed: only explicitly reviewed, retired content enters the site."""
    machines = yaml.safe_load((root / "data/machines.yml").read_text(encoding="utf-8"))
    if not isinstance(machines, list) or not machines:
        raise ConfigurationError("The machine catalog must be a non-empty list")
    names, paths = set(), set()
    for machine in machines:
        for field in ("name", "path", "platform", "description", "techniques", "eligibility"):
            if not machine.get(field):
                raise ConfigurationError(f"Machine is missing {field}")
        name, path, platform = machine["name"], machine["path"], machine["platform"]
        if name.casefold() in names or path.casefold() in paths:
            raise ConfigurationError(f"Duplicate machine name or route: {name}")
        names.add(name.casefold())
        paths.add(path.casefold())
        directory = "active-directory" if platform == "Active Directory" else platform.lower()
        if platform not in PLATFORMS or Path(path).parent.as_posix() != directory or not path.endswith(".md"):
            raise ConfigurationError(f"Invalid platform or article path: {name}")
        if not (root / "docs" / path).is_file():
            raise ConfigurationError(f"Missing article: {path}")
        if machine.get("difficulty") not in (None, "Easy", "Medium", "Hard", "Insane"):
            raise ConfigurationError(f"Unrecognized difficulty: {name}")
        eligibility = machine["eligibility"]
        evidence = urlparse(eligibility.get("evidence", ""))
        checked = str(eligibility.get("checked", ""))
        try:
            date.fromisoformat(checked)
        except ValueError as error:
            raise ConfigurationError(f"Missing retirement verification date: {name}") from error
        if (eligibility.get("state") != "retired" or evidence.scheme != "https"
                or evidence.hostname not in ("labs.hackthebox.com", "app.hackthebox.com", "www.hackthebox.com")
                or not evidence.path.startswith(("/achievement/machine/", "/machines/"))):
            raise ConfigurationError(f"Official retirement evidence is required: {name}")
    # Never let an uncatalogued Markdown solution get copied into the public site.
    articles = {p.relative_to(root / "docs").as_posix()
                for platform in ("active-directory", "windows", "linux")
                for p in (root / "docs" / platform).rglob("*.md")}
    if articles != {machine["path"] for machine in machines}:
        raise ConfigurationError("Every machine article must appear in the reviewed catalog")
    return machines


def on_config(config):
    global _machines
    root = Path(config.config_file_path).resolve().parent
    _machines = load_catalog(root)
    config.nav = [{"Home": "index.md"}] + [
        {platform: [{machine["name"]: machine["path"]} for machine in _machines
                    if machine["platform"] == platform]}
        for platform in PLATFORMS
    ]
    return config


def machine_cards(machines):
    cards = []
    for machine in machines:
        name, platform = escape(machine["name"]), escape(machine["platform"])
        difficulty = escape(machine.get("difficulty") or "Unspecified")
        label = "Windows / Active Directory" if platform == "Active Directory" else platform
        url = escape(machine["path"].removesuffix(".md") + "/")
        cards.append(
            f'<a class="machine-card" data-platform="{platform}" data-difficulty="{difficulty}" href="{url}" '
            f'aria-label="Read {name}, {difficulty}, {platform}">'
            '<div class="machine-card-top"><span class="machine-symbol"><svg viewBox="0 0 24 24" aria-hidden="true">'
            f'{SYMBOLS[machine["platform"]]}</svg></span>'
            f'<span class="difficulty {difficulty.lower()}">{difficulty}</span></div>'
            f'<h3>{name}</h3><span class="platform-label">{label}</span>'
            f'<p class="machine-description">{escape(machine["description"])}</p>'
            f'<div class="machine-card-bottom"><span class="techniques">{escape(machine["techniques"])}</span>'
            '<span class="read-link">Read writeup</span></div></a>'
        )
    return "".join(cards)


def investigation_previews(machines):
    selected = sorted((machine for machine in machines if machine.get("preview")),
                      key=lambda machine: machine["preview"]["order"])
    slides, buttons = [], []
    for index, machine in enumerate(selected):
        name = escape(machine["name"])
        platform = "Windows / Active Directory" if machine["platform"] == "Active Directory" else machine["platform"]
        level = escape(machine.get("difficulty") or "Unspecified")
        url = escape(machine["path"].removesuffix(".md") + "/")
        hidden = " hidden" if index else ""
        stages = "".join(
            '<li><span class="case-preview-node" aria-hidden="true"></span>'
            f'<span class="case-preview-stage">{escape(stage["label"])}</span><strong>{escape(stage["value"])}</strong></li>'
            for stage in machine["preview"]["stages"]
        )
        slides.append(
            f'<article class="case-preview" data-case-preview data-case-name="{name}" role="group" '
            f'aria-roledescription="slide" aria-label="{name}, {index + 1} of {len(selected)}"{hidden}>'
            f'<div class="case-preview-meta"><span>{escape(platform)}</span>'
            f'<span class="case-preview-difficulty case-preview-difficulty-{level.lower()}">{level}</span></div>'
            f'<h3><a href="{url}">{name}</a></h3>'
            f'<p class="case-preview-summary">{escape(machine["preview"]["summary"])}</p>'
            f'<ol class="case-preview-path" aria-label="{name} attack path">{stages}</ol>'
            f'<a class="button primary case-preview-read" href="{url}">Read {name}</a></article>'
        )
        current = ' aria-current="true"' if index == 0 else ""
        buttons.append(f'<button type="button" data-preview-go="{index}" aria-label="Show {name}"{current}><span></span></button>')
    status = f'{escape(selected[0]["name"])}, 1 of {len(selected)}' if selected else ""
    return "".join(slides), "".join(buttons), status


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri != "index.md":
        return markdown
    difficulties = [level for level in ("Easy", "Medium", "Hard", "Insane", "Unspecified")
                    if any((machine.get("difficulty") or "Unspecified") == level for machine in _machines)]
    slides, buttons, status = investigation_previews(_machines)
    return (markdown.replace("{{ machine_count }}", str(len(_machines)))
            .replace("{{ machine_cards }}", machine_cards(_machines))
            .replace("{{ difficulty_options }}", "".join(f"<option>{level}</option>" for level in difficulties))
            .replace("{{ investigation_previews }}", slides)
            .replace("{{ preview_buttons }}", buttons)
            .replace("{{ first_preview_status }}", status))


def on_post_build(config):
    root = Path(config.site_dir)
    sitemap = config.site_url.rstrip("/") + "/sitemap.xml"
    (root / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + sitemap + "\n", encoding="utf-8")
    (root / ".nojekyll").touch()
