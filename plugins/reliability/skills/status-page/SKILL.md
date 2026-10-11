---
name: status-page
description: >
  Set up a static status page built from published records: the service
  catalogue in services/*.yml and the incident records in
  incidents/incidents.json, turned into one HTML page and a JSON file by a
  standard-library script that runs in the deploy job. Use when users need one
  place to see whether a service works and what happened before, or when a
  hosted status tool is more than the team needs. Activates on "/status-page",
  "status page", "set up a status page", "public incident history", "build the
  status page", "where do users see outages".
user-invocable: true
---

# Status page

Sets up a status page that a script builds from two records in the repository: the service catalogue and the incident records. The page shows each service with its tier and SLO target, the open incidents with their timeline, and the incidents resolved in the last 90 days. It needs no JavaScript and loads nothing from a third party. It is as fresh as its last build, so the deploy job runs the script, and every change to an incident goes out through a deploy.

A service without an open incident shows "No open incident". The script reads no live check. A team that wants live state adds a probe and opens an incident when the probe fails.

## Inputs

- **Services on the page**: by default every entry in `services/`. An entry with `status_page: hidden` stays off the page and out of the incident service lists, for example an internal database.
- **Where the page is served**: the output folder of the site build, and the URL.
- **Title**: default "Status".
- **Docs URL prefix**: for `doc:` links to postmortems, default `/docs/`, the default of the `docs` module.

## Steps

1. **Set up.** Copy the templates without overwriting:

   ```bash
   mkdir -p services incidents scripts
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/services/_template.yml" services/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/incidents/" incidents/
   rsync -a --ignore-existing "${CLAUDE_PLUGIN_ROOT}/templates/scripts/build_status.py" scripts/
   ```

   Without rsync, use `cp -n` for each file.
2. **Fill the catalogue.** One `services/<id>.yml` per service users can see fail, from `services/_template.yml`. Add the serial dependencies too, with `status_page: hidden` when users do not know them by name. If the gate runs the rule, run `python3 .github/actions/gate/run.py --only reliability.service-catalog --dry-run`.
3. **Validate.** Run `python3 scripts/build_status.py --check`. It validates the catalogue and the incidents, and lists each SLO target next to its dependency ceiling. Fix every problem it reports.
4. **Build.**

   ```bash
   python3 scripts/build_status.py --out <site output>/status --title "<product> status" --docs-prefix /docs/
   ```

   The output is `index.html` and `status.json`. Serve the folder locally and read the page: `python3 -m http.server -d <site output>/status 8000`.
5. **Add the build to the deploy job.** One step before the upload of the site, for example in a GitHub Actions workflow:

   ```yaml
   - name: Build the status page
     run: python3 scripts/build_status.py --out <site output>/status --title "<product> status"
   ```

   Show the change to the user. The user merges it.
6. **Choose the host.** When the product is down, the status page must still load. Serve it from a host that shares as little as possible with the product: another provider, another domain or a static host. Name the shared parts that remain, for example DNS.
7. **Agree the update path.** An incident update is a change to `incidents/incidents.json` plus a deploy. Write the steps into the incident runbook, or use the `incident` skill, which prepares each update.
8. **Report.**

## Output

The page URL or folder, the number of services shown and hidden, the open incidents, the build step added to the deploy job, and the shared parts between the product and the status page host.

## Rules

- The page shows only what is in the records. A service state comes from open incidents.
- Text on the page is public: no internal host names, addresses, customer names or personal details.
- The page loads nothing from a third party.
- The skill never pushes and never deploys. It prepares the files and the workflow step, and the user publishes.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/reliability" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/reliability/` exists, read its `README.md` first, then the files in `reliability/status-page/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
