#!/usr/bin/env bash
# Fixture: a clone of a small public CLI tool at ./src. It has an AWS key in a tracked settings file,
# a status server that binds to all interfaces and runs a shell command built from the request,
# actions pinned by tag, and requirements with ranges and no lock file.
# The key is assembled at run time so this file holds no secret pattern.
set -euo pipefail
export GIT_AUTHOR_NAME="Acme Dev" GIT_AUTHOR_EMAIL="dev@acme-tools.example" GIT_COMMITTER_NAME="Acme Dev" GIT_COMMITTER_EMAIL="dev@acme-tools.example"
mkdir src && cd src
git init -q -b main .
mkdir -p widget .github/workflows
cat > README.md <<'MD'
# widget

A command-line tool that resizes product images for small shops. Install it with `pip install acme-widget`
and run `widget resize photos/`. `widget serve` starts a status page on port 8080.
MD
cat > requirements.txt <<'TXT'
pillow>=10
click>=8
TXT
cat > widget/__init__.py <<'PY'
__version__ = "0.4.0"
PY
cat > widget/cli.py <<'PY'
import click


@click.group()
def main():
    pass


@main.command()
@click.argument("folder")
def resize(folder):
    click.echo(f"resizing {folder}")
PY
cat > widget/server.py <<'PY'
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Status(BaseHTTPRequestHandler):
    def do_GET(self):
        folder = self.path.lstrip("/") or "."
        listing = os.popen("ls -la " + folder).read()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(listing.encode())


def serve():
    HTTPServer(("0.0.0.0", 8080), Status).serve_forever()
PY
cat > .github/workflows/ci.yml <<'YML'
name: ci
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt && python -m compileall widget
YML
git add -A && git commit -q -m "First release"
printf 'S3_BUCKET = "acme-widget-uploads"\nAWS_ACCESS_KEY_ID = "%s%s"\n' "AKIA" "Z3KQ8VJ2LM5XR7TD" > widget/settings.py
git add -A && git commit -q -m "Upload resized images to S3"
printf '\n@main.command()\ndef serve():\n    from widget.server import serve as run\n    run()\n' >> widget/cli.py
git add -A && git commit -q -m "Status page"
git remote add origin https://github.com/acme-tools/widget.git
