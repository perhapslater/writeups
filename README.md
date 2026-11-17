# HTB Writeups

Retired HackTheBox machine investigations by PerhapsLater, following the evidence
from enumeration through foothold and privilege escalation.

[Read the writeups](https://perhapslater.github.io/writeups/)

## Contents

- Active Directory, Windows, and Linux investigations.
- Attack paths, command examples, evidence screenshots, and the reasoning behind each step.
- A machine library with platform, difficulty, and technique filters.

Only retired machines are documented. Use these techniques in authorized labs and assessments.

## Local development

Install the locked dependencies and build the production site:

```sh
python -m pip install --require-hashes -r requirements.lock
python -m unittest discover -s tests
python -m mkdocs build --strict
python tools/validate_site.py
```

Run `python -m mkdocs serve` to review the site locally. `SITE_URL` can override
the default GitHub Pages URL for a custom deployment.

## Adding an investigation

Machine pages live under `docs/linux`, `docs/windows`, or `docs/active-directory`.
The reviewed catalog in `data/machines.yml` supplies navigation, machine cards,
counts, and difficulty options. Keep its descriptions specific to each attack
path. Omit difficulty when it cannot be verified; the library labels it
"Unspecified" rather than guessing.

Every catalog entry requires an official HTB retirement evidence URL and a check
date. Follow [HTB's publication guidelines](https://help.hackthebox.com/en/articles/5188925-streaming-writeups-walkthrough-guidelines):
seasonally expired content is not necessarily retired. The build rejects
uncatalogued machine pages, duplicate routes, and entries without a recorded
retirement check. This is a review guard, not a live HTB status lookup.

Keep flag values out of text and images. Store only the screenshots referenced
by the article, under a machine-specific asset directory. Do not place private
notes, incomplete exports, or active-machine solutions in this repository.

## Attribution

Research and tool references accompany the relevant writeups. Third-party
attributions are retained in [NOTICE](NOTICE) and the [Material for MkDocs license](THIRD_PARTY_LICENSES/mkdocs-material.txt).
