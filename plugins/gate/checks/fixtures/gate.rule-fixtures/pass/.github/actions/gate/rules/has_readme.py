"""Example rule for the fixture test: the repository has a README.md at its root."""
ID = "example.has-readme"
DEFAULTS = {}


def check(ctx):
    ok = (ctx.root / "README.md").is_file()
    return {"result": "pass" if ok else "fail", "detail": "README.md at the root" if ok else "no README.md at the root",
            "hits": [] if ok else [{"file": "README.md", "snippet": "missing README.md"}]}
