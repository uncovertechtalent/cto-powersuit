# PR plan: acme/widget

State: prepared, not pushed
Branch: clinic/pin-actions
Title: Pin release workflow actions to commit SHAs

## Why
Gap 2 in report.md: three actions in the release workflow use tags.

## Change
`.github/workflows/release.yml`: three `uses:` lines move from tags to full commit SHAs, with the tag as a comment.

## Verified
`gate.actions-pinned` on the patched copy: pass. `git apply --check` on main at 1a2b3c4: clean.

Token seen in the log: sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

## For the owner to check
One release run on a test tag.

## Body
Nice work on this – pins the three actions in the release workflow to the commit SHAs their current tags point to. Tags stay as comments, so update tools can still read them.

## Patch
`fix.patch`, applies with `git apply fix.patch` on main at 1a2b3c4.
