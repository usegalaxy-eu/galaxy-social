# GitHub Copilot Code Review Instructions

This file provides project-specific context for GitHub Copilot code review.

---

## Project Overview

Galaxy Social cross-posts announcements to Mastodon, Bluesky, LinkedIn, Matrix, and Slack via GitHub Actions. Contributors add markdown files under `posts/` with YAML frontmatter targeting platforms. PRs generate previews as comments; merging publishes to all targeted platforms.

---

## Creating a New Post

### File Naming

Posts must be placed in `posts/YYYY/YYYY-MM-DD-slug.md` (e.g. `posts/2026/2026-03-20-my-announcement.md`). Flag files not matching this pattern or placed outside the correct year subdirectory.

### Frontmatter Structure

Every post requires YAML frontmatter between `---` delimiters:

```yaml
---
media:
  - mastodon-galaxyproject
  - bluesky-galaxyproject
  - linkedin-galaxyproject

mentions:
  mastodon-galaxyproject:
    - galaxyfreiburg@bawü.social
  bluesky-galaxyproject:
    - galaxyproject.bsky.social
  linkedin-galaxyproject:
    - galaxy-project

hashtags:
  mastodon-galaxyproject:
    - UseGalaxy
    - GalaxyProject
  bluesky-galaxyproject:
    - UseGalaxy
---

Post body in markdown here.
```

### Valid Plugin Names

Only these enabled plugins are valid in the `media` field:

| Name | Platform |
|------|----------|
| `mastodon-galaxyproject` | Mastodon (mstdn.science) |
| `mastodon-eu-freiburg` | Mastodon (bawü.social) |
| `mastodon-brc` | Mastodon (mstdn.science) |
| `mastodon-vgp` | Mastodon (mastodon.social) |
| `bluesky-galaxyproject` | Bluesky |
| `bluesky-brc` | Bluesky |
| `bluesky-vgp` | Bluesky |
| `linkedin-galaxyproject` | LinkedIn |
| `linkedin-brc` | LinkedIn |
| `matrix-eu-announce` | Matrix |
| `markdown` | Local markdown cache |

`slack` exists in `plugins.yml` but is **disabled** — flag if used.

### Frontmatter Validation Rules

- **`media`** (required): array of unique strings; each must match an enabled plugin name above
- **`mentions`** (optional): object where keys are plugin names, values are arrays of strings
  - Keys must be a subset of the `media` list
  - Must NOT include `@` prefix — the system adds it
  - Format varies by platform:
    - Mastodon: `username@server` (e.g. `galaxyproject@mstdn.science`)
    - Bluesky: `username.server` (e.g. `galaxyproject.bsky.social`)
    - LinkedIn: organization vanity name (e.g. `galaxy-project`)
    - Matrix: `username:server` (e.g. `bgruening:matrix.org`)
- **`hashtags`** (optional): object where keys are plugin names, values are arrays of strings
  - Keys must be a subset of the `media` list
  - Must NOT include `#` prefix — the system adds it
  - Only alphanumeric and underscore characters allowed (no hyphens or spaces)
- **`images`** (optional): array of `{url, alt_text}` objects; `url` must be a valid URI; supported MIME types: jpeg, png, gif

### Content Rules

- Body text goes after the closing `---`
- Markdown formatting (bold, italic, headings, lists) only renders on Matrix. Mastodon, Bluesky, and LinkedIn strip formatting to plain text — only links and images are preserved
- Images use markdown syntax: `![Alt text](https://example.com/image.jpg)`
- GitHub emoji shortcodes like `:tada:` are converted to Unicode
- Two consecutive blank lines force a thread split on platforms that support threading
- Image URLs must be publicly accessible and return a supported MIME type

### Platform Character Limits

| Platform | Limit | URL counting | Max images |
|----------|-------|-------------|------------|
| Mastodon | 500 chars | All URLs = 23 chars | 4 |
| Bluesky | 300 chars | Actual URL length | 4 |
| LinkedIn | 3000 chars | Actual URL length | 20 |
| Matrix | Unlimited | — | Unlimited |

Content exceeding limits is auto-split into threaded chunks with `(1/N)` pagination. Flag posts that are excessively long without clear thread break points.

### Common Mistakes to Flag

1. `media` field is missing or empty
2. Plugin names misspelled (e.g. `mastodon-galaxy-project` instead of `mastodon-galaxyproject`)
3. Using disabled plugins (e.g. `slack`)
4. Mentions/hashtag keys referencing plugins not in the `media` list
5. Mentions with `@` prefix or hashtags with `#` prefix
6. Invalid mention format for the target platform
7. Hashtags with hyphens, spaces, or special characters
8. Image URLs that are not valid URIs
9. Post file not in `posts/YYYY/` directory or wrong naming pattern
10. Editing existing published posts instead of creating new files

---

## Plugin System

Plugins live in `lib/plugins/` and follow duck-typing — no abstract base class. Every plugin implements:

- `format_content(content, mentions, hashtags, images, **kwargs)` → `(formatted_content, preview_str, warnings_str)`
- `create_post(formatted_content, **kwargs)` → `(success: bool, url_or_none)`

Use `strip_markdown_formatting()` from `lib/plugins/base.py` for plain-text conversion (shared by Mastodon, Bluesky, LinkedIn plugins).

---

## plugins.yml and Secrets

- Secrets use `$ENV_VAR_NAME` syntax, resolved at runtime from environment variables
- Every `$SECRET` in `plugins.yml` must be declared in `.github/workflows/galaxy_social.yml` env block
- Every secret in the workflow env block must be used by at least one plugin
- `validate_social_plugin.yml` workflow enforces this and posts errors on PRs

---

## Workflow Security

- `galaxy_social.yml` uses `pull_request_target` — review changes for safe use (avoid running untrusted fork code)
- Required permissions: `contents: write`, `pull-requests: write`, `actions: write`
- Secrets must never be logged or exposed in PR comments
