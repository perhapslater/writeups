"""Publish small site-level files using MkDocs' validated site URL."""
from pathlib import Path


def on_post_build(config):
    root = Path(config.site_dir)
    sitemap = config.site_url.rstrip("/") + "/sitemap.xml"
    (root / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + sitemap + "\n", encoding="utf-8")
    (root / ".nojekyll").touch()
