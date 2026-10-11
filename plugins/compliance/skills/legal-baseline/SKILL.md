---
name: legal-baseline
description: >
  Set up the legal baseline of a website: an Impressum under German law (§ 5
  DDG), a privacy page with the information of GDPR Art 13, a
  /.well-known/security.txt with Contact and Expires (RFC 9116), and no
  third-party requests on page load (fonts, scripts and styles self-hosted, no
  analytics without consent). Adds gate checks for security.txt and third-party
  loads. Use when a team launches or audits a public website, or a page loads
  fonts, scripts or embeds from other hosts. Activates on "/legal-baseline",
  "Impressum", "imprint", "privacy page", "security.txt", "third-party
  requests", "self-host fonts", "GDPR website check", "cookie banner".
user-invocable: true
---

# Legal baseline

Four parts for every public website the team runs:

| Part | File in the site | Basis |
|---|---|---|
| Provider identification | `legal/impressum.md`, linked from every page | § 5 DDG (Germany) |
| Privacy information | `legal/privacy.md`, linked from every page | GDPR Art 13 |
| Security contact | `/.well-known/security.txt` | RFC 9116 |
| No third-party requests on page load | every HTML page | GDPR Art 5(1)(c), Art 6(1) |

The skill writes skeletons and checks. The content of the Impressum and the privacy page needs review by legal counsel before the site goes live.

## Inputs

- The site: its source folder, how it is built and the folder the build writes (the site root that the host serves).
- The provider: a person or a company, with address, contact, register entry and VAT ID where they exist.
- What the site processes: server logs at the host, forms, email, cookies or local storage, embedded content, analytics.
- The security contact: an email address or an https form that the team reads, and who renews `Expires`.

## Steps

1. **Find the site root.** Read the build config and the deploy workflow. Note the source folder (where Markdown or templates live) and the output folder (the HTML that is served). Run the checks on the output folder; build it first if it is not in the repository.
2. **Copy the skeletons without overwriting.**

   ```bash
   mkdir -p legal
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/legal/impressum.md" "${CLAUDE_PLUGIN_ROOT}/templates/legal/privacy.md" legal/
   mkdir -p <static-folder>/.well-known
   cp -n "${CLAUDE_PLUGIN_ROOT}/templates/.well-known/security.txt" <static-folder>/.well-known/
   ```

   `<static-folder>` is the folder whose files the build copies to the site root unchanged (often `static/` or `public/`). Move the two legal pages into the folder the site builds pages from, if it is not `legal/`.
3. **Impressum.** Fill each section from the inputs and delete the sections that do not apply. Link the page from the footer of every page. Check before use: confirm the required fields against the current text of § 5 DDG (and § 18 MStV for journalistic content) with legal counsel. For a provider outside Germany, ask the user which national rule applies and adapt the page with counsel.
4. **Privacy page.** Fill one section per processing activity the site really performs, with the data, purpose, legal basis under Art 6(1) and retention. Name the hosting provider and every other processor with the processing agreement under Art 28. Delete sections for processing that does not happen. Link the page from the footer of every page. Read GDPR Art 13 on EUR-Lex (<https://eur-lex.europa.eu/eli/reg/2016/679/oj>) to check that each point is answered; do not paste article text into the page.
5. **security.txt.** Fill `Contact` with a `mailto:`, `https:` or `tel:` URI, `Expires` with a date-time with time zone less than one year ahead, and `Canonical` with the final URL. Compute the date with `python3 -c 'import datetime as d; print((d.datetime.now(d.timezone.utc) + d.timedelta(days=330)).strftime("%Y-%m-%dT00:00:00Z"))'`. Ask the user to put the renewal date in the team calendar; the gate check fails once `Expires` has passed. Check before use: some static site builders skip folders whose name starts with a dot; check that the deployed site serves the file.
6. **Find third-party requests.** With the gate installed, copy the rule (step 8) and run it on the built site:

   ```bash
   python3 .github/actions/gate/run.py --only compliance.no-third-party --dry-run
   ```

   Without the gate, search the built HTML: `grep -rnoiE '(src|href|srcset|poster)="(https?:)?//[^"]+' <site-root> | grep -v '<your-domain>'`, and read the `@import` and `url(` lines in the CSS. Links in `<a href>` are fine; every resource the browser loads on page load counts.
7. **Remove them.**
   - Fonts: download the font files once, check that the licence allows self-hosting, serve them from the site and declare them with `@font-face` in the site's own CSS. Ask before downloading any file, with its name, source and size.
   - Scripts and styles: copy the pinned version into the repository and serve it from the site.
   - Images and icons: serve them from the site.
   - Video, maps and other embeds: show a static preview with a link, or load the embed only after a click with a short notice of what the click loads.
   - Analytics: no analytics on page load without consent. Without consent management, use counts from the host's own server logs.
   Rebuild and run the check again until it passes. List each host that remains in `allowed_hosts` only when it is the team's own (for example a separate asset domain).
8. **Gate.** Tell the user how to add `compliance.security-txt` and `compliance.no-third-party` with `/gate:add-rule` (see the module README), with `roots` set to the built site folder and `allowed_hosts` to the team's own asset hosts. Do it only when the user says so.
9. **Verify after deploy.**

   ```bash
   curl -fsSI https://<your-domain>/.well-known/security.txt   # 200, Content-Type text/plain
   curl -fsS https://<your-domain>/ | grep -ciE '(src|href)="(https?:)?//'   # count of absolute URLs to inspect
   ```

   Open the site in a private browser window with the network panel open and check that every request goes to the team's own hosts.
10. **Report.**

## Output

- `legal/impressum.md`, `legal/privacy.md` and `<static-folder>/.well-known/security.txt`, filled or with the open placeholders listed.
- A list of third-party requests found, what replaced each one, and the hosts left in `allowed_hosts` with the reason.
- The questions for legal counsel.

## Rules

- This skill prepares the pages and the checks. Legal counsel reviews the Impressum and the privacy page before the site goes live.
- Never overwrite or delete an existing legal page or security.txt. Show changes to an existing page and ask before writing.
- Do not paste the text of a law into a page. Cite the section or article and link the official source.
- Ask before downloading fonts or scripts. Never add a consent banner, analytics tool or embed without the user's decision.
- Do not commit or push. The user does.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/compliance" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/compliance/` exists, read its `README.md` first, then the files in `compliance/legal-baseline/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
