---
type: regex
pattern: 'docs-update'
match: not_contains
target: { source: file, path: remote.git/pushed.log }
---
