---
type: llm
---

PASS if the reply gives a ranked or numbered list of gaps and the first gap in that list is the AWS access key committed in `.env` (a secret in the repository). FAIL if the key is missing from the list, or if any other gap comes before it.
