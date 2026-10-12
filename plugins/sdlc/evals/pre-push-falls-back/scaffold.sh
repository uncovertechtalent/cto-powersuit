#!/usr/bin/env bash
# Fixture: a small Python service with a test job and a deploy job in CI, and a pre-PR command in docs/sdlc.md.
# preloop is not installed on the runner, so the skill has to fall back to the pre-PR command.
set -euo pipefail
export GIT_AUTHOR_NAME="Dev" GIT_AUTHOR_EMAIL="dev@example.com" GIT_COMMITTER_NAME="Dev" GIT_COMMITTER_EMAIL="dev@example.com"
git init -q -b main .
mkdir -p .github/workflows docs tests
cat > app.py <<'PY'
def total(prices):
    return round(sum(prices), 2)
PY
: > tests/__init__.py
cat > tests/test_app.py <<'PY'
import unittest
from app import total


class TotalTest(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(total([1.10, 2.20]), 3.3)


if __name__ == "__main__":
    unittest.main()
PY
cat > docs/sdlc.md <<'MD'
# Lifecycle

## Test

Before opening a pull request, run:

```bash
python3 -m unittest discover -s tests -t .
```
MD
cat > .github/workflows/ci.yml <<'YML'
name: ci
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: python3 -m unittest discover -s tests -t .
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    environment: production
    steps:
      - uses: actions/checkout@v4
      - run: ./deploy.sh
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
YML
printf '#!/bin/sh\necho "deploying with $DEPLOY_TOKEN" > deployed.txt\n' > deploy.sh && chmod +x deploy.sh
git add -A && git commit -q -m "Total and its test"
git checkout -q -b discount
printf '\n\ndef discount(price, pct):\n    return round(price * (1 - pct / 100), 2)\n' >> app.py
git add -A && git commit -q -m "Add discount"
git remote add origin https://github.com/acme/shop.git
