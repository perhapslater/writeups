# Publish with GitHub Pages

This project is prepared for a public repository owned by `perhapslater`. Its
workflow builds MkDocs and deploys a Pages artifact; it does not need a `gh-pages`
branch, a force push, a Figma subscription, or a separate hosting service.

## 1. Create and push the project repositories

Sign in to GitHub as **perhapslater**. Git commit identity and GitHub authentication
are separate: verify the active browser or CLI account before publishing.

Create two **empty public repositories**:

- `perhapslater/red-team-runbook`
- `perhapslater/writeups`

Do not initialize them with a README, license, or `.gitignore`; those files are
already prepared locally. If either repository already exists, inspect it first
and reconcile its contents before pushing. Do not overwrite it or force-push.

In each prepared local repository, review the source and run:

```sh
git status
git log -1 --format=fuller
git remote -v
```

The author and committer should both be `PerhapsLater` with the configured GitHub
noreply address. The `origin` should name the matching `perhapslater` repository.
When you approve publication, push from each directory:

```sh
git push -u origin main
```

No secret deployment token is required. The workflow uses GitHub's scoped token
and OpenID Connect for deployment. For future editing, keep the repository-local
Git identity; do not substitute a global identity by accident.

## 2. Enable each project site

In **each** repository:

1. Open **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. Leave the project's **Custom domain empty**. Do not add a project `CNAME` file.
4. Open **Actions → Publish documentation → Run workflow**, choosing `main`.
5. Check both the `build` and `deploy` jobs. Follow the deployment URL from the run.

If the first push ran before Pages was enabled, rerun it after step 2. The workflow
deliberately does not enable Pages or change repository settings automatically.
Organization policy or environment protections may require an administrator to
allow Actions or approve the `github-pages` environment.

Before the custom domain is active, the fallback URLs are:

- <https://perhapslater.github.io/red-team-runbook/>
- <https://perhapslater.github.io/writeups/>

The workflow reads the configured Pages URL before building, so canonical URLs,
Open Graph images, sitemap entries, and robots.txt use the actual deployment
domain. Pull requests run checks without deploying. See GitHub's
[custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## 3. Create the account site for the shared domain

To serve both projects beneath `perhapslater.com`, create the public account-site
repository **`perhapslater/perhapslater.github.io`** if it does not already exist.
This is a separate, small site, not another copy of either documentation project.

For a simple root landing page, add this `index.html` to its `main` branch:

```html
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PerhapsLater</title>
<h1>PerhapsLater</h1>
<p>Security publications and retired-machine investigations.</p>
<ul>
  <li><a href="/red-team-runbook/">Red Team Runbook</a></li>
  <li><a href="/writeups/">HTB Writeups</a></li>
</ul>
</html>
```

For that account repository only, set **Settings → Pages → Deploy from a branch →
main → /(root)**. The account site can use its own design later.

Verify ownership of `perhapslater.com` through your GitHub account's **Settings →
Pages** using the exact TXT record GitHub supplies. In the **account repository's**
Pages settings, set **Custom domain → perhapslater.com** and save **before** changing
DNS. With branch publishing GitHub creates a root `CNAME` file containing that
domain; retain it in the account repository only.

GitHub's account-level custom domain is inherited by project sites that do not
set their own domain. The resulting URLs are:

- <https://perhapslater.com/red-team-runbook/>
- <https://perhapslater.com/writeups/>

See [custom-domain inheritance](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages).

## 4. Change DNS manually

At the DNS provider for `perhapslater.com`, replace conflicting **parked web**
records for the apex and `www`. Preserve unrelated mail, verification, and other
service records. Create the apex records below; providers commonly call the host
field `@` or leave it blank.

| Type | Host | Value |
| --- | --- | --- |
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | perhapslater.github.io |

Optional IPv6 support uses four apex AAAA records:

```text
2606:50c0:8000::153
2606:50c0:8001::153
2606:50c0:8002::153
2606:50c0:8003::153
```

The `www` CNAME contains only the hostname, with no `https://` or project path.
Do not add wildcard DNS records. Follow GitHub's current
[domain and DNS instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
if your provider uses ALIAS/ANAME records instead. DNS propagation can take up to
24 hours.

When GitHub reports a successful DNS check and the certificate is available,
enable **Enforce HTTPS** on the account site and check HTTPS on both project sites.
Then rerun **Publish documentation** in both project repositories so their canonical
and sitemap URLs reflect the inherited custom domain.

## 5. Check the published result

- Open both project homepages and a deeply nested article on the final domain.
- Use global search and open a result. Check images, code-copy buttons, navigation,
  the publication switch, and mobile navigation.
- In the runbook, change a target and verify command substitution and reset.
- In the writeups, filter machines and expand an evidence screenshot.
- Inspect page source: canonical and `og:url` must start with the correct final
  project URL. Open each project's `sitemap.xml` and `robots.txt`.
- Confirm the account root page, `www` redirect, and HTTPS work. No mixed-content
  or missing-asset errors should appear.

Keep both projects' Custom domain fields empty. A custom domain belongs to the
account site, not to both project repositories.

## Local checks and maintenance

Python 3.12 is used by deployment. Create a virtual environment, activate it, and
run these commands from either project:

```sh
python -m pip install --require-hashes -r requirements.lock
python scripts/content_audit.py
python -m mkdocs build --strict
python scripts/publication_audit.py
python -m mkdocs serve
```

Open the local URL printed by MkDocs. The header's links between publications use
their final root subpaths; a single-project dev server does not serve the other
project. Native article and asset links remain relative to the current project.
Local builds default to the intended custom-domain canonical URL; set `SITE_URL`
to a full alternate URL ending in `/` when verifying another deployment base.

Keep dependency versions and SHA-256 hashes in `requirements.lock` synchronized.
Upgrade in a separate change and repeat the strict build and browser checks.
Actions are pinned to reviewed full commit SHAs; review updates rather than
replacing pins with floating tags. No generated `site/` output is committed.

The public project sites are within GitHub Pages' free public-repository model;
there is no per-document charge. GitHub still imposes site-size and usage limits,
and Actions storage has its own allowances. See
[Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
and [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

MkDocs Material has announced end of maintenance on May 5, 2027. The current
publication retains its working MkDocs features; plan and test a future migration
separately. See the [maintainer's announcement](https://squidfunk.github.io/mkdocs-material/).
