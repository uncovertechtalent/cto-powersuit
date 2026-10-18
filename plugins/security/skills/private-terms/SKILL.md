---
name: private-terms
description: >
  Keep private terms out of public repositories and pages: names of
  prospective employers or clients, internal shorthand, family names in
  business copy, private hosts and addresses. The term list stays on the
  owner's machine; a pre-push hook stops a push that adds a term, and a gate
  dry run scans the tree and the built pages. Use before a repository goes
  public, after a private note landed in a public file, or when an agent
  writes into public repositories. Activates on "/private-terms", "private
  terms", "keep this name out of the repo", "a private note went public",
  "block internal names", "pre-push check for names".
user-invocable: true
---

# Private terms

Some words must never reach a public repository: the name of a company in talks, a project codename, a family member's name in a business page, an internal host. Rules like these hold only by memory until a check reads them. An agent that copies a chat aside into a README breaks them without noticing.

The check needs a list of the terms, and that list is itself private. So the list stays outside every repository, on the machine that pushes, and the check runs there.

## Why the list stays local

| Option | What it gives | What it costs |
|---|---|---|
| A hash list in the repository | CI can match without the plain terms | Short terms such as a name or a company fall to a dictionary in seconds; the hashes give the list away |
| The list as a CI secret | Every push is checked, from any machine | A public repository publishes a pushed commit before CI runs, so CI only finds a term after it is out. Every workflow run, and anyone who can push a workflow change, can read the secret |
| **The list on the pushing machine (this skill)** | A pre-push hook stops the push before anything leaves the machine, for commits, messages, file names, branch and tag names | Pushes from other machines and edits in the web interface are not checked; run the dry run before a release to cover them |

## The term list

`$POWERSUIT_OVERLAY/security/private-terms.txt`, or the file `--terms` and the `terms_file` option name. One term per line:

```text
# Lines that start with # are comments.
# A term matches without case, on word boundaries; a space matches any run of whitespace, line breaks included.
Example Corp
# An optional label before " = " names the term in reports and allow files. Pick labels that say nothing.
employer-a = Example Corp
# A regular expression after "re:"; the word boundaries wrap it.
host-b = re:build-?box\.lan
```

A term without a label is reported as `line<N>`, its line number in the list. HTML, XML and SVG files are read twice: as written, for attributes and URLs, and as a reader sees them, with tags removed and entities decoded, so `Example <em>Corp</em>` and `Example&nbsp;Corp` match. Soft hyphens and zero-width characters do not split a term.

Reports never show a term. A hit shows the file, the line and the label, with the term masked, also inside a file name: `drafts/****.md private term family-b **** in the file name`.

## The allow file

An intended mention, such as a former employer on an about page, goes into `.private-terms-allow` at the repository root. One entry per line: a path glob, a label (or `*` for every term), and a reason. An entry without a reason is a hit.

```text
about/index.html employer-a Former employer, named on the about page on purpose
```

The allow file is public. Write the glob so it does not spell the term (`drafts/b*.md`, not the full name), and use labels that say nothing about the term.

## Steps

1. **Seed the list.** Create `$POWERSUIT_OVERLAY/security/private-terms.txt` from the comment block above, outside every repository, and let the user fill it. Never write a real term yourself, and never read the list back into the conversation. If the overlay folder is under version control, add the file to its ignore list so the plain terms are never committed.
2. **Install the hook.** The hook is a two-line shim that runs `checks/private_terms.py` from a fixed place. Copy the script out of the plugin first, so an update of the plugin cannot break the hook:

   ```bash
   mkdir -p ~/.config/private-terms && cp "${CLAUDE_PLUGIN_ROOT}/checks/private_terms.py" ~/.config/private-terms/
   python3 ~/.config/private-terms/private_terms.py install-hook --into .git/hooks --terms "$POWERSUIT_OVERLAY/security/private-terms.txt"
   ```

   For every clone made from now on, agents' fresh clones included, write the shim into a git template folder instead. The user sets the template, since it changes the global git configuration:

   ```bash
   python3 ~/.config/private-terms/private_terms.py install-hook --into ~/.config/private-terms/template/hooks --terms "$POWERSUIT_OVERLAY/security/private-terms.txt"
   git config --global init.templateDir ~/.config/private-terms/template
   ```

   `git init` in an existing repository then adds the hook there too, and never replaces a hook that is already in place. `init.templateDir` holds one folder, so `/security:secrets` installs into the same template. `install-hook` refuses to replace another pre-push hook, with one exception: when `secrets.py install-hook` has put its dispatcher there, the shim goes into `pre-push.d/10-private-terms` and both hooks run. For any other hook, chain the two by hand.
3. **Know what the hook reads.** For each pushed ref it reads the commits the remote does not have yet: messages, author and committer, the names of new files, and every added line, joined across line breaks. It also reads the branch or tag name and the message of an annotated tag. A missing list stops the push, and the output says where the hook looks: fix the `--terms` path in `.git/hooks/pre-push` (in `pre-push.d/10-private-terms` when the secrets dispatcher is installed), or create the list there. A hit has the allow file as its exit. A repository that has no private terms points the hook at a list that holds only comments: the hook then lets every push through with a note and checks nothing. The output never offers to skip the hook, and neither do you: a refusal is answered with one of those exits.
4. **Scan the tree.** Commits that are already public are outside the hook. Scan the whole tree once, with the build output of a site:

   ```bash
   python3 ~/.config/private-terms/private_terms.py scan . --built public
   ```

   For the history, count only. `history` reads every commit on every ref and prints a count per label, no line:

   ```bash
   python3 ~/.config/private-terms/private_terms.py history .
   ```

   Removing a term from the history needs a force push and the repository owner's go; it does not reach clones and forks made before.
5. **Add the gate check.** With the gate in place, copy the rule and its fixtures, and add it on `warn`:

   ```bash
   cp "${CLAUDE_PLUGIN_ROOT}/checks/private_terms.py" .github/actions/gate/rules/
   mkdir -p gate/fixtures && cp -R "${CLAUDE_PLUGIN_ROOT}/checks/fixtures/security.private-terms" gate/fixtures/
   ```

   ```json
   "security.private-terms": {"tier": "warn", "options": {"built": ["public"]}}
   ```

   In CI the list is absent and the rule returns `n/a`. On the owner's machine it runs with the dry run: `python3 .github/actions/gate/run.py --only security.private-terms --dry-run`. Its fixtures carry their own made-up list in `overlay/`; test the rule with that folder as `POWERSUIT_OVERLAY`.
6. **Record the false-positive test** with the real list, as counts only (files read, hits, legitimate), then move the rule to `block`.

Options in `gate/gate.json`:

| Option | Default | Use |
|---|---|---|
| `terms_file` | `$POWERSUIT_OVERLAY/security/private-terms.txt` | Another path to the list. A list inside the scanned tree is refused |
| `allow_file` | `.private-terms-allow` | The allow file, relative to the root |
| `built` | `[]` | Folders read even when git does not track them, such as a site's build output |
| `tracked_only` | `true` | `false` reads every file under the root |
| `require_list` | `false` | `true` fails instead of `n/a` when the list is missing or empty |

## Output

- The term list in the overlay, filled by the user, ignored by every version control.
- The pre-push hook in each repository that publishes, or in the git template for every new clone.
- A tree scan of each public repository and its built pages: hits by file, line and label, never a term.
- The gate check, `n/a` in CI and run by the dry run on the owner's machine.

## Rules

- Never write a real term into a file, commit, pull request, issue, ticket, or chat reply. Test with made-up terms only.
- Never print the list or pass a term on a command line, where the process list shows it. Read it from the file.
- Changes to the global git configuration, a history rewrite, and a force push are the user's actions.
- A refusal by the hook is fixed or documented: take the term out of the commits, add an entry with a reason to `.private-terms-allow`, or correct the path to the list. Never offer a way around the hook as the answer.
- A hit in a commit that is already public is out. Treat it as exposed: tell the user, fix the file, and decide with the owner on the history.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/security" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/security/` exists, read its `README.md` first, then the files in `security/private-terms/` if that folder exists. Read other overlay files only when that README or this skill names them. Do not read `private-terms.txt` into the conversation: the script reads it. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
