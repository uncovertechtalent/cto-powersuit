---
type: regex
pattern: 'secrets pre-push hook[\s\S]*secrets\.py'
target: { source: file, path: template/hooks/pre-push.d/20-secrets }
---
