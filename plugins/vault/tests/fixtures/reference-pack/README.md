# Fixtures for the reference pack tests

The tests in `../../test_reference_pack.py` replay these folders as if they were the site. Each `site/` folder is laid out as the site's URL tree, so `https://machinebehavior.io/map/index.html.md` is `site/map/index.html.md`. No test opens a network connection.

## pass/recorded

A recorded copy of six pages of machinebehavior.io, fetched on 2026-10-20 from the live site after the pull request that publishes the corpus was deployed. The twins are byte for byte as the site served them. Their sha256, which is the `sha256:` value an import writes:

| Twin | sha256 |
|---|---|
| `index.html.md` | `bef68ef699e2c4915112c2fe8fa8bf4147ec864d6db89f0d2c4f0ac7c5e98644` |
| `inside/docs/eng/adr-0002-deploy-is-gated/index.html.md` | `867513204e5cc33a74e0b4cda75ff6a382462e53dee6cd1f0262ccff649e5c09` |
| `inside/docs/sre/incidents/index.html.md` | `e703b4d243f1aafcb75d40a3f62592da9ad4e771db23a1ee513b9c39e017a6e1` |
| `inside/docs/sre/pillars/index.html.md` | `c2f94266ba52683afb8e3eea1358f23fb9e782877c152c77a35e485fe2f14fd2` |
| `inside/search/index.html.md` | `2444ddcf55554f34a7cdc9f4d86b57fd5d6743110e188f5a74a352c50a078477` |
| `map/index.html.md` | `a7ada093f144c6dede6f1a9340ebf6fe62cd85ce9f06aa3d0ad188b2775669f2` |

`site/llms-passages.json` is the live passage index cut down to what the importer reads: the `generated`, `site`, `source`, and `tokenizer` fields and the six `pages` entries as served. The `passages` and `bm25` parts are left out.

To record again, fetch the manifest and the twins of the pages you want with `curl`, keep the manifest entries as served, and update the table above.

## pass/instructions-as-data

Made up. One page whose text gives orders to an agent, has a line that looks like front matter, and has a comment that looks like an end marker. It carries no hidden character and no real pack marker, so the importer takes it, byte for byte, between the markers of the note.

## fail

Made up, one defect each. The test for each fixture states what it expects.

| Folder | Defect |
|---|---|
| `hidden-chars` | A twin with a zero-width space (U+200B) and a right-to-left override (U+202E) in its text. Invisible in an editor; the test checks that they are present. |
| `marker-forgery` | A twin with a line shaped like a pack end marker, followed by text that speaks as the vault owner. |
| `offsite-url` | A manifest entry on `evil.example` beside a good page. |
| `url-mismatch` | A twin whose front matter names another page than the manifest does. |
| `truncated-manifest` | A passage index cut off in the middle. |
