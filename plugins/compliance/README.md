# compliance

Compliance groundwork kept in the repository. A control map links the team's own controls and evidence to ISO/IEC 27001 Annex A, TISAX (VDA ISA), NIS2 and GDPR by number. An AI register triages every AI use under the EU AI Act and prepares the questions for legal review. A legal baseline gives a public website an Impressum, a privacy page, a security.txt and pages that load nothing from third parties. Two gate checks report an expired or incomplete security.txt and third-party loads in HTML.

The module holds no text of any standard. Standards are licensed: under the terms of the standards publishers (for example DIN Media AGB 5.4), processing their text with AI tools needs a separate licence. The templates and skills use clause, control and question numbers only, and the client fills the titles from their own licensed copy. EU legal acts are cited by article number with a link to EUR-Lex.

The skills prepare work for auditors and legal counsel. They do not replace either.

Install:

```bash
claude plugin install compliance@cto-powersuit
```

## Skills

| Skill | What it does |
|---|---|
| `/compliance:control-map` | Copies the control map, sets the frameworks in scope, lists the team's controls with owners and evidence, proposes the requirement numbers each control covers for the owners to confirm, and reports the gaps. |
| `/compliance:ai-act-triage` | Finds the AI uses in the repository and with the user, records the team's role, classifies each use as prohibited (Art 5), high-risk (Annex III or Annex I), transparency (Art 50) or minimal, adds provider obligations for general-purpose AI models, and writes the questions for legal review. |
| `/compliance:legal-baseline` | Copies and fills the Impressum, the privacy page and security.txt, finds every third-party request on page load, replaces each one with a self-hosted file or a click-to-load embed, and sets up the two gate checks. |

Every skill checks the overlay first: `$POWERSUIT_OVERLAY/compliance/` (see the root README). Use it for your frameworks in scope, your control ids and owners, your lawyer's contact and your site roots.

## Templates

The skills copy these files into the client repository on first use. An existing file is never overwritten.

| File in the plugin | Lands at | What it is |
|---|---|---|
| `templates/compliance/control-map.csv` | `compliance/control-map.csv` | Columns `framework, number, title, control_id, owner, evidence, status, gap`. One row per ISO/IEC 27001:2022 Annex A control number, the NIS2 points of Art 20, Art 21(2) and Art 23, a set of GDPR articles, and a placeholder row for VDA ISA. `title` stays empty for the client |
| `templates/compliance/ai-register.md` | `compliance/ai-register.md` | AI register with the docs front matter: AI uses, general-purpose AI models provided, the application dates and a change log |
| `templates/.well-known/security.txt` | `<site root>/.well-known/security.txt` | RFC 9116 fields with placeholders: Contact, Expires, Preferred-Languages, Canonical, optional Policy, Encryption, Acknowledgments |
| `templates/legal/impressum.md` | `legal/impressum.md` | Impressum skeleton under § 5 DDG with the docs front matter |
| `templates/legal/privacy.md` | `legal/privacy.md` | Privacy page skeleton with one section per point of GDPR Art 13 and the docs front matter |

Check before use: the dates in the AI register against the consolidated text of the AI Act on EUR-Lex, and the Impressum fields against § 5 DDG with legal counsel.

## Gate checks

Two rules for the deploy gate of the `gate` module.

### compliance.security-txt

`checks/security_txt.py`. For each site root in the option `roots` (default `["."]`) it reads `.well-known/security.txt` and reports:

| Snippet | Problem |
|---|---|
| `missing .well-known/security.txt` | The file does not exist in the site root |
| `missing Contact` | No `Contact` field |
| `Contact is not a mailto:, tel: or https: URI` | A `Contact` value with another form, or with a placeholder in angle brackets |
| `missing Expires` | No `Expires` field |
| `Expires appears more than once` | Two `Expires` fields |
| `malformed Expires: want an ISO 8601 date-time with time zone` | A value that is no date-time, or has no time zone |
| `Expires is in the past` | `Expires` is at or before the time of the run |
| `site root not found`, `site root outside the repository` | A configured root that does not exist, or lies outside the repository |

Field names are case-insensitive, comments are skipped and an OpenPGP cleartext signature is read correctly. The result is `fail` on any hit, `pass` when every root has a valid file and `n/a` when `roots` is empty. With the default root, a repository without a security.txt fails: enable the rule only for repositories that serve a site.

### compliance.no-third-party

`checks/no_third_party.py`. For each HTML file (`**/*.html`, `**/*.htm`) under the site roots it collects every resource the browser loads on page load and reports the ones on a host outside the option `allowed_hosts` (default empty). The snippet names the tag, the attribute and the host, for example `script src loads from third-party host: <host>`.

| What is checked | Snippet starts with |
|---|---|
| `<script src>` | `script src` |
| `<link href>` with `rel` stylesheet, preload, modulepreload, prefetch, preconnect, icon, apple-touch-icon, mask-icon or manifest | `link rel=<rel> href` |
| `<img src>`, `<img srcset>`, `<iframe src>`, `<source src>`, `<source srcset>`, `<video src>`, `<video poster>`, `<audio src>` | `<tag> <attribute>` |
| `url()` and `@import` in `<style>` blocks | `style url()`, `style @import` |
| `url()` in `style` attributes | `style attribute url()` |

Relative and root-relative URLs pass, and so do `data:` and `blob:` URLs. `<a href>` links, `<link rel=canonical>` and other links that load nothing do not count. Content inside `<pre>` and `<code>` is skipped, and so is any path below a root with a segment that starts with `_`. An entry `*.example.com` in `allowed_hosts` allows every subdomain of `example.com`. The result is `fail` on any hit, `pass` when no page loads from a third-party host and `n/a` when no HTML file matches. Scripts that fetch from other hosts at run time are outside what the rule can see; check those in the browser's network panel.

### Enable

Enable each rule with `/gate:add-rule` (path A: install a module's check). By hand, from a clone of this repository:

1. Copy the rules into the gate's rules folder: `cp -n plugins/compliance/checks/security_txt.py plugins/compliance/checks/no_third_party.py <repo>/.github/actions/gate/rules/`.
2. Copy the fixtures: `mkdir -p <repo>/gate/fixtures && cp -Rn plugins/compliance/checks/fixtures/compliance.security-txt plugins/compliance/checks/fixtures/compliance.no-third-party <repo>/gate/fixtures/`.
3. Add the rules to `gate/gate.json` in the `warn` tier first, with the folder the site is served from:

   ```json
   "compliance.security-txt": {"tier": "warn", "options": {"roots": ["<site root>"]}},
   "compliance.no-third-party": {"tier": "warn", "options": {"roots": ["<site root>"], "allowed_hosts": []}}
   ```

   The fixtures use the default root `.`. With another root, move the fixture files under the same folder in `gate/fixtures/<rule id>/pass/` and `fail/`, so `gate.rule-fixtures` runs them with your options.
4. Move a rule to `"tier": "block"` once the fixtures are in place and a false-positive test over your own site is recorded under the rule as `"false_positive_test": {"date": ..., "corpus": ..., "hits": ..., "legitimate": ..., "decision": ...}`. The rule `gate.rule-fixtures`, which `/gate:gate-init` installs, checks both.

Run them on their own with `python3 .github/actions/gate/run.py --only compliance.security-txt,compliance.no-third-party --dry-run`.

Demo: [machinebehavior.io/inside/docs/std/](https://machinebehavior.io/inside/docs/std/), the standards and compliance space of the platform behind machinebehavior.io.
