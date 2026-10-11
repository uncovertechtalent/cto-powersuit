---
name: structured-data
description: >
  Add JSON-LD structured data to every page of a site, one graph per page type
  (Organization or Person, WebSite, Article, BreadcrumbList, and FAQPage only
  where the page shows real questions), generated from one source, parsed as
  JSON and checked against the visible page. Use when a site has no structured
  data, carries hand-written blocks that drift from the pages, or marks up text
  a reader cannot see. Activates on "/structured-data", "add JSON-LD",
  "schema.org markup", "structured data for AI search", "check our JSON-LD".
user-invocable: true
---

# Structured data

Writes one JSON-LD graph into each page from one source of truth for the entity and the page fields, then checks every block: it parses as JSON, carries the required fields of its type, and matches the text a reader sees.

Check before use: the structured data guidelines of each engine you target, at `<URL of the engine's structured data guidelines>`. Expect no citation effect from markup alone. The rule that markup must match the visible page holds in every case.

## Inputs

- The site source and its build step, if it has one.
- The entity: Organization or Person, its name as the pages write it, its URL, its logo or image, and the profiles it controls (`sameAs`).
- The built pages (`<site root>`), for the check.

## Steps

1. **List the page types** and map each one:

   | Page | Nodes in its graph |
   |---|---|
   | Every page | `Organization` or `Person` (one per site, with a fixed `@id` such as `<site URL>/#org`), `WebSite` (`@id` `<site URL>/#website`) |
   | Article, guide, post | `Article`, `TechArticle` or `BlogPosting` with `headline`, `description`, `datePublished`, `dateModified`, `author`, `publisher` |
   | List, section front, index | `CollectionPage` or `WebPage` |
   | Any page below the home page | `BreadcrumbList`, one `ListItem` per level, matching the visible breadcrumb |
   | Page that shows questions with their answers | `FAQPage` with one `Question` and `acceptedAnswer` per visible pair |

2. **Set up one source.** Entity fields live in one place: the site config or a data file such as `aieo/entity.json`. Page fields come from each page's own front matter, title and navigation entry. The build writes the graph into the `<head>` of every page as `<script type="application/ld+json">`. No block is typed by hand into a page.
3. **Copy the example** as a reference:

   ```bash
   mkdir -p aieo && cp -n "${CLAUDE_PLUGIN_ROOT}/templates/aieo/jsonld-example.json" aieo/
   ```

4. **Write the generator** in the language of the existing build. Reuse the `@id` of the entity and the website in every graph. Write dates in ISO 8601. Use the canonical URL of the page for `url` and `@id`.
5. **Check the built pages.** Run from the repository root:

   ```bash
   python3 - "<site root>" <<'EOF'
   import html, json, re, sys
   from pathlib import Path
   NEED = {"Organization": ["name", "url"], "Person": ["name"], "WebSite": ["name", "url"],
           "Article": ["headline", "datePublished"], "TechArticle": ["headline", "datePublished"],
           "BlogPosting": ["headline", "datePublished"], "BreadcrumbList": ["itemListElement"], "FAQPage": ["mainEntity"]}
   def nodes(d):
       if isinstance(d, list):
           for x in d: yield from nodes(x)
       elif isinstance(d, dict):
           yield from (nodes(d["@graph"]) if "@graph" in d else [d])
   def text(s):
       return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", s))).strip().lower()
   bad = 0
   for f in sorted(Path(sys.argv[1]).rglob("*.html")):
       src = f.read_text(errors="replace")
       body = re.search(r"(?is)<body\b.*?</body>", src)
       seen = text(re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", body.group(0) if body else src))
       blocks = re.findall(r"(?is)<script[^>]*application/ld\+json[^>]*>(.*?)</script>", src)
       if not blocks:
           print(f"{f}: no JSON-LD"); continue
       for b in blocks:
           try:
               data = json.loads(b)
           except json.JSONDecodeError as e:
               print(f"{f}: invalid JSON: {e}"); bad += 1; continue
           for n in nodes(data):
               types = n.get("@type") if isinstance(n.get("@type"), list) else [n.get("@type")]
               for t in types:
                   for k in NEED.get(t, []):
                       if k not in n: print(f"{f}: {t} without {k}"); bad += 1
               shown = [n.get("headline")] if "headline" in n else []
               if "FAQPage" in types:
                   for q in n.get("mainEntity", []):
                       shown += [q.get("name"), (q.get("acceptedAnswer") or {}).get("text")]
               for v in shown:
                   if isinstance(v, str) and text(v) not in seen:
                       print(f"{f}: not in the visible page: {v[:70]}"); bad += 1
   print(f"{bad} problems"); sys.exit(1 if bad else 0)
   EOF
   ```

   It prints pages with no JSON-LD (decide per page whether that is right), invalid JSON, missing fields, and headlines or FAQ text that the visible page does not show. Exit 0 means no problem.
6. **Check with the engines' own tools.** Check before use: `<URL of each engine's rich results or markup validator>`. Run two or three page types through it and record the result in the report.

## Output

The generator in the site build, one graph per page, the check output with exit code, and a list of page types with the nodes each one carries.

## Rules

- Mark up only what a reader sees on the page. Hidden text, invented questions and invented ratings are out.
- `FAQPage` only for questions and answers shown on the page, in the same words.
- One name per entity, the same in the markup, the page text and `llms.txt`. `sameAs` lists only profiles the entity controls.
- One source. Fix a wrong value in the source and rebuild. Never patch a built page.
- Never overwrite an existing file with a template. Never push.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/aieo" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/aieo/` exists, read its `README.md` first, then the files in `aieo/structured-data/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
