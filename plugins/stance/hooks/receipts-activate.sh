#!/usr/bin/env bash
# receipts-activate: SessionStart hook. Emits the receipts standard
# (skills/receipts/SKILL.md, frontmatter stripped) as session context, ahead of
# the style filters. Set STANCE_RECEIPTS=off to turn it off.
[ "${STANCE_RECEIPTS:-on}" = "off" ] && exit 0
skill="$(cd "$(dirname "$0")/.." && pwd)/skills/receipts/SKILL.md"
[ -f "$skill" ] || exit 0
echo "RECEIPTS STANDARD ACTIVE."
awk 'BEGIN{fm=0} NR==1 && /^---$/ {fm=1; next} fm && /^---$/ {fm=0; next} !fm' "$skill"
