#!/usr/bin/env python3
"""Build a static docs site from Markdown pages. Standard library only, Python 3.9+.

Sources: docs/<space>/<slug>.md, one file per page, each with front matter. The spaces, the output folder and the
URL prefix come from docs/docs.json. A file or folder whose name starts with '_' is skipped (docs/_templates/).
A space in the config without a folder is skipped.

Output, under the configured "out" folder, served at "url_prefix":
  index.html                  docs home: the spaces and the recently updated pages
  <space>/index.html          space home, from docs/<space>/index.md
  <space>/<slug>/index.html   one folder per page
  health/index.html           owners, review dates and types: what is missing or late
  search.json                 title, summary, labels and text of every page
Before writing, the build removes <out>/<space>/ for every configured space and <out>/health/.

Usage (from the repository root):
  python3 scripts/build_docs.py [--config docs/docs.json] [--check] [--stale] [--today YYYY-MM-DD]

  --check   parse, validate and render every page in memory, write nothing
  --stale   list the pages that need a review, grouped by owner, write nothing
  --today   use this date as today

Exit codes: 0 done, 1 errors in the pages (nothing is written), 2 config error.
"""
import argparse, datetime, html, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPES = ('tutorial', 'how-to', 'reference', 'explanation')  # Diátaxis
ADR_STATUS = ('proposed', 'accepted', 'rejected', 'deprecated', 'superseded')
RFC_STATUS = ('draft', 'review', 'accepted', 'rejected', 'withdrawn')
REVIEW_FIELDS = ('owner', 'reviewed', 'review_by', 'type')
DATE_FIELDS = ('created', 'updated', 'date', 'comments_close')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
SLUG = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
SPACE_KEY = re.compile(r'^[a-z0-9][a-z0-9-]*$')
RESERVED = {'health'}  # the health page uses this folder
SOON_DAYS = 30


class ConfigError(Exception):
    pass


class Stop(Exception):
    """A build phase found errors. Nothing is written."""


# The same function as parse_front_matter in the gate runner (.github/actions/gate/run.py), so the build and
# the gate read front matter the same way.
def parse_front_matter(text):
    """Return (meta, body, body_line). Accepts a block between two '---' lines at the top of the file,
    or a header of 'key: value' lines ended by a '---' line. Values are strings; a key followed by
    '- item' lines becomes a comma-separated string. Without front matter: ({}, text, 1)."""
    lines = text.split("\n")
    key_line = re.compile(r"^([A-Za-z_][\w-]*)\s*:(.*)$")
    head, start = None, 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                head, start = lines[1:i], i + 1
                break
    elif lines and key_line.match(lines[0]):
        for i, line in enumerate(lines):
            if line.strip() == "---":
                head, start = lines[:i], i + 1
                break
            if line.strip() and not (key_line.match(line) or line.lstrip().startswith("- ")):
                break
    if head is None:
        return {}, text, 1
    meta, last = {}, None
    for line in head:
        m = key_line.match(line)
        if m:
            last = m.group(1)
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            if v.startswith("[") and v.endswith("]"):
                v = ", ".join(x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip())
            meta[last] = v
        elif last and line.lstrip().startswith("- "):
            item = line.lstrip()[2:].strip().strip("\"'")
            meta[last] = (meta[last] + ", " + item) if meta[last] else item
    return meta, "\n".join(lines[start:]), start + 1


def is_date(v):
    if not DATE.match(v or ''):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def add_days(d, n):
    return (datetime.date.fromisoformat(d) + datetime.timedelta(days=n)).isoformat()


def split_list(v):
    return [re.sub(r'\.md$', '', x.strip()) for x in (v or '').split(',') if x.strip()]


def esc(s):
    return html.escape(str(s), quote=True)


def text_of(h):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h))).strip()


def slugify(s):
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'[^a-z0-9]+', '-', html.unescape(s).lower()).strip('-') or 'section'


def short_title(p):
    """'ADR-0004: Use one queue' -> 'Use one queue'."""
    return p['title'].split(': ', 1)[-1]


def count(n, word):
    return f'{n} {word}' + ('' if n == 1 else 's')


def cell(s):
    return str(s).replace('|', '\\|')


# ---------- config ----------
def load_config(path):
    try:
        cfg = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise ConfigError(f'config not found: {path}')
    except json.JSONDecodeError as e:
        raise ConfigError(f'{path}: {e}')
    if not isinstance(cfg, dict):
        raise ConfigError(f'{path}: the config must be a JSON object')
    cfg.setdefault('title', 'Docs')
    cfg.setdefault('out', 'site/docs')
    cfg.setdefault('url_prefix', '/docs/')
    cfg.setdefault('base_url', '')
    cfg.setdefault('lang', 'en')
    cfg.setdefault('review_interval_days', 90)
    cfg['base_url'] = (cfg['base_url'] or '').rstrip('/')
    if not (cfg['url_prefix'].startswith('/') and cfg['url_prefix'].endswith('/')):
        raise ConfigError(f'{path}: url_prefix must start and end with "/"')
    if not str(cfg['out']).strip():
        raise ConfigError(f'{path}: out must name a folder')
    if not isinstance(cfg['review_interval_days'], int) or cfg['review_interval_days'] < 1:
        raise ConfigError(f'{path}: review_interval_days must be a whole number of days')
    spaces = cfg.get('spaces')
    if not isinstance(spaces, list) or not spaces:
        raise ConfigError(f'{path}: spaces must list at least one space')
    seen = set()
    for s in spaces:
        k = s.get('key', '')
        if not SPACE_KEY.match(k):
            raise ConfigError(f'{path}: space key {k!r} must use a-z, 0-9 and -')
        if k in RESERVED:
            raise ConfigError(f'{path}: space key {k!r} is reserved')
        if k in seen:
            raise ConfigError(f'{path}: space key {k!r} is listed twice')
        if not s.get('name'):
            raise ConfigError(f'{path}: space {k!r} needs a name')
        seen.add(k)
        s.setdefault('about', '')
        s.setdefault('owner', '')
    return cfg


# ---------- markdown ----------
PANEL = {'note': 'note', 'info': 'info', 'abstract': 'info', 'summary': 'info', 'question': 'info', 'tip': 'tip',
         'success': 'tip', 'important': 'note', 'example': 'note', 'warning': 'warning', 'caution': 'warning',
         'danger': 'warning', 'failure': 'warning', 'bug': 'warning'}
LIST_ITEM = re.compile(r'^\s*([-*+]|\d+[.)])\s+')


class Ctx:
    def __init__(self, page):
        self.page = page
        self.out_links = set()
        self.ids = set()


class Site:
    def __init__(self, cfg, src, out, today):
        self.cfg, self.src, self.out, self.today = cfg, src, out, today
        self.soon = add_days(today, SOON_DAYS)
        self.prefix = cfg['url_prefix']
        self.base = cfg['base_url']
        self.interval = cfg['review_interval_days']
        self.spaces = cfg['spaces']
        self.space = {s['key']: s for s in self.spaces}
        self.pages, self.children = {}, {}
        self.errors, self.warnings = [], []
        self.files = {}  # path relative to out -> text

    # ----- reporting -----
    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def checkpoint(self):
        if self.errors:
            raise Stop()

    def rel(self, path):
        try:
            return Path(path).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return str(path)

    def build(self):
        self.check_paths()
        self.load()
        self.checkpoint()
        self.tree()
        self.checkpoint()
        self.decisions()
        self.checkpoint()
        self.render_all()
        self.checkpoint()
        self.assemble()

    def check_paths(self):
        """The build removes <out>/<space>/ and <out>/health/; none of them may hold the sources or the repository."""
        if self.out == ROOT or ROOT.is_relative_to(self.out) or not self.out.is_relative_to(ROOT):
            raise ConfigError(f'out folder {self.out} must be a folder inside the repository, below its root')
        for k in [s['key'] for s in self.spaces] + ['health']:
            t = self.out / k
            if t == self.src or self.src.is_relative_to(t) or t.is_relative_to(self.src) or ROOT.is_relative_to(t):
                raise ConfigError(f'out folder {self.rel(self.out)} overlaps the sources in {self.rel(self.src)}; pick another out folder')

    # ----- sources -----
    def git_date(self, path):
        try:
            last = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', str(path)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
            dirty = subprocess.run(['git', 'status', '--porcelain', '--', str(path)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
            return self.today if dirty or not last else last
        except Exception:
            return self.today

    def load(self):
        keys = {s['key'] for s in self.spaces}
        for d in sorted(p for p in self.src.iterdir() if p.is_dir()) if self.src.is_dir() else []:
            if d.name not in keys and not d.name.startswith(('_', '.')) and any(d.glob('*.md')):
                self.warn(f'{self.rel(d)}/: not a space in the config; skipped')
        for sp in self.spaces:
            d = self.src / sp['key']
            if not d.is_dir():
                continue
            for f in sorted(d.rglob('*.md')):
                parts = f.relative_to(d).parts
                if any(x.startswith('_') for x in parts):
                    continue
                if len(parts) > 1:
                    self.warn(f'{self.rel(f)}: pages in subfolders are not read; move the file to {self.rel(d)}/')
                    continue
                p = self.parse_page(f, sp['key'])
                if p:
                    self.pages[(sp['key'], p['slug'])] = p
        for sp in self.spaces:
            if any(k[0] == sp['key'] for k in self.pages) and (sp['key'], 'index') not in self.pages:
                self.error(f'{self.rel(self.src / sp["key"])}/: the space has pages but no index.md')
        if not self.pages and not self.errors:
            self.error(f'no pages found under {self.rel(self.src)}/<space>/')

    def parse_page(self, f, space):
        rel = self.rel(f)
        meta, body, _ = parse_front_matter(f.read_text(encoding='utf-8'))
        if not meta:
            self.error(f'{rel}: no front matter')
            return None
        slug = f.stem
        if not SLUG.match(slug):
            self.error(f'{rel}: the file name must use letters, digits, ".", "_" and "-"')
        for k in ('title', 'summary'):
            if not meta.get(k):
                self.error(f'{rel}: missing {k}')
        for k in DATE_FIELDS:
            if meta.get(k) and not is_date(meta[k]):
                self.error(f'{rel}: {k} must be a date, YYYY-MM-DD')
        rv, rb = meta.get('reviewed', ''), meta.get('review_by', '')
        if rv and rv != 'no' and not is_date(rv):
            self.error(f'{rel}: reviewed must be a date, YYYY-MM-DD, or no')
        if rb and not is_date(rb):
            self.error(f'{rel}: review_by must be a date, YYYY-MM-DD')
        if meta.get('type') and meta['type'] not in TYPES:
            self.error(f'{rel}: type must be one of {", ".join(TYPES)}')
        try:
            order = int(meta.get('order') or 1000)
        except ValueError:
            self.error(f'{rel}: order must be a whole number')
            order = 1000
        missing = [k for k in REVIEW_FIELDS if not meta.get(k) and not (k == 'review_by' and rv == 'no')]
        if missing:
            self.warn(f'{rel}: missing {", ".join(missing)}')
        for kind, statuses in (('adr', ADR_STATUS), ('rfc', RFC_STATUS)):
            if meta.get(kind):
                if not meta[kind].isdigit():
                    self.error(f'{rel}: {kind} must be a number')
                if meta.get('status') not in statuses:
                    self.error(f'{rel}: status must be one of {", ".join(statuses)}')
        if meta.get('adr') and meta.get('rfc'):
            self.error(f'{rel}: a page carries adr or rfc; this page has both')
        p = dict(meta)
        p.update(space=space, slug=slug, body=body.strip('\n'), src=rel, order=order,
                 labels=[x.strip() for x in meta.get('labels', '').split(',') if x.strip()],
                 url=self.prefix + space + '/' + ('' if slug == 'index' else slug + '/'))
        created = meta.get('created') or meta.get('date') or ''
        p['updated'] = meta.get('updated') or max(self.git_date(f), created)
        p['created'] = created or p['updated']
        if is_date(rv) and not rb:
            p['review_by'], p['review_by_default'] = add_days(rv, self.interval), True
        return p

    # ----- tree -----
    def tree(self):
        for (sk, slug), p in self.pages.items():
            if slug == 'index':
                continue
            par = re.sub(r'\.md$', '', p.get('parent', '').strip()) or 'index'
            if (sk, par) not in self.pages:
                self.warn(f'{p["src"]}: parent {par} not found; placed under the space home')
                par = 'index'
            p['parent'] = par
            self.children.setdefault((sk, par), []).append(p)
        for k in self.children:
            self.children[k].sort(key=lambda p: (p['order'], p['title'].lower(), p['url']))  # the URL breaks ties
        for (sk, slug), p in self.pages.items():
            seen, cur = set(), p
            while cur['slug'] != 'index':
                if cur['slug'] in seen:
                    self.error(f'{p["src"]}: the parent chain loops back to {cur["slug"]}')
                    break
                seen.add(cur['slug'])
                cur = self.pages[(sk, cur['parent'])]

    def ancestors(self, p):
        out, cur = [], p
        while cur['slug'] != 'index':
            cur = self.pages[(cur['space'], cur['parent'])]
            out.append(cur)
        return list(reversed(out))

    # ----- decision records and RFCs -----
    def decisions(self):
        adrs = sorted((p for p in self.pages.values() if p.get('adr')), key=lambda p: (int(p['adr']), p['url']))
        rfcs = sorted((p for p in self.pages.values() if p.get('rfc')), key=lambda p: (int(p['rfc']), p['url']))
        for kind, recs in (('ADR', adrs), ('RFC', rfcs)):
            by_num = {}
            for p in recs:
                by_num.setdefault(int(p[kind.lower()]), []).append(p['src'])
            for n, srcs in sorted(by_num.items()):
                if len(srcs) > 1:
                    self.error(f'{kind}-{n:04d} is used by more than one page: {", ".join(srcs)}')
        for p in adrs:
            for old in split_list(p.get('supersedes')):
                o = self.pages.get((p['space'], old))
                if not o or not o.get('adr'):
                    self.error(f'{p["src"]}: supersedes {old}, but {p["space"]}/{old} is not a decision record')
                elif p['slug'] not in split_list(o.get('superseded_by')) or o.get('status') != 'superseded':
                    self.error(f'{p["src"]}: supersedes {old}, but {o["src"]} is not marked superseded by {p["slug"]}')
            succ = split_list(p.get('superseded_by'))
            if p.get('status') == 'superseded' and not succ:
                self.error(f'{p["src"]}: status superseded needs superseded_by')
            if succ and p.get('status') != 'superseded':
                self.error(f'{p["src"]}: superseded_by is set, so status must be superseded')
            for s in succ:
                n = self.pages.get((p['space'], s))
                if not n or p['slug'] not in split_list(n.get('supersedes')):
                    self.error(f'{p["src"]}: superseded_by {s}, but that record does not list {p["slug"]} under supersedes')
        self.checkpoint()
        adr_mark = re.compile(r'^<!-- adr-index -->$', re.M)  # on a line of its own; a mention in running text stays
        rfc_mark = re.compile(r'^<!-- rfc-index -->$', re.M)
        adr_ref = lambda a: f'[ADR-{int(a["adr"]):04d}](doc:{a["space"]}/{a["slug"]})'
        for p in self.pages.values():
            if adr_mark.search(p['body']):
                rows = ['| Record | Decision | Date | Status |', '|---|---|---|---|']
                for a in sorted(adrs, key=lambda a: -int(a['adr'])):
                    st = a['status']
                    if st == 'superseded':
                        st = 'superseded by ' + ', '.join(adr_ref(self.pages[(a['space'], s)]) for s in split_list(a['superseded_by']))
                    rows.append(f'| {adr_ref(a)} | {cell(short_title(a))} | {a["created"]} | {st} |')
                table = '\n'.join(rows) if adrs else 'No decision records yet.'
                p['body'] = adr_mark.sub(lambda m: table, p['body'])
            if rfc_mark.search(p['body']):
                rows = ['| RFC | Title | Status | Comments close | Decision |', '|---|---|---|---|---|']
                for r in sorted(rfcs, key=lambda r: -int(r['rfc'])):
                    rows.append(f'| [RFC-{int(r["rfc"]):04d}](doc:{r["space"]}/{r["slug"]}) | {cell(short_title(r))} | {r["status"]} '
                                f'| {r.get("comments_close", "")} | {self.decision_ref(r)} |')
                table = '\n'.join(rows) if rfcs else 'No RFCs yet.'
                p['body'] = rfc_mark.sub(lambda m: table, p['body'])

    def decision_page(self, r):
        """The page the decision field of an RFC names: a slug in the same space or space/slug. None for plain text."""
        key = re.sub(r'^doc:', '', re.sub(r'\.md$', '', r.get('decision', '').strip()))
        return self.pages.get(tuple(key.split('/', 1))) if '/' in key else self.pages.get((r['space'], key))

    def decision_ref(self, r):
        """The decision cell of the RFC index: a link when the field names a page, else the text."""
        t = self.decision_page(r)
        if t:
            label = f'ADR-{int(t["adr"]):04d}' if t.get('adr') else cell(t['title'])
            return f'[{label}](doc:{t["space"]}/{t["slug"]})'
        return cell(r.get('decision', '').strip())

    # ----- markdown -----
    def resolve_href(self, url, ctx):
        url = url.strip()
        if url.startswith('doc:'):
            target, _, frag = url[4:].partition('#')
            sk, _, slug = target.strip().strip('/').partition('/')
            t = self.pages.get((sk, slug or 'index'))
            if not t:
                self.error(f'{ctx.page["src"]}: unknown doc link {url}')
                return '#'
            ctx.out_links.add(t['url'])
            return t['url'] + (f'#{slugify(frag)}' if frag else '')
        if url.startswith('#'):
            return '#' + slugify(url[1:])
        if url.startswith('/') or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', url):
            return url
        path, _, frag = url.partition('#')
        if path.endswith('.md'):  # a relative link to another source file, as an editor writes it
            try:
                target = (self.src / ctx.page['space'] / path).resolve().relative_to(self.src.resolve()).parts
            except ValueError:
                target = ()
            t = self.pages.get((target[0], target[1][:-3])) if len(target) == 2 else None
            if t:
                ctx.out_links.add(t['url'])
                return t['url'] + (f'#{slugify(frag)}' if frag else '')
            self.warn(f'{ctx.page["src"]}: link {url} does not name a page; use doc:<space>/<slug>')
        return url

    def inline(self, s, ctx):
        stash = []

        def keep(h):
            stash.append(h)
            return f'\x00{len(stash) - 1}\x00'
        s = re.sub(r'`([^`]+)`', lambda m: keep(f'<code>{esc(m.group(1))}</code>'), s)
        s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', lambda m: keep(f'<img src="{esc(m.group(2))}" alt="{esc(m.group(1))}" loading="lazy">'), s)

        def mdlink(m):
            text, url = m.group(1), m.group(2).split(' "')[0]
            return keep(f'<a href="{esc(self.resolve_href(url, ctx))}">{self.inline(text, ctx)}</a>')
        s = re.sub(r'\[([^\]]+)\]\(([^)\s]+(?: "[^"]*")?)\)', mdlink, s)
        s = re.sub(r'<(https?://[^>\s]+)>', lambda m: keep(f'<a href="{esc(m.group(1))}">{esc(m.group(1))}</a>'), s)
        s = re.sub(r'(?<![("=\w])(https?://[^\s<>()\]]+[^\s<>()\].,;:!?\'"])', lambda m: keep(f'<a href="{esc(m.group(1))}">{esc(m.group(1))}</a>'), s)
        s = html.escape(s, quote=False)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'__(.+?)__', r'<strong>\1</strong>', s)
        s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
        s = re.sub(r'(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])', r'<em>\1</em>', s)
        s = re.sub(r'~~(.+?)~~', r'<del>\1</del>', s)
        while '\x00' in s:
            s = re.sub(r'\x00(\d+)\x00', lambda m: stash[int(m.group(1))], s)
        return s

    def render(self, md, ctx, toc):
        lines = md.replace('\t', '    ').split('\n')
        out, i, n = [], 0, len(lines)
        para = []

        def flush():
            if para:
                out.append('<p>' + self.inline(' '.join(x.strip() for x in para), ctx) + '</p>')
                para.clear()

        while i < n:
            line = lines[i]
            st = line.strip()
            m = re.match(r'^\s*(```|~~~)\s*([\w+-]*)', line)
            if m:
                flush()
                fence, lang, buf = m.group(1), m.group(2), []
                i += 1
                while i < n and not lines[i].strip().startswith(fence):
                    buf.append(lines[i])
                    i += 1
                i += 1
                cls = f' class="lang-{esc(lang)}"' if lang else ''
                out.append(f'<pre><code{cls}>' + html.escape('\n'.join(buf)) + '</code></pre>')
                continue
            if st.startswith('<!--'):  # comments are not published
                flush()
                while i < n and '-->' not in lines[i]:
                    i += 1
                i += 1
                continue
            if not st:
                flush()
                i += 1
                continue
            m = re.match(r'^(#{1,6})\s+(.*?)\s*#*$', st)
            if m:
                flush()
                lvl = len(m.group(1))
                text = self.inline(m.group(2), ctx)
                hid = base = slugify(text)
                k = 2
                while hid in ctx.ids:
                    hid = f'{base}-{k}'
                    k += 1
                ctx.ids.add(hid)
                tag = min(max(lvl, 2), 4)  # the page title is the only h1
                if lvl <= 3:
                    toc.append((min(max(lvl, 2), 3), hid, re.sub(r'<[^>]+>', '', text)))
                out.append(f'<h{tag} id="{hid}">{text}</h{tag}>')
                i += 1
                continue
            if re.match(r'^(\*\s*\*\s*\*|-\s*-\s*-|_\s*_\s*_)[\s*_-]*$', st):
                flush()
                out.append('<hr>')
                i += 1
                continue
            if st.startswith('|') and i + 1 < n and re.match(r'^\s*\|?\s*:?-{2,}', lines[i + 1]):
                flush()

                def cells(row):
                    return [c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', row.strip().strip('|'))]
                head = cells(lines[i])
                i += 2
                rows = []
                while i < n and lines[i].strip().startswith('|'):
                    rows.append(cells(lines[i]))
                    i += 1
                t = '<div class="tbl"><table><thead><tr>' + ''.join(f'<th>{self.inline(c, ctx)}</th>' for c in head) + '</tr></thead><tbody>'
                for r in rows:
                    t += '<tr>' + ''.join(f'<td>{self.inline(c, ctx)}</td>' for c in r) + '</tr>'
                out.append(t + '</tbody></table></div>')
                continue
            if st.startswith('>'):
                flush()
                buf = []
                while i < n and lines[i].strip().startswith('>'):
                    buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                    i += 1
                m = re.match(r'^\[!(\w+)\][+-]?\s*(.*)$', buf[0].strip())
                if m:
                    kind = PANEL.get(m.group(1).lower(), 'note')
                    title = m.group(2)
                    inner = self.render('\n'.join(buf[1:]), ctx, []) if len(buf) > 1 else ''
                    if title and not inner:
                        inner, title = '<p>' + self.inline(title, ctx) + '</p>', ''
                    head = f'<div class="panel-title">{self.inline(title, ctx)}</div>' if title else ''
                    out.append(f'<div class="panel panel-{kind}">{head}{inner}</div>')
                else:
                    out.append('<blockquote>' + self.render('\n'.join(buf), ctx, []) + '</blockquote>')
                continue
            if LIST_ITEM.match(line):
                flush()
                block = []
                while i < n and (LIST_ITEM.match(lines[i]) or (lines[i].startswith('  ') and lines[i].strip() and block)):
                    block.append(lines[i])
                    i += 1
                out.append(self.render_list(block, ctx))
                continue
            para.append(line)
            i += 1
        flush()
        return '\n'.join(out)

    def render_list(self, block, ctx):
        items = []  # [indent, ordered, text]
        for ln in block:
            m = re.match(r'^(\s*)([-*+]|\d+[.)])\s+(.*)$', ln)
            if m:
                items.append([len(m.group(1)), m.group(2)[0].isdigit(), m.group(3)])
            elif items:
                items[-1][2] += ' ' + ln.strip()

        def build(idx, indent):
            tag = 'ol' if items[idx][1] else 'ul'
            h = f'<{tag}>'
            while idx < len(items) and items[idx][0] >= indent:
                ind, _, text = items[idx]
                if ind > indent:
                    sub, idx = build(idx, ind)
                    h = h[:-5] + sub + '</li>' if h.endswith('</li>') else h + sub
                    continue
                m = re.match(r'^\[([ xX])\]\s+(.*)$', text)
                if m:
                    box = '☑' if m.group(1).lower() == 'x' else '☐'
                    h += f'<li class="task"><span class="box">{box}</span> {self.inline(m.group(2), ctx)}</li>'
                else:
                    h += f'<li>{self.inline(text, ctx)}</li>'
                idx += 1
            return h + f'</{tag}>', idx

        out, idx = '', 0
        while idx < len(items):
            part, idx = build(idx, items[idx][0])
            out += part
        return out

    def render_all(self):
        for p in self.pages.values():
            ctx = Ctx(p)
            toc = []
            p['html'] = self.render(p['body'], ctx, toc)
            p['toc'] = toc
            p['out_links'] = ctx.out_links - {p['url']}
            p['words'] = len(text_of(p['html']).split())
        self.backlinks = {}
        for p in self.pages.values():
            for u in p['out_links']:
                self.backlinks.setdefault(u, set()).add((p['space'], p['slug']))

    # ----- review state -----
    def review_state(self, p):
        """overdue, soon, not-reviewed or ok."""
        rv, rb = p.get('reviewed', ''), p.get('review_by', '')
        if rb and rb < self.today:
            return 'overdue'
        if not is_date(rv):
            return 'not-reviewed'
        if rb and rb <= self.soon:
            return 'soon'
        return 'ok'

    def reasons(self, p):
        out = []
        st = self.review_state(p)
        if st == 'overdue':
            out.append(f'review overdue since {p["review_by"]}')
        elif st == 'soon':
            out.append(f'review due {p["review_by"]}')
        if not is_date(p.get('reviewed', '')):
            out.append('not reviewed')
        out += [f'missing {k}' for k in ('owner', 'type') if not p.get(k)]
        if p.get('review_by_default'):
            out.append('missing review_by')
        return out

    # ----- HTML -----
    def head(self, title, desc, url, extra=''):
        canon = f'<link rel="canonical" href="{esc(self.base + url)}">\n' if self.base else ''
        return (f'<!doctype html>\n<html lang="{esc(self.cfg["lang"])}">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                f'<title>{esc(title)}</title>\n<meta name="description" content="{esc(desc)}">\n{canon}{extra}'
                f'<meta name="generator" content="build_docs.py">\n<style>{CSS}</style>\n</head>')

    def tree_html(self, current):
        open_set = {(a['space'], a['slug']) for a in self.ancestors(current)} | {(current['space'], current['slug'])}

        def walk(key):
            kids = self.children.get(key, [])
            if not kids:
                return ''
            h = '<ul>'
            for c in kids:
                ck = (c['space'], c['slug'])
                cur = ' aria-current="page"' if ck == (current['space'], current['slug']) else ''
                link = f'<a href="{c["url"]}"{cur}>{esc(c["title"])}</a>'
                sub = walk(ck)
                if sub:
                    h += f'<li><details{" open" if ck in open_set else ""}><summary>{link}</summary>{sub}</details></li>'
                else:
                    h += f'<li class="leaf">{link}</li>'
            return h + '</ul>'
        return walk((current['space'], 'index'))

    def crumbs(self, p):
        sp = self.space[p['space']]
        h = f'<nav class="crumbs" aria-label="Breadcrumbs"><a href="{self.prefix}">{esc(self.cfg["title"])}</a>'
        if p['slug'] != 'index':
            h += f'<a href="{self.prefix}{sp["key"]}/">{esc(sp["name"])}</a>'
            h += ''.join(f'<a href="{a["url"]}">{esc(a["title"])}</a>' for a in self.ancestors(p) if a['slug'] != 'index')
        return h + '</nav>'

    def recent(self, pool, k):
        rows = sorted(pool, key=lambda p: (p['updated'], p['title'], p['url']), reverse=True)[:k]
        return '<ul class="recent">' + ''.join(
            f'<li><a href="{r["url"]}">{esc(r["title"])}</a><span>{esc(self.space[r["space"]]["name"])}, updated {r["updated"]}</span></li>'
            for r in rows) + '</ul>'

    def byline(self, p):
        by = []
        if p.get('adr') or p.get('rfc'):
            by.append(f'<span class="st st-{esc(p["status"])}">{esc(p["status"])}</span>')
        by.append(f'<span>owner {esc(p["owner"])}</span>' if p.get('owner') else '<span class="late">no owner</span>')
        by.append(f'<span>created {p["created"]}</span><span>updated {p["updated"]}</span>')
        rv, rb, st = p.get('reviewed', ''), p.get('review_by', ''), self.review_state(p)
        if is_date(rv):
            by.append(f'<span>reviewed {rv}</span>')
        else:
            by.append('<span class="no">not reviewed</span>')
        if st == 'overdue':
            by.append(f'<span class="late">review overdue since {rb}</span>')
        elif rb:
            by.append(f'<span>review by {rb}</span>')
        if p.get('rfc') and p.get('comments_close'):
            by.append(f'<span>comments close {p["comments_close"]}</span>')
        if p.get('type'):
            by.append(f'<span class="chip">{esc(p["type"])}</span>')
        by.append(f'<span>{max(1, round(p["words"] / 220))} min read</span>')
        return '<div class="byline">' + ''.join(by) + '</div>'

    def panels(self, p):
        out = ''
        link = lambda q: f'<a href="{q["url"]}">{esc(q["title"])}</a>'
        if p.get('adr') and p.get('status') == 'superseded':
            out += '<div class="panel panel-warning"><p>Superseded by ' + ', '.join(
                link(self.pages[(p['space'], s)]) for s in split_list(p['superseded_by'])) + '. Kept for the history.</p></div>'
        olds = [self.pages[(p['space'], x)] for x in split_list(p.get('supersedes'))] if p.get('adr') else []
        if olds:
            out += '<div class="panel panel-info"><p>Supersedes ' + ', '.join(link(o) for o in olds) + '.</p></div>'
        if p.get('rfc') and p.get('decision'):
            t = self.decision_page(p)
            out += f'<div class="panel panel-info"><p>Decision: {link(t) if t else esc(p["decision"])}.</p></div>'
        if p.get('reviewed') == 'no':
            out += '<div class="panel panel-note"><p>Not reviewed against the system it describes. Check the facts before you rely on them.</p></div>'
        return out

    def page_html(self, p):
        sp = self.space[p['space']]
        is_home = p['slug'] == 'index'
        title = f'{sp["name"]} · {self.cfg["title"]}' if is_home else f'{p["title"]} · {sp["name"]} · {self.cfg["title"]}'
        extra = f'<meta name="docs-space" content="{esc(sp["key"])}">\n'
        extra += ''.join(f'<meta name="docs-{k.replace("_", "-")}" content="{esc(p[k])}">\n' for k in REVIEW_FIELDS if p.get(k))
        if p['labels']:
            extra += f'<meta name="keywords" content="{esc(", ".join(p["labels"]))}">\n'
        if not is_home:
            extra += f'<link rel="up" href="{self.pages[(p["space"], p["parent"])]["url"]}">\n'
        labels = ''
        if p['labels']:
            labels = '<div class="labels" aria-label="Labels">' + ''.join(f'<span class="chip">{esc(l)}</span>' for l in p['labels']) + '</div>'
        kids = self.children.get((p['space'], p['slug']), [])
        child = ''
        if kids:
            child = '<nav class="children" aria-label="Child pages"><h2>Child pages</h2><ul>' + ''.join(
                f'<li><a href="{c["url"]}">{esc(c["title"])}</a><span>{esc(c["summary"])}</span></li>' for c in kids) + '</ul></nav>'
        bl = sorted((self.pages[k] for k in self.backlinks.get(p['url'], set())), key=lambda x: (x['title'].lower(), x['url']))
        back = ''
        if bl:
            back = '<nav class="backlinks" aria-label="Linked from"><h2>Linked from</h2><ul>' + ''.join(
                f'<li><a href="{b["url"]}">{esc(b["title"])}</a><span>{esc(self.space[b["space"]]["name"])}</span></li>' for b in bl) + '</ul></nav>'
        toc = ''
        if len(p['toc']) >= 2:
            toc = '<nav class="toc" aria-label="On this page"><div class="toc-h">On this page</div><ul>' + ''.join(
                f'<li class="l{lv}"><a href="#{hid}">{esc(t)}</a></li>' for lv, hid, t in p['toc']) + '</ul></nav>'
        home_extra = ''
        if is_home:
            pool = [q for q in self.pages.values() if q['space'] == p['space'] and q['slug'] != 'index']
            if pool:
                home_extra = f'<section><h2>Recently updated in this space</h2>{self.recent(pool, 6)}</section>'
        side = (f'<nav class="side" aria-label="Pages in {esc(sp["name"])}"><a class="space-head" href="{self.prefix}{sp["key"]}/">'
                f'{esc(sp["name"])}</a>{self.tree_html(p)}</nav>')
        return f'''{self.head(title, p["summary"], p["url"], extra)}
<body>
<div class="layout">
{side}
<main id="main">
{self.crumbs(p)}
<h1>{esc(sp["name"] if is_home else p["title"])}</h1>
{self.byline(p)}
{self.panels(p)}
<article class="doc">
{p["html"]}
</article>
{home_extra}
{child}
{labels}
{back}
<p class="page-note">Source: <code>{esc(p["src"])}</code></p>
</main>
{toc}
</div>
</body>
</html>
'''

    def present(self):
        return [s for s in self.spaces if (s['key'], 'index') in self.pages]

    def docs_home(self):
        cards = ''
        for s in self.present():
            ps = [p for p in self.pages.values() if p['space'] == s['key']]
            owner = f'<span>owner {esc(s["owner"])}</span>' if s.get('owner') else ''
            cards += (f'<a class="space-card" href="{self.prefix}{s["key"]}/"><b>{esc(s["name"])}</b><span>{esc(s["about"])}</span>'
                      f'{owner}<span>{count(len(ps), "page")}, updated {max(p["updated"] for p in ps)}</span></a>')
        links = sum(len(p['out_links']) for p in self.pages.values())
        newest = max(p['updated'] for p in self.pages.values())
        desc = f'{self.cfg["title"]}: {count(len(self.pages), "page")} in {count(len(self.present()), "space")}.'
        return f'''{self.head(self.cfg["title"], desc, self.prefix)}
<body>
<div class="layout wide">
<main id="main">
<h1>{esc(self.cfg["title"])}</h1>
<p class="lede">{count(len(self.pages), 'page')} in {count(len(self.present()), 'space')}, {count(links, 'link')} between them, last updated {newest}. Owners, review dates and types: <a href="{self.prefix}health/">Docs health</a>.</p>
<section class="spaces">{cards}</section>
<section><h2>Recently updated</h2>{self.recent(self.pages.values(), 12)}</section>
</main>
</div>
</body>
</html>
'''

    def health_page(self):
        allp = sorted(self.pages.values(), key=lambda p: (p['space'], p['title'].lower(), p['url']))
        overdue = sorted((p for p in allp if self.review_state(p) == 'overdue'), key=lambda p: (p['review_by'], p['url']))
        soon = sorted((p for p in allp if self.review_state(p) == 'soon'), key=lambda p: (p['review_by'], p['url']))
        not_rev = [p for p in allp if not is_date(p.get('reviewed', ''))]
        no_owner = [p for p in allp if not p.get('owner')]
        no_type = [p for p in allp if not p.get('type')]

        def table(rows, cols):
            if not rows:
                return '<p class="lede">None.</p>'
            h = '<div class="tbl"><table><thead><tr>' + ''.join(f'<th>{c}</th>' for c, _ in cols) + '</tr></thead><tbody>'
            for p in rows:
                h += '<tr>' + ''.join(f'<td>{f(p)}</td>' for _, f in cols) + '</tr>'
            return h + '</tbody></table></div>'
        link = lambda p: f'<a href="{p["url"]}">{esc(p["title"])}</a>'
        spn = lambda p: esc(self.space[p['space']]['name'])
        own = lambda p: esc(p.get('owner', ''))
        sp_own = lambda p: esc(self.space[p['space']].get('owner', ''))
        cols_review = [('Page', link), ('Space', spn), ('Owner', own), ('Reviewed', lambda p: esc(p.get('reviewed', ''))),
                       ('Review by', lambda p: p['review_by'])]
        by_space = ''
        for sp in self.present():
            ps = [p for p in allp if p['space'] == sp['key']]
            states = [self.review_state(p) for p in ps]
            nr = sum(1 for p in ps if not is_date(p.get('reviewed', '')))
            by_space += (f'<tr><td><a href="{self.prefix}{sp["key"]}/">{esc(sp["name"])}</a></td><td>{esc(sp.get("owner", ""))}</td>'
                         f'<td>{len(ps)}</td><td>{len(ps) - nr}</td><td>{nr}</td><td>{states.count("overdue")}</td>'
                         f'<td>{states.count("soon")}</td><td>{sum(1 for p in ps if p.get("owner"))}</td><td>{sum(1 for p in ps if p.get("type"))}</td></tr>')
        desc = f'Docs health: owners, types and review dates of {count(len(allp), "page")}, and the pages past review.'
        url = self.prefix + 'health/'
        return f'''{self.head('Docs health · ' + self.cfg["title"], desc, url)}
<body>
<div class="layout wide">
<main id="main">
<nav class="crumbs" aria-label="Breadcrumbs"><a href="{self.prefix}">{esc(self.cfg["title"])}</a></nav>
<h1>Docs health</h1>
<div class="byline"><span>built {self.today}</span><span>{count(len(allp), 'page')}</span></div>
<p class="lede">Each page names an owner, the date of its last review, the date of its next review and a type (tutorial, how-to, reference or explanation, after Diátaxis). This page lists what is missing or late. Past the review date: {len(overdue)}. Due in the next {SOON_DAYS} days: {len(soon)}. Not reviewed: {len(not_rev)}. Without an owner: {len(no_owner)}. Without a type: {len(no_type)}.</p>
<article class="doc">
<h2 id="overdue">Past the review date</h2>
{table(overdue, cols_review)}
<h2 id="soon">Due in the next {SOON_DAYS} days</h2>
{table(soon, cols_review)}
<h2 id="not-reviewed">Not reviewed</h2>
{table(not_rev, [('Page', link), ('Space', spn), ('Owner', own)])}
<h2 id="no-owner">Without an owner</h2>
{table(no_owner, [('Page', link), ('Space', spn), ('Space owner', sp_own)])}
<h2 id="no-type">Without a type</h2>
{table(no_type, [('Page', link), ('Space', spn), ('Owner', own)])}
<h2 id="spaces">By space</h2>
<div class="tbl"><table><thead><tr><th>Space</th><th>Space owner</th><th>Pages</th><th>Reviewed</th><th>Not reviewed</th><th>Overdue</th><th>Due soon</th><th>With owner</th><th>With type</th></tr></thead><tbody>{by_space}</tbody></table></div>
<h2 id="fields">The fields</h2>
<p>In the front matter of each source file: <code>owner</code> (who keeps the page true), <code>reviewed</code> (the date the page was last checked against the system it describes, or <code>no</code>), <code>review_by</code> (the date of the next check; {self.interval} days after the review by default) and <code>type</code>. A page written from the system it describes counts as reviewed on the day it was written.</p>
</article>
</main>
</div>
</body>
</html>
'''

    def assemble(self):
        def put(url, text):
            self.files[url[len(self.prefix):] + 'index.html'] = text
        for p in self.pages.values():
            put(p['url'], self.page_html(p))
        put(self.prefix, self.docs_home())
        put(self.prefix + 'health/', self.health_page())
        index = [{'title': p['title'], 'url': p['url'], 'space': p['space'], 'summary': p['summary'], 'labels': p['labels'],
                  'type': p.get('type', ''), 'owner': p.get('owner', ''), 'updated': p['updated'], 'text': text_of(p['html'])[:400]}
                 for p in sorted(self.pages.values(), key=lambda p: p['url'])]
        spaces = {s['key']: {'name': s['name'], 'url': self.prefix + s['key'] + '/'} for s in self.present()}
        self.files['search.json'] = json.dumps({'title': self.cfg['title'], 'spaces': spaces, 'pages': index}, ensure_ascii=False, separators=(',', ':'))

    def write(self):
        for k in [s['key'] for s in self.spaces] + ['health']:
            if (self.out / k).is_dir():
                shutil.rmtree(self.out / k)
        for rel, text in self.files.items():
            t = self.out / rel
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(text, encoding='utf-8')

    def stale_report(self):
        groups = {}
        for p in sorted(self.pages.values(), key=lambda p: p['src']):
            r = self.reasons(p)
            if r:
                groups.setdefault(p.get('owner') or '', []).append((p, r))
        if not groups:
            return 'No page needs a review.'
        lines = []
        for owner in sorted(groups, key=lambda o: (o == '', o.lower())):
            rows = groups[owner]
            lines.append(f'{owner or "no owner"} ({len(rows)})')
            lines += [f'  {p["src"]}: {"; ".join(r)}' for p, r in rows]
        return '\n'.join(lines)


CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#1d2026;--soft:#454b55;--dim:#68707c;--line:#dde1e6;--panel:#f4f6f8;--code:#eef1f4;--accent:#1d5fbf;--late:#b42318;--warn:#8a5a00;--ok:#1d7a46}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#e5e7ea;--soft:#bcc1c8;--dim:#8d949e;--line:#2d313a;--panel:#1b1e24;--code:#20242b;--accent:#80aaff;--late:#ff8a80;--warn:#e6c15c;--ok:#6fd39a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}
.layout{display:grid;grid-template-columns:240px minmax(0,760px) 200px;gap:0 32px;max-width:1320px;margin:0 auto;padding:0 16px}
.layout.wide{grid-template-columns:minmax(0,1000px);justify-content:center}
main{min-width:0;padding:24px 0 48px}
.side,.toc{position:sticky;top:0;align-self:start;max-height:100vh;overflow:auto;padding:24px 0;font-size:14px}
.side ul,.toc ul{list-style:none;margin:0;padding:0}
.side ul ul{padding-left:12px;margin-left:6px;border-left:1px solid var(--line)}
.side a,.toc a{display:block;padding:3px 6px;border-radius:4px;color:var(--soft);text-decoration:none}
.side a:hover,.toc a:hover{background:var(--panel);color:var(--fg)}
.side a[aria-current="page"]{color:var(--accent);font-weight:600}
.side summary{cursor:pointer}.side summary a{display:inline}
.side li.leaf{padding-left:14px}
.side .space-head{font-weight:700;color:var(--fg);margin-bottom:8px}
.toc-h{font-weight:600;color:var(--dim);margin-bottom:6px}.toc .l3{padding-left:12px}
.crumbs{font-size:13px;margin-bottom:8px}.crumbs a{color:var(--dim);text-decoration:none}
.crumbs a+a::before{content:"/";margin:0 6px;color:var(--line)}
h1{font-size:32px;line-height:1.2;margin:0 0 8px}h2{font-size:22px;margin:32px 0 8px}h3{font-size:18px;margin:24px 0 6px}h4{font-size:16px}
.byline{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--dim);margin-bottom:20px}
.late{color:var(--late);font-weight:600}.no{color:var(--warn);font-weight:600}
.chip{border:1px solid var(--line);border-radius:999px;padding:0 8px;font-size:13px}
.st{font-weight:600;text-transform:uppercase;letter-spacing:.04em}.st-accepted{color:var(--ok)}
.st-proposed,.st-draft,.st-review{color:var(--warn)}.st-rejected,.st-deprecated,.st-superseded,.st-withdrawn{color:var(--dim)}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
code{background:var(--code);padding:1px 4px;border-radius:4px;font-size:.9em}
pre{background:var(--code);padding:12px 14px;border-radius:6px;overflow:auto;font-size:14px}pre code{background:none;padding:0}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:15px;margin:12px 0}
th,td{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}th{font-weight:600}
blockquote{margin:12px 0;padding:2px 16px;border-left:3px solid var(--line);color:var(--soft)}
.panel{margin:14px 0;padding:8px 16px;border-left:4px solid var(--accent);border-radius:4px;background:var(--panel)}
.panel-tip{border-color:var(--ok)}.panel-warning{border-color:var(--late)}.panel-info{border-color:var(--dim)}.panel-title{font-weight:600;margin-top:6px}
li.task{list-style:none}li.task .box{margin-left:-1.2em}
img{max-width:100%}
.children ul,.backlinks ul,.recent{list-style:none;padding:0}
.children li,.backlinks li,.recent li{padding:6px 0;border-bottom:1px solid var(--line)}
.children li span,.backlinks li span,.recent li span{display:block;color:var(--dim);font-size:14px}
.labels{display:flex;flex-wrap:wrap;gap:6px;margin:20px 0}
.lede{color:var(--soft)}
.spaces{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin:20px 0}
.space-card{display:block;padding:14px 16px;border:1px solid var(--line);border-radius:8px;color:var(--fg);text-decoration:none}
.space-card:hover{border-color:var(--accent)}.space-card span{display:block;color:var(--dim);font-size:14px}
.page-note{margin-top:40px;font-size:13px;color:var(--dim)}
@media (max-width:1100px){.layout{grid-template-columns:220px minmax(0,1fr)}.toc{display:none}}
@media (max-width:760px){.layout{grid-template-columns:minmax(0,1fr)}.side{position:static;max-height:none;padding:12px 0;border-bottom:1px solid var(--line)}}
""".strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build the docs site from docs/<space>/<slug>.md.')
    ap.add_argument('--config', default='docs/docs.json', help='config file; a relative path starts at the repository root')
    ap.add_argument('--check', action='store_true', help='parse, validate and render in memory, write nothing, exit 1 on errors')
    ap.add_argument('--stale', action='store_true', help='list the pages that need a review, grouped by owner, write nothing')
    ap.add_argument('--today', default=None, help='use this date as today (YYYY-MM-DD)')
    args = ap.parse_args(argv)
    try:
        today = args.today or datetime.date.today().isoformat()
        if not is_date(today):
            raise ConfigError('--today must be a date, YYYY-MM-DD')
        cfg_path = Path(args.config)
        cfg_path = (cfg_path if cfg_path.is_absolute() else ROOT / cfg_path).resolve()
        cfg = load_config(cfg_path)
        out = Path(cfg['out'])
        site = Site(cfg, cfg_path.parent, (out if out.is_absolute() else ROOT / out).resolve(), today)
        site.build()
    except ConfigError as e:
        print(f'build_docs: config error: {e}', file=sys.stderr)
        return 2
    except Stop:
        for w in site.warnings:
            print(f'warning: {w}', file=sys.stderr)
        for e in site.errors:
            print(f'error: {e}', file=sys.stderr)
        print(f'build_docs: {count(len(site.errors), "error")}; nothing written', file=sys.stderr)
        return 1
    for w in site.warnings:
        print(f'warning: {w}', file=sys.stderr)
    links = sum(len(p['out_links']) for p in site.pages.values())
    summary = (f'{count(len(site.pages), "page")} in {count(len(site.present()), "space")}, {count(links, "link")}, '
               f'{count(len(site.warnings), "warning")}')
    if args.stale:
        print(site.stale_report())
        return 0
    if args.check:
        print(f'build_docs: check passed: {summary}; nothing written')
        return 0
    site.write()
    print(f'build_docs: {summary}; wrote {len(site.files)} files to {site.rel(site.out)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
