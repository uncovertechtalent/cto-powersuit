---
name: release
description: >
  Prepare a release: a changelog entry drafted from the main line, a rollback
  plan, the feature flags the release depends on, and the release record with
  tag, changelog and deploy run. Use before a deploy that users will notice,
  before tagging a version, or when nobody knows how to undo the last release.
  Activates on "/release", "prepare the release", "write the changelog",
  "how do we roll back", "tag a version".
user-invocable: true
---

# Release

Gets a release ready to ship and to undo.

## Steps

1. **Draft the changelog.** If `scripts/changelog_draft.py` is missing, copy it without overwriting: `cp -n "${CLAUDE_PLUGIN_ROOT}/templates/scripts/changelog_draft.py" scripts/`. Then:

   ```bash
   python3 scripts/changelog_draft.py --version <x.y.z>
   ```

   It prints the commits since the last tag on the main line, grouped into Added, Changed, Fixed, Removed and Security, without bot commits. The grouping reads words, so edit the draft: merge duplicates, write each entry for a user, drop internal noise. Add the edited entry to `CHANGELOG.md` above the previous release.
2. **Write the rollback plan.** One of:
   - Redeploy the previous artifact or tag (name the command and how long it takes).
   - Revert the merge commit and let the pipeline deploy it.
   - Turn the feature flag off.
   Schema or data migrations need their own line: backward-compatible migrations ship first, destructive steps ship in a later release after the rollback window.
3. **List the feature flags** the release depends on: name, default, owner and the date the flag gets removed. A flag with no removal date gets a ticket.
4. **Check the gate.** The gate run on the release commit passed, if the gate is installed.
5. **Record the release** after the user deploys: tag, changelog entry, deploy run link and the dashboard to watch. With the user's go: `git tag -a v<x.y.z> -m "<summary>"` and `gh release create v<x.y.z> --notes-file <entry>`.

## Output

The changelog entry, the rollback plan, the flag list and the commands to tag and publish, for the user to run or approve.

## Rules

- Never tag, push, deploy or publish a release without the user's go.
- Every release has a rollback path before it ships.
- The changelog is for users. Commit hashes stay as links; internal file names stay out.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/sdlc" 2>/dev/null
```

If `$POWERSUIT_OVERLAY/sdlc/` exists, read its `README.md` first, then the files in `sdlc/release/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. Never copy overlay content into this plugin, into its templates or into any public repository.
