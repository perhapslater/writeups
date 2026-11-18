import importlib.util
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import yaml
from mkdocs.exceptions import ConfigurationError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("publication", ROOT / "hooks/publication.py")
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "docs/linux").mkdir(parents=True)
        (self.root / "docs/linux/example.md").write_text("# Example\n")
        self.machine = {
            "name": "Example", "path": "linux/example.md", "platform": "Linux",
            "description": "A specific investigation.", "techniques": "File read",
            "eligibility": {"state": "retired", "checked": "2026-11-17",
                            "evidence": "https://labs.hackthebox.com/achievement/machine/1/2"},
        }

    def write_catalog(self, machines=None):
        (self.root / "data/machines.yml").write_text(yaml.safe_dump(machines or [self.machine]))

    def test_retired_entry_is_accepted_without_inventing_difficulty(self):
        self.write_catalog()
        catalog = publication.load_catalog(self.root)
        card = publication.machine_cards(catalog)
        self.assertIn('data-difficulty="Unspecified"', card)
        self.assertIn('href="linux/example/"', card)

    def test_active_expired_and_unknown_statuses_are_rejected(self):
        for state in ("active", "expired", "unknown", None):
            with self.subTest(state=state):
                self.machine["eligibility"]["state"] = state
                self.write_catalog()
                with self.assertRaises(ConfigurationError):
                    publication.load_catalog(self.root)

    def test_third_party_status_evidence_is_rejected(self):
        self.machine["eligibility"]["evidence"] = "https://writeup.example/machines/example"
        self.write_catalog()
        with self.assertRaises(ConfigurationError):
            publication.load_catalog(self.root)

    def test_missing_verification_date_is_rejected(self):
        del self.machine["eligibility"]["checked"]
        self.write_catalog()
        with self.assertRaises(ConfigurationError):
            publication.load_catalog(self.root)

    def test_duplicate_route_is_rejected(self):
        self.write_catalog([self.machine, {**self.machine, "name": "Another"}])
        with self.assertRaises(ConfigurationError):
            publication.load_catalog(self.root)

    def test_uncatalogued_machine_cannot_enter_the_build(self):
        self.write_catalog()
        (self.root / "docs/linux/unreviewed.md").write_text("# Unreviewed\n")
        with self.assertRaises(ConfigurationError):
            publication.load_catalog(self.root)

    def test_card_text_is_escaped(self):
        self.machine["description"] = '<script>alert("x")</script>'
        card = publication.machine_cards([self.machine])
        self.assertNotIn("<script>", card)
        self.assertIn("&lt;script&gt;", card)

    def test_repository_nav_and_library_share_the_reviewed_collection(self):
        config = SimpleNamespace(config_file_path=str(ROOT / "mkdocs.yml"))
        publication.on_config(config)
        count = sum(len(group[next(iter(group))]) for group in config.nav[1:])
        self.assertEqual(count, len(publication.load_catalog(ROOT)))
        page = SimpleNamespace(file=SimpleNamespace(src_uri="index.md"))
        rendered = publication.on_page_markdown(
            "{{ machine_count }}|{{ machine_cards }}|{{ difficulty_options }}", page, config, None)
        self.assertTrue(rendered.startswith(str(count) + "|"))
        self.assertEqual(rendered.count('class="machine-card"'), count)
        self.assertNotIn("{{", rendered)

    def test_preview_labels_and_controls_use_the_same_collection(self):
        catalog = publication.load_catalog(ROOT)
        slides, buttons = publication.investigation_previews(catalog)
        selected = sorted((machine for machine in catalog if machine.get("preview")),
                          key=lambda machine: machine["preview"]["order"])
        self.assertEqual(slides.count('data-case-preview '), len(selected))
        self.assertEqual(buttons.count('data-preview-go='), len(selected))
        self.assertEqual(buttons.count('aria-current="true"'), 1)
        for index, machine in enumerate(selected):
            preview = machine["preview"]
            name = escape(machine["name"])
            route = machine["path"].removesuffix(".md") + "/"
            self.assertIn(f'aria-label="{name}, {index + 1} of {len(selected)}"', slides)
            self.assertIn(f'href="{escape(route)}#{escape(preview["anchor"])}"', slides)
            self.assertIn(f'<mark>{escape(preview["highlight"])}</mark>', slides)
            current = ' aria-current="true"' if index == 0 else ""
            self.assertIn(f'data-preview-go="{index}"{current}>{name}</button>', buttons)


if __name__ == "__main__":
    unittest.main()
