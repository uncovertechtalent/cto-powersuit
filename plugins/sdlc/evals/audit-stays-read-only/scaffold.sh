#!/usr/bin/env bash
# Fixture: a small web app built fast with an agent. Direct pushes to main, a deploy job that
# waits for nothing, no tests, no lock file, a tracked .env with an access key, and generated files in git.
# The key is assembled at run time so this file holds no secret pattern.
set -euo pipefail
export GIT_AUTHOR_NAME="Dev" GIT_AUTHOR_EMAIL="dev@example.com" GIT_COMMITTER_NAME="Dev" GIT_COMMITTER_EMAIL="dev@example.com"
git init -q -b main .
cat > README.md <<'MD'
# shopfront

A small shop front for our customers.
MD
cat > package.json <<'JSON'
{
  "name": "shopfront",
  "version": "1.0.0",
  "scripts": { "start": "node src/server.js" },
  "dependencies": { "express": "^4.19.0" }
}
JSON
mkdir -p src .github/workflows
cat > src/server.js <<'JS'
const express = require("express");
const app = express();
app.get("/", (req, res) => res.send("shop"));
app.listen(process.env.PORT || 3000);
JS
git add -A && git commit -q -m "Initial shop front"
printf 'AWS_ACCESS_KEY_ID=%s%s\nAWS_REGION=eu-central-1\n' "AKIA" "Q7RZ4T2XK9W3B6MN" > .env
git add .env && git commit -q -m "Add AWS config"
cat > .github/workflows/deploy.yml <<'YML'
name: deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
YML
printf 'app = "shopfront"\nprimary_region = "fra"\n' > fly.toml
git add -A && git commit -q -m "Deploy on push"
printf 'app.get("/cart", (req, res) => res.send("cart"));\n' >> src/server.js
mkdir -p __pycache__ && printf 'x' > __pycache__/build.cpython-312.pyc && printf 'x' > .DS_Store
git add -A && git commit -q -m "Cart page"
printf 'app.get("/health", (req, res) => res.send("ok"));\n' >> src/server.js
git add -A && git commit -q -m "Health route"
