---
name: llms-txt
description: >
  Write and maintain llms.txt at the site root: a title, a short summary and
  sections of links with one line per page, built from the site's own pages and
  kept in step with the sitemap. Use when the owners of a site want a plain
  index for agents and language models that read it, or when pages were added or
  removed since the file was last written. Activates on "/llms-txt", "write
  llms.txt", "update llms.txt", "is llms.txt in sync", "llms.txt out of date".
user-invocable: true
---

# llms.txt

Writes `llms.txt`, a Markdown index at the site root with one line per page, and checks it against `sitemap.xml`. An agent that reads the site finds there a short list of what each page holds.

Check before use: whether the engines you target document reading `llms.txt`, and the current form of the proposal at `<URL of the llms.txt proposal>`. Treat the file as an index for agents. Promise no ranking or citation effect from it.

## Inputs

- The folder the site is served from (`<site root>`, for example `public/` or the repository root).
- `sitemap.xml` in that folder. Without one, the built HTML pages.
- Optional: `aieo/llms-exempt.txt`, one URL per line, for pages the index leaves out (legal pages, error pages, tag lists).

## Steps

1. **List the pages.** Read the `<loc>` entries of `sitemap.xml`. Without a sitemap, list the built `*.html` files and say so in the report. For each page read its `<title>`, its meta description and its first paragraph.
2. **Copy the template** if the site has no `llms.txt`:

   ```bash
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/llms.txt" "<site root>/llms.txt"
   ```

3. **Write the head.** `# <site or organisation name>`, then a `>` summary of one or two sentences: who runs the site, what it covers, the main finding or offer. An optional paragraph defines the terms a reader needs, in the words the pages use.
4. **Write the sections.** Group the pages as the site navigation groups them, one `##` heading per group. One line per page: `- [<page title>](<canonical URL>): <one line on what the page holds>`. Lead with the page's finding or content. Use the canonical URL of each page, the same URL as in the sitemap.
5. **Check the sync.** Run from the repository root:

   ```bash
   python3 - "<site root>" <<'EOF'
   import re, sys
   from pathlib import Path
   site = Path(sys.argv[1])
   locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", (site / "sitemap.xml").read_text())
   links = re.findall(r"\]\((https?://[^)\s]+)\)", (site / "llms.txt").read_text())
   ex = Path("aieo/llms-exempt.txt")
   exempt = {l.strip().rstrip("/") for l in ex.read_text().splitlines() if l.strip() and not l.startswith("#")} if ex.exists() else set()
   host = lambda u: re.sub(r"^https?://([^/]+).*$", r"\1", u)
   hosts = {host(u) for u in locs}
   L, S = {u.rstrip("/") for u in links}, {u.rstrip("/") for u in locs}
   missing = sorted(u for u in locs if u.rstrip("/") not in L | exempt)
   extra = sorted(u for u in links if host(u) in hosts and u.rstrip("/") not in S)
   print(f"sitemap: {len(locs)} URLs, llms.txt: {len(links)} links, exempt: {len(exempt)}")
   for u in missing: print("missing from llms.txt:", u)
   for u in extra: print("not in sitemap.xml:", u)
   sys.exit(1 if missing or extra else 0)
   EOF
   ```

   Exit 0 means every sitemap URL is listed or exempt, and every link to the site's own host is in the sitemap. Fix each line the script prints, then run it again.
6. **Keep it in step.** When the site has a build step, generate `llms.txt` there from the same page list as the sitemap, and run the sync check before each deploy. Without a build step, run this skill after each page is added or removed.

## Output

`llms.txt` at the site root, the sync report (missing and extra URLs), and the pages that had no description, so their owners can write one.

## Rules

- One line per page. Each line describes what a reader sees on that page.
- No text addressed to models that the pages do not show to readers. No keyword lists, no instructions to models.
- Name the entity, its products and its terms the same way on every line and on the pages.
- Update lines in an existing `llms.txt` and keep the rest. Remove a line only when its page is gone from the sitemap, and list the removed lines in the report.
- Never overwrite an existing file with the template. Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/aieo" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/aieo/` exists, read its `README.md` first, then the files in `aieo/llms-txt/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
