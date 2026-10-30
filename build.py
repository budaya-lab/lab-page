"""Build the site to plain HTML without Ruby/Jekyll.

Usage:  python build.py            (writes to _html/)
        python build.py SRC OUT
In Jupyter:  %run build.py
Needs: pip install pyyaml jinja2 markdown
Output uses relative links, so it can be opened from disk or uploaded to any web host.
"""
import re, sys, os, csv, shutil, glob, datetime, yaml, markdown, jinja2

SRC, OUT = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else (os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "_html"))
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
cfg = yaml.safe_load(open(f"{SRC}/_config.yml"))

def split_fm(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    return (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, text)

def conv_filters(expr):
    parts = [p.strip() for p in re.split(r"\|(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)", expr)]
    out = parts[0].replace(".size", "|length")
    out = re.sub(r"(\S+) contains (\S+)", r"(\2 in \1)", out)
    for f in parts[1:]:
        if ":" in f and not f.startswith("'"):
            name, args = f.split(":", 1); out += f"|{name.strip()}({args.strip()})"
        else:
            out += f"|{f}"
    return out

def liquid2jinja(t):
    t = re.sub(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", "", t, flags=re.S)
    t = re.sub(r"{{(.*?)}}", lambda m: "{{ " + conv_filters(m.group(1).strip()) + " }}", t)
    def tag(m):
        s = m.group(1).strip()
        if s.startswith("assign "):
            n, e = s[7:].split("=", 1); return "{% set " + n.strip() + " = " + conv_filters(e.strip()) + " %}"
        if s.startswith("include "):
            bits = s[8:].split(None, 1); f = bits[0]
            kv = re.findall(r"(\w+)=(\S+)", bits[1] if len(bits) > 1 else "")
            d = ", ".join(f"'{k}': {conv_filters(v)}" for k, v in kv)
            return "{% with include={" + d + "} %}{% include '" + f + "' %}{% endwith %}"
        if s.startswith("for "):
            m2 = re.match(r"for (\w+) in (.+?)(?: limit: ?(\d+))?$", s)
            v, coll, lim = m2.groups()
            coll = conv_filters(coll)
            if "include.links" in coll: coll += "|dictitems"
            return "{% for " + v + " in (" + coll + ")" + (f"[:{lim}]" if lim else "") + " %}"
        if s.startswith("if ") or s.startswith("elsif "):
            kw, cond = s.split(" ", 1)
            cond = re.sub(r"(\S+) contains (\S+)", r"(\2 in \1)", cond).replace(".size", "|length")
            return "{% " + ("elif" if kw == "elsif" else "if") + " " + cond + " %}"
        return "{% " + s + " %}"
    return re.sub(r"{%-?(.*?)-?%}", tag, t, flags=re.S)

def where(seq, k, v): return [x for x in seq if x.get(k) == v]
def group_by(seq, k):
    g = {}
    for x in seq: g.setdefault(x.get(k), []).append(x)
    from types import SimpleNamespace as N; return [N(name=n, items=i, get=lambda k, n=n: n) for n, i in g.items()]
def sortf(seq, k=None):
    return sorted(seq, key=lambda x: (x.get(k) is None, str(x.get(k)) if k else x)) if k else sorted(seq)
def datef(d, fmt):
    if isinstance(d, str): d = datetime.date.fromisoformat(d)
    return d.strftime(fmt)
def mdify(s): return markdown.markdown(str(s))
def rel(u): return (cfg.get("baseurl") or "") + ("" if str(u).startswith("/") else "/") + str(u)
def ruby_split(s, d):  # Ruby drops trailing empty fields: "a;b;".split(";") == ["a", "b"]
    parts = str(s or "").split(d)
    while parts and parts[-1] == "": parts.pop()
    return parts

class Loader(jinja2.BaseLoader):
    def get_source(self, env, name):
        p = f"{SRC}/_includes/{name}"
        return liquid2jinja(open(p).read()), p, lambda: True

env = jinja2.Environment(loader=Loader(), undefined=jinja2.ChainableUndefined, autoescape=False)
env.filters.update(where=where, group_by=group_by, sort=sortf, reverse=lambda s: list(reversed(list(s))),
    join=lambda s, j: j.join(map(str, s)), split=ruby_split, strip=lambda s: str(s or "").strip(), slice=lambda s, i: s[i:i+1],
    remove=lambda s, r: str(s).replace(r, ""), strip_newlines=lambda s: str(s).replace("\n", ""),
    relative_url=rel, date=datef, markdownify=mdify, dictitems=lambda d: list((d or {}).items()))
env.filters["default"] = lambda v, d: v if v else d

data = {os.path.basename(f)[:-4]: yaml.safe_load(open(f)) for f in glob.glob(f"{SRC}/_data/*.yml")}
data.update({os.path.basename(f)[:-4]: list(csv.DictReader(open(f, encoding="utf-8-sig", newline="")))
             for f in glob.glob(f"{SRC}/_data/*.csv")})
site = dict(cfg, data=data)

def url_for(path):
    rel_ = os.path.relpath(path, SRC); stem = os.path.splitext(rel_)[0]
    if stem == "index": return "/"
    if stem.endswith("/index"): return "/" + stem[:-6] + "/"
    return "/" + stem + "/"

pages = []
for f in glob.glob(f"{SRC}/**/*.*", recursive=True):
    r = os.path.relpath(f, SRC)
    if r.startswith(("_", "assets", ".")) or r in ("README.md", "Gemfile"): continue
    if not f.endswith((".md", ".html")): continue
    fm, body = split_fm(open(f).read()); fm.update(url=url_for(f), _src=f, _body=body); pages.append(fm)

def render(page):
    body = env.from_string(liquid2jinja(page["_body"])).render(site=site, page=page)
    if page["_src"].endswith(".md"):
        body = markdown.markdown(body, extensions=["tables", "fenced_code", "md_in_html"])
    layout = page.get("layout", "page" if page["url"] != "/" else "default")
    while layout:
        fm, lt = split_fm(open(f"{SRC}/_layouts/{layout}.html").read())
        body = env.from_string(liquid2jinja(lt)).render(site=site, page=page, content=body)
        layout = fm.get("layout")
    return body

for p in pages:
    d = OUT + p["url"]; os.makedirs(d, exist_ok=True)
    open(d + "index.html", "w").write(render(p)); print("built", p["url"])
shutil.copytree(f"{SRC}/assets", f"{OUT}/assets")

# Make every internal link relative so the site works from any folder,
# including when opened directly from disk (file://).
def relativize(html, url):
    depth = url.strip("/").count("/") + (1 if url.strip("/") else 0)
    prefix = "../" * depth or "./"
    def fix(m):
        attr, path = m.group(1), m.group(2)
        frag = ""
        if "#" in path: path, frag = path.split("#", 1); frag = "#" + frag
        if path.endswith("/") or path == "": path += "index.html"
        return f'{attr}="{prefix}{path.lstrip("/")}{frag}"'
    return re.sub(r'(href|src)="(/(?!/)[^"]*)"', fix, html)

for p in pages:
    f = OUT + p["url"] + "index.html"
    html = relativize(open(f).read(), p["url"]); open(f, "w").write(html)
# Relative links written in Markdown (e.g. ../people/) also need index.html for file:// browsing
for p in pages:
    f = OUT + p["url"] + "index.html"
    html = re.sub(r'href="((?!https?:|mailto:|#)[^"]*/)(#[^"]*)?"', lambda m: f'href="{m.group(1)}index.html{m.group(2) or ""}"', open(f).read())
    open(f, "w").write(html)
