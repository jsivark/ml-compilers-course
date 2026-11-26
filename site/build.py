#!/usr/bin/env python3
"""Build the course website from curriculum/*.json into docs/ (served by GitHub Pages).

  python3 site/build.py
"""
import html, json, os, re, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "curriculum")
OUT = os.environ.get("SITE_OUT") or os.path.join(ROOT, "docs")
STYLE = "style.css"
E = lambda s: html.escape(str(s or ""), quote=True)

PARTS = [
  ("start", "Start here", "Orientation", range(0, 1),
   "Set up your tools, learn how to study this material, and start the public repo and learning log that become your portfolio."),
  ("foundations", "Part I", "Foundations", range(1, 11),
   "What CMU's prerequisites (15-213 Computer Systems, 10-301 Machine Learning) would have taught you: C, the C++ that ML tools are written in, how machines run code, the math, and deep learning from scratch."),
  ("bridge", "Part II", "Bridge", range(11, 19),
   "What a compiler course assumes you know: interpreters, compiling to assembly, IRs, rewriting, autodiff, ML frameworks, performance, and GPUs."),
  ("course", "Part III", "The Course", range(19, 33),
   "The 10-411 syllabus in order. One repo, one ./compile, more capable with each module: from constant folding to tensor-core GEMMs and flash attention."),
  ("frontier", "Part IV", "Frontier", range(33, 41),
   "From course graduate to top-lab level: the industrial tools (Triton, CUTLASS, MLIR, XLA), scheduling theory, low-precision numerics, accelerator design, training at scale, and research and open-source work."),
]
KIND = {"watch": "Watch", "read": "Read", "do": "Do", "build": "Build", "implement": "Implement",
        "test": "Test", "measure": "Measure"}

EXTRA_JS = ""
TOGGLE = ""
THEME_JS = ""
PREVIEW = True
MAP = {}  # depth -> course map html (preview)
if True:
  THEME_JS = "<script>try{var t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}catch(e){}</script>"
  TOGGLE = '<button class="theme" type="button" aria-label="Switch light or dark" onclick="var d=document.documentElement,n=d.dataset.theme==\'dark\'?\'light\':\'dark\';d.dataset.theme=n;try{localStorage.setItem(\'theme\',n)}catch(e){}">◐</button>'


def page(title, body, depth=0, here="", part=""):
  up = "../" * depth
  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><link rel="icon" type="image/svg+xml" href="{up}favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono&display=swap">
<link rel="stylesheet" href="{up}style.css">{THEME_JS}{f'<meta name="base" content="{up}"><script src="{up}app.js" defer></script>' if PREVIEW else ''}</head>
<body data-part="{part}"{' class="has-map"' if (PREVIEW and part) else ''}>{'<div class="art-bg" aria-hidden="true"></div>' if PREVIEW else ''}<header class="top"><div class="bar">{'<button class="map-btn" type="button" aria-label="Course map">☰</button>' if (PREVIEW and part) else ''}<a class="brand" href="{up}index.html">ML Compilers From Zero</a>{'<button class="menu-btn" type="button" aria-label="Menu">Menu</button>' if PREVIEW else ''}
<nav><a href="{up}index.html#modules"{' class="on"' if here=='modules' else ''}>Modules</a><a href="{up}assignments.html"{' class="on"' if here=='assign' else ''}>Assignments</a><a href="{up}portfolio.html"{' class="on"' if here=='portfolio' else ''}>Portfolio</a><a href="{up}projects.html"{' class="on"' if here=='projects' else ''}>Capstone</a><a href="{up}library.html"{' class="on"' if here=='library' else ''}>Library</a><a href="{up}about.html"{' class="on"' if here=='about' else ''}>About</a><a href="https://github.com/jsivark/ml-compilers-course">GitHub</a>{'<button class="search-open" type="button" aria-label="Search">Search <kbd>⌘K</kbd></button>' if PREVIEW else ''}{TOGGLE}</nav></div></header>
{MAP.get(depth, "") if (PREVIEW and part) else ""}<main class="wrap">{linkify(body)}</main>
<footer class="wrap foot">An independent, free rebuild of CMU 10-411 <i>Compilers for Machine Learning</i>, based on the course's public topic list and Week 1 handout. Not affiliated with CMU. © 2026 jsivark · <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0 — reuse freely with credit</a> · <a href="{up}about.html">How this was made</a> · <a href="https://github.com/jsivark/ml-compilers-course/issues">Report a mistake</a>{'<br><span class="art-credit"></span>' if PREVIEW else ''}</footer>
{EXTRA_JS}</body></html>"""

URL = re.compile(r"https?://[^\s<>\"']+")
def _label(u):
  h, _, path = u.split("://", 1)[1].partition("/")
  h = h.removeprefix("www.")
  parts = [x for x in path.split("/") if x]
  if "github.com" in h and len(parts) >= 2:
    return parts[1] + (" · " + parts[-1] if len(parts) > 2 else "") + " on GitHub"
  if "arxiv.org" in h and parts: return "arXiv " + parts[-1]
  lab = h + ("/" + "/".join(parts) if parts else "")
  return lab if len(lab) <= 42 else h + "/…/" + parts[-1]
CODECH = set("()[]{}=*%^_<>\\|~")
def _is_code(w):
  if len(w) < 2 or not any(c.isalnum() for c in w): return False
  if w in {"sizeof", "printf", "malloc", "calloc", "realloc", "memcpy", "strlen", "argc", "argv", "argc/argv", "malloc/free", "nullptr", "__global__", "numpy"}: return True
  if re.fullmatch(r"[<>~]?\d+(\.\d+)?%\+?", w): return False                 # 70%, >97%
  if re.fullmatch(r"\(([^()\[\]{}=*%^_<>\\|~]*)\)", w): return False     # (optional), (4)
  if re.fullmatch(r"-{1,2}[A-Za-z][\w=,.-]*", w): return True            # -Wall, --links
  if re.search(r"\.(c|h|py|cu|json|md|uir|bin|s)$", w) and "/" not in w[:-3]: return True
  return any(c in CODECH for c in w) or w.endswith("'\\0'")
def codeify(text):
  """Wrap code-like words in <code> (text is already HTML-escaped)."""
  def word(m):
    w = html.unescape(m.group(0)); pre = post = ""
    while w and w[-1] in ".,;:!?": post = w[-1] + post; w = w[:-1]
    if w.startswith("(") and w.count("(") > w.count(")"): pre, w = "(", w[1:]
    if w.endswith(")") and w.count(")") > w.count("("): post, w = ")" + post, w[:-1]
    if not _is_code(w): return m.group(0)
    return E(pre) + "<code>" + E(w) + "</code>" + E(post)
  parts = re.split(r"`([^`]+)`", text)   # explicit `code` spans first
  return "".join(f"<code>{x}</code>" if i % 2 else re.sub(r"\S+", word, x) for i, x in enumerate(parts))

def linkify(htm):
  out, inside = [], False
  for tok in re.split(r"(<[^>]+>)", htm):
    if tok.startswith("<"):
      t = tok.lower()
      if re.match(r"<(a|pre|code|title|h1)[ >]", t): inside = True
      elif re.match(r"</(a|pre|code|title|h1)>", t): inside = False
      out.append(tok); continue
    if inside: out.append(tok); continue
    if "http" not in tok: out.append(codeify(tok)); continue
    def rep(m):
      u = m.group(0); tail = ""
      while u and u[-1] in ".,;:)]": tail = u[-1] + tail; u = u[:-1]
      raw = html.unescape(u)
      return f'<a href="{E(raw)}" target="_blank" rel="noopener">{E(_label(raw))}</a>{tail}'
    pieces = re.split(r"(https?://[^\s<>\"']+)", tok)
    out.append("".join(URL.sub(rep, x) if i % 2 else codeify(x) for i, x in enumerate(pieces)))
  return "".join(out)

SENT = re.compile(r"(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\bch)(?<!\bet al)(?<=[.!?])\s+(?=[A-Z(])")
def numbered(t):
  """Readable blocks: '(1) a (2) b' or 3+ sentences become a list; short text stays a paragraph."""
  t = str(t or "").strip()
  if t.startswith("(1) "):
    items = [x.strip() for x in re.split(r"(?:^|\s)\(\d\)\s", t) if x.strip()]
    return "<ol>" + "".join(f"<li>{E(x)}</li>" for x in items) + "</ol>"
  sents = SENT.split(t)
  if len(sents) < 3: return f"<p>{E(t)}</p>"
  return '<ul class="sents">' + "".join(f"<li>{E(x)}</li>" for x in sents) + "</ul>"

def link(t, u):
  return f'<a href="{E(u)}" target="_blank" rel="noopener">{E(t)}</a>' if u else E(t)

def load():
  mods = {}
  for f in sorted(os.listdir(SRC)):
    if f.endswith(".json"):
      for m in json.load(open(os.path.join(SRC, f))): mods[int(m["id"])] = m
  return mods

def part_of(i):
  for p in PARTS:
    if i in p[3]: return p

KILN = {}

def module_page(m, mods):
  i = m["id"]; p = part_of(i)
  def step(s):
    k = E(KIND.get(s.get("kind"), s.get("kind", "")).capitalize())
    d = "<p>" + E(s["detail"]) + "</p>" if s.get("detail") else ""
    return f'<li><span class="k">{k}</span><div><p class="st">{link(s["title"], s.get("url"))}</p>{d}</div></li>'
  steps = "".join(step(s) for s in m["steps"])
  check = "".join(f"<li>{E(c)}</li>" for c in m.get("check", []))
  ex = lambda x: f"<li>{E(x)}</li>" if isinstance(x, str) else f'<li>{link(x["title"], x.get("url"))}{" — " + E(x["note"]) if x.get("note") else ""}</li>'
  extra = "".join(ex(x) for x in m.get("extra", []))
  sol = "".join(f'<li>{link(x["title"], x.get("url"))}{" <span class=n>(" + E(x["for"]) + ")</span>" if x.get("for") else ""}{"<br><span class=n>" + E(x["note"]) + "</span>" if x.get("note") else ""}</li>' for x in m.get("solutions", []))
  KO = ["lecture", "course", "talk", "video", "paper", "book", "blog", "repo", "problems"]
  KN = {"lecture": "Lectures", "course": "Courses", "talk": "Talks", "video": "Videos", "paper": "Papers", "book": "Books", "blog": "Blogs and articles", "repo": "Code to read", "problems": "Problem sets"}
  groups = {}
  for x in m.get("deeper", []): groups.setdefault(x.get("kind", "blog"), []).append(x)
  def shelf(xs):
    return '<div class="shelf">' + "".join(
      f'<a class="bk" href="{E(x.get("url") or "#")}" target="_blank" rel="noopener" title="{E(x.get("note", ""))}">'
      f'<span class="bt">{E(x["title"])}</span><span class="ba">{E(x.get("by", ""))}</span></a>' for x in xs) + "</div>"
  deeper = "".join(
    f'<h3>{KN.get(k, k.title())}</h3><ul class="extra">' + "".join(
      f'<li>{link(x["title"], x.get("url"))}{" <span class=n>· " + E(x["by"]) + "</span>" if x.get("by") else ""}{"<br><span class=n>" + E(x["note"]) + "</span>" if x.get("note") else ""}</li>' for x in groups[k]) + "</ul>"
    for k in sorted(groups, key=lambda k: KO.index(k) if k in KO else 99))
  cw = f' · 10-411 week {m["course_week"]}' if m.get("course_week") else ""
  meta = " · ".join(x for x in [m.get("effort") and f'about {m["effort"]}', m.get("difficulty") and "difficulty " + "●"*int(m["difficulty"]) + "○"*(5-int(m["difficulty"]))] if x)
  outcomes = "".join(f"<li>{E(o)}</li>" for o in m.get("outcomes", []))
  stuck = "".join(f"<li>{E(o)}</li>" for o in m.get("stuck", []))
  pr = m.get("project") or {}
  proj = ""
  TL = {"main": "kiln, the main project", "skill": "Skill project", "optional": "Optional project", "capstone": "Capstone", "setup": "Setup project"}
  if pr.get("track") == "merged":
    proj = (f'<section class="proj" id="project"><h2>Project</h2><p>{E(pr.get("note"))} '
            f'<a href="{pr["into"]:02d}.html">Go to Module {pr["into"]:02d}</a>.</p></section>')
    pr = {}
  if pr:
    tr = pr.get("track", "")
    tag = TL.get(tr, "")
    if tr == "main":
      vs = sorted(((int(k), v) for k, v in KILN.items()), key=lambda t: t[0])
      before = [k for k, _ in vs if k < i]; after = [k for k, _ in vs if k > i]
      tag += (f' · {E(pr["version"])} adds {E(pr["adds"])}'
              + (f' · builds on <a href="{before[-1]:02d}.html">{E(KILN[before[-1]])}</a>' if before else "")
              + (f' · next: <a href="{after[0]:02d}.html">{E(KILN[after[0]])}</a>' if after else ""))
    tagh = f'<p class="hint">{tag}</p>' if tag else ""
    dl = "".join(f"<li>{E(d)}</li>" for d in pr.get("deliverables", []))
    rb = pr.get("rubric", {})
    refs = ", ".join(link(r["title"], r.get("url")) for r in pr.get("references", []))
    proj = (f'<section class="proj" id="project"><h2>Portfolio project: {E(pr.get("title"))}</h2>{tagh}<p>{E(pr.get("brief"))}</p>'
            + (f"<h3>Deliverables</h3><ul>{dl}</ul>" if dl else "")
            + (f'<h3>Rubric</h3><dl class="rub"><dt>Solid</dt><dd>{E(rb.get("solid"))}</dd><dt>Exceptional</dt><dd>{E(rb.get("exceptional"))}</dd></dl>' if rb else "")
            + (f'<p class="hint">References: {refs}</p>' if refs else "") + "</section>")
  prev = f'<a href="{i-1:02d}.html">← {i-1:02d} {E(mods[i-1]["title"])}</a>' if i-1 in mods else "<span></span>"
  nxt = f'<a href="{i+1:02d}.html">{i+1:02d} {E(mods[i+1]["title"])} →</a>' if i+1 in mods else "<span></span>"
  body = f"""<nav class="pn top">{prev}{nxt}</nav><p class="crumb"><a href="../index.html#{p[0]}">{p[1]} · {p[2]}</a>{cw}</p>
<h1><span class="num">{i:02d}</span>{E(m["title"])}</h1>
<p class="lede">{E(m.get("why"))}</p>
<div class="mhead">{f'<p class="mmeta">{meta}</p>' if meta else ''}{f'<button class="mark" type="button" data-mod="{i}">Mark module done</button>' if PREVIEW else ''}</div>
<nav class="toc"><a href="#steps">Steps</a><a href="#build">Build</a>{'<a href="#project">Project</a>' if proj else ''}<a href="#help">Help</a>{'<a href="#deeper">Go deeper</a>' if (deeper or extra or m.get("stretch")) else ''}</nav>
{f'<h2>After this module you can</h2><ul class="check">{outcomes}</ul>' if outcomes else ''}
<h2 id="steps">Steps</h2><p class="hint">Work through these in order. Each step points at one specific unit.</p>
<ol class="steps">{steps}</ol>
<h2 id="build">Build</h2><div class="build">{numbered(m.get("build"))}</div>
{proj}
<h2 id="help">Help</h2>
{f'<div class="callout stuck"><h3>If you get stuck</h3><ul class="check">{stuck}</ul></div>' if stuck else ''}
{f'<div class="callout ready"><h3>Ready to move on when</h3><ul class="check">{check}</ul></div>' if check else ''}
{f'<details><summary>Reference implementations ({len(m.get("solutions", []))})</summary><p class="hint">Make a real attempt first. When you are stuck, or after you finish, compare your work with these.</p><ul class="extra">{sol}</ul></details>' if sol else ''}
{'<h2 id="deeper">Go deeper <span class="n">(optional)</span></h2>' if (deeper or extra or m.get("stretch")) else ''}
{f'<details><summary>Talks, papers, code and writing ({len(m.get("deeper", [])) + len(m.get("extra", []))})</summary>{deeper}' + (f'<h3>More reading</h3><ul class="extra">{extra}</ul>' if extra else '') + '</details>' if (deeper or extra) else ''}
{f'<details><summary>Stretch project</summary><div class="build">{numbered(m.get("stretch"))}</div></details>' if m.get("stretch") else ''}
<nav class="pn">{prev}{nxt}</nav>"""
  html_ = page(f'{i:02d} {m["title"]} · ML Compilers From Zero', body, 1, "", p[0])
  return html_.replace(f'<a data-mod="{i}" ', f'<a data-mod="{i}" class="cur" aria-current="page" ', 1)

def index(mods):
  parts = ""
  for pid, pn, name, rng, blurb in PARTS:
    rows = "".join(
      f'<li><a href="modules/{i:02d}.html" data-mod="{i}"><span class="num">{i:02d}</span>{E(mods[i]["title"])}</a>'
      f'<span class="meta">{E((mods[i].get("effort") or "").split(" (")[0] or str(len(mods[i]["steps"])) + " steps")}{" · " + "●"*int(mods[i]["difficulty"]) if mods[i].get("difficulty") else ""}</span></li>'
      for i in rng if i in mods)
    pp = f' <span class="pp" data-part-progress="{",".join(str(i) for i in rng)}"></span>' if PREVIEW else ""
    parts += f'<section id="{pid}"><h2>{pn} · {name}{pp}</h2><p class="sub">{E(blurb)}</p><ol class="mods">{rows}</ol></section>'
  body = f"""<h1>ML Compilers From Zero</h1>
<p class="lede">A free, self-paced path from intermediate Python and basic C to writing your own machine-learning compiler, modelled on CMU 10-411 <i>Compilers for Machine Learning</i>. Every module is a short, ordered list of specific lectures, chapters, problems and projects. Each one ends with something you build.</p>
<h2>How to use this</h2>
<ul class="how">
<li><b>Go in order.</b> Each module assumes the ones before it. If you already know a topic, do its <i>Build</i> step anyway. If it's easy, skip ahead.</li>
<li><b>No deadlines.</b> Move on when the build works and you can answer every “ready to move on when” question without notes.</li>
<li><b>Get the code.</b> The assignments, tests and this site's source are on GitHub: <a href="https://github.com/jsivark/ml-compilers-course">github.com/jsivark/ml-compilers-course</a>.</li>

<li><b>Build one system, plus focused projects.</b> Your main project, kiln, grows from a C tensor core in Module 1 to a compiler that trains a GPT on your GPU in Module 39. Each version works on its own. Skill projects along the way teach what kiln does not cover. See the <a href="portfolio.html">portfolio</a>.</li>
<li><b>Effort estimates are honest, not deadlines.</b> Hard modules take longer. Being stuck is normal, and every module has an “if you get stuck” section.</li>
<li><b>Write the code yourself.</b> Use AI to explain things and to debug, not to write your compiler. The real course has the same rule.</li>
</ul>
<div id="modules">{parts}</div>"""
  if PREVIEW:  # table of contents first, how-to folded below
    head, rest = body.split("<h2>How to use this</h2>")
    how, mods_ = rest.split('<div id="modules">')
    body = (head + '<p class="progress" data-progress></p><div id="modules">' + mods_
            + '<details class="how-box"><summary>How to use this course</summary>' + how + "</details>")
  return page("ML Compilers From Zero — a free course on machine learning compilers", body, 0, "modules")

def portfolio(mods):
  P = lambda i: mods[i]["project"]
  def li(i, sub):
    return (f'<li><a href="modules/{i:02d}.html"><span class="num">{i:02d}</span>{E(P(i)["title"])}</a>'
            f'<p>{E(sub)}</p></li>')
  by = lambda t: [i for i in sorted(mods) if mods[i].get("project", {}).get("track") == t]
  def sec(h, intro, ids, sub):
    if not ids: return ""
    return f'<h2>{h}</h2><p>{intro}</p><ol class="pf">' + "".join(li(i, sub(i)) for i in ids) + "</ol>"
  ex = lambda i: P(i).get("rubric", {}).get("exceptional", "")
  kv = lambda i: (P(i)["version"] + " adds " + P(i)["adds"] + ".") if P(i).get("version") else "Create the repo."
  body = ('<h1>Portfolio</h1><p class="lede">Two kinds of projects. <b>kiln</b> is one system you grow through the whole course: a small ML library with its own compiler, ending with a GPT trained on your own GPU. '
          '<b>Skill projects</b> are done once each and teach things kiln does not cover. Every kiln version is complete, tested and publishable on its own.</p>'
          + sec("kiln, version by version", "Tag each version in your kiln repo. If an earlier version is too messy to build on, refactor it before you move on; that is part of the work.", by("setup") + by("main"), kv)
          + sec("Skill projects", "One repo each, or folders in one monorepo. Below each is the bar for exceptional work.", by("skill"), ex)
          + sec("Capstone", "One capstone in three phases. Module 40 adds a research track.", by("capstone"), ex)
          + sec("Optional projects", "For readers who want these specialisms.", by("optional"), ex)
          + '<h2>How to present it</h2><ul class="how"><li>A README for every kiln version and skill project: how to run it, results tables and plots.</li>'
          '<li>A write-up for each on your blog or notes site. Explain the why, the measurements and what failed. This is the strongest signal you can send.</li>'
          '<li>Pin kiln first, then your best two or three skill projects (usually a GPU kernel worklog and mycc).</li></ul>')
  return page("Portfolio · ML Compilers From Zero", body, 0, "portfolio")

def md_to_html(md):
  """tiny markdown subset for README -> assignments page"""
  out, code, lst, tbl = [], False, None, []
  def inline(s):
    s = E(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r'(?<!href=")(?<![">])(https?://[^\s<)*]+)', r'<a href="\1">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
    return s
  def flush():
    nonlocal lst, tbl
    if lst: out.append(f"<{lst}>" + "".join(items) + f"</{lst}>"); lst = None
    if tbl:
      rows = [r for r in tbl if not re.match(r"^\|[-| ]+\|$", r)]
      cells = lambda r: [c.strip() for c in r.strip("|").split("|")]
      h = "".join(f"<th>{inline(c)}</th>" for c in cells(rows[0]))
      b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells(r)) + "</tr>" for r in rows[1:])
      out.append(f'<div class="tw"><table><tr>{h}</tr>{b}</table></div>'); tbl = []
  items = []
  for line in md.splitlines():
    if line.startswith("```"):
      flush()
      if code: out[-1] = out[-1].rstrip("\n") + "</pre>"
      else: out.append("<pre>")
      code = not code; continue
    if code: out[-1] += E(line) + "\n"; continue
    if line.startswith("|"): tbl.append(line); continue
    m = re.match(r"^(#{1,3}) (.*)", line)
    if m: flush(); lvl = len(m[1]) + (0 if len(m[1]) > 1 else 0); out.append(f"<h{lvl}>{inline(m[2])}</h{lvl}>"); continue
    m = re.match(r"^\s*(?:- |(\d+)\. )(.*)", line)
    if m:
      kind = "ol" if m[1] else "ul"
      if lst != kind: flush(); lst = kind; items = []
      items.append(f"<li>{inline(m[2])}</li>"); continue
    if line.strip() == "---": flush(); out.append("<hr>"); continue
    if not line.strip(): flush(); continue
    flush(); out.append(f"<p>{inline(line)}</p>")
  flush()
  return "\n".join(out)

def assignments():
  md = open(os.path.join(ROOT, "README.md")).read()
  md = md[md.index("\n## "):]  # skip H1, website link and repo blurb
  intro = ('<h1>Assignments</h1><p class="lede">The compiler you build across Part III. Get the starter repo, which has the specs, test suites and a test runner:</p>'
           '<pre>git clone https://github.com/jsivark/ml-compilers-course.git\ncd ml-compilers-course\npython3 run_tests.py 1   # runs ./compile on tests/week01</pre>')
  return page("Assignments · ML Compilers From Zero", intro + md_to_html(md), 0, "assign")

def static(name):
  return open(os.path.join(ROOT, "site", name)).read()

def main():
  mods = load()
  if PREVIEW:
    for d in (0, 1):
      up = "../" * d
      groups = "".join(
        f'<li><p>{E(pn)} · {E(name)}</p><ol>' + "".join(
          f'<li><a data-mod="{i}" href="{up}modules/{i:02d}.html"><span class="num">{i:02d}</span>{E(mods[i]["title"])}</a></li>' for i in rng if i in mods) + "</ol></li>"
        for pid, pn, name, rng, _ in PARTS)
      MAP[d] = f'<aside class="map" aria-label="Course map"><ol>{groups}</ol></aside>'
  KILN.update({i: m["project"]["version"] for i, m in mods.items() if m.get("project", {}).get("track") == "main"})
  if os.path.exists(OUT): shutil.rmtree(OUT)
  os.makedirs(os.path.join(OUT, "modules"))
  BASE = "https://jsivark.github.io/ml-compilers-course/"
  HOME_D = "A free, self-paced course on machine learning compilers: from Python and C to building your own ML compiler (IR, rewrites, codegen, GPU kernels, Triton). Modelled on CMU 10-411."
  DESC = {f"modules/{i:02d}.html": m.get("why", "").replace("`", "") for i, m in mods.items()}
  def seo(p, s):
    d = E((DESC.get(p) or HOME_D)[:300]); u = BASE + ("" if p == "index.html" else p)
    t = s[s.index("<title>")+7:s.index("</title>")]
    tags = (f'<meta name="description" content="{d}"><link rel="canonical" href="{u}">'
            f'<meta property="og:type" content="website"><meta property="og:title" content="{t}"><meta property="og:description" content="{d}"><meta property="og:url" content="{u}">')
    return s.replace("</title>", "</title>" + tags, 1)
  PAGES = []
  def w(p, s):
    if p.endswith(".html"): s = seo(p, s); PAGES.append(p)
    open(os.path.join(OUT, p), "w").write(s)
  w("style.css", static(STYLE))
  w("favicon.svg", static("favicon.svg"))
  if PREVIEW:
    w("app.js", static("app.js"))
    idx = []
    for i, m in mods.items():
      u = f"modules/{i:02d}.html"; mt = f"Module {i:02d} · {m['title']}"
      body_txt = " ".join([m.get("why", ""), m.get("build", ""), m.get("stretch", "")] + m.get("outcomes", []) + m.get("check", []) + m.get("stuck", [])).replace("`", "")
      idx.append({"k": "module", "t": f"{i:02d} {m['title']}", "m": m.get("why", "")[:120].replace("`", ""), "u": u, "x": body_txt})
      for st in m.get("steps", []): idx.append({"k": st.get("kind", "step"), "t": st["title"], "m": mt, "u": u + "#steps", "x": st.get("detail", "").replace("`", "")})
      pr = m.get("project") or {}
      if pr.get("title"): idx.append({"k": "project", "t": pr["title"], "m": mt, "u": u + "#project"})
      for x in m.get("deeper", []) + m.get("solutions", []):
        if x.get("url"): idx.append({"k": x.get("kind", "code"), "t": x["title"] + (" · " + x["by"] if x.get("by") else ""), "m": mt, "u": x["url"]})
    w("search.json", json.dumps(idx, ensure_ascii=False))
  w(".nojekyll", "")
  w("index.html", index(mods))
  w("assignments.html", assignments())
  w("portfolio.html", portfolio(mods))
  for name, here, title in (("projects.html", "projects", "Capstone"), ("library.html", "library", "Library"), ("about.html", "about", "About")):
    w(name, page(f"{title} · ML Compilers From Zero", static(name), 0, here))
  for i, m in mods.items(): w(f"modules/{i:02d}.html", module_page(m, mods))
  w("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{BASE}{'' if q == 'index.html' else q}</loc></url>\n" for q in PAGES) + "</urlset>\n")
  print(f"built {len(mods)} modules into {OUT}")

if __name__ == "__main__":
  main()
