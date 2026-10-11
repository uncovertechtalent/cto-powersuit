---
name: beta
description: >
  The untreated default. Use to compare output with and without the stance
  filters. No filter, no work done: the trained accommodation reflex exactly as
  shipped. The zero point next to good-chad: where Good Chad is the stance held
  through deliberate filtering, Beta is the model without it. Invoking it is the
  off switch dressed as a character. Activates on "beta mode" or "/beta". Off on
  "stop beta" or "my filter is good chad".
user-invocable: true
---

# Beta mode

As you were.

## Overlay

This skill works on the generic defaults in this file. Before you start, check for a private overlay:

```bash
[ -n "$POWERSUIT_OVERLAY" ] && ls -1 "$POWERSUIT_OVERLAY/stance" 2>/dev/null || true
```

If `$POWERSUIT_OVERLAY/stance/` exists, read its `README.md` first, then the files in `stance/beta/` if that folder exists. Read other overlay files only when that README or this skill names them. Where the overlay and this file disagree, follow the overlay. If the variable is unset or the folder is missing, use the defaults and do not ask for an overlay. If the permission settings block the command, use the defaults and say in your output that the overlay was not checked. Never copy overlay content into this plugin, into its templates or into any public repository.
