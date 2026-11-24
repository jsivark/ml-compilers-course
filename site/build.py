#!/usr/bin/env python3
"""Build the course website from curriculum/*.json into docs/ (served by GitHub Pages).

  python3 site/build.py
"""
import html, json, os, re, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "curriculum")
OUT = os.path.join(ROOT, "docs")
E = lambda s: html.escape(str(s or ""), quote=True)

PARTS = [
  ("start", "Start here", "Orientation", range(0, 1),
   "Set up your tools, learn how to study this material, and start the public repo and learning log that become your portfolio."),
  ("foundations", "Part I", "Foundations", range(1, 10),
   "What CMU's prerequisites (15-213 Computer Systems, 10-301 Machine Learning) would have taught you: C, how machines run code, the math, and deep learning from scratch."),
  ("bridge", "Part II", "Bridge", range(10, 18),
   "What a compiler course assumes you know: interpreters, compiling to assembly, IRs, rewriting, autodiff, ML frameworks, performance, and GPUs."),
  ("course", "Part III", "The Course", range(18, 32),
   "The 10-411 syllabus in order. One repo, one ./compile, more capable with each module: from constant folding to tensor-core GEMMs and flash attention."),
  ("frontier", "Part IV", "Frontier", range(32, 40),
   "From course graduate to top-lab level: the industrial tools (Triton, CUTLASS, MLIR, XLA), scheduling theory, low-precision numerics, accelerator design, training at scale, and research and open-source work."),
]
KIND = {"watch": "Watch", "read": "Read", "do": "Do", "build": "Build", "implement": "Implement",
        "test": "Test", "measure": "Measure"}

def page(title, body, depth=0, here=""):
  up = "../" * depth
  return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono&display=swap">
<link rel="stylesheet" href="{up}style.css"></head>
<body><header class="top"><div class="bar"><a class="brand" href="{up}index.html">ML Compilers From Zero</a>
<nav><a href="{up}index.html#modules"{' class="on"' if here=='modules' else ''}>Modules</a><a href="{up}assignments.html"{' class="on"' if here=='assign' else ''}>Assignments</a><a href="{up}portfolio.html"{' class="on"' if here=='portfolio' else ''}>Portfolio</a><a href="{up}projects.html"{' class="on"' if here=='projects' else ''}>Capstone</a><a href="{up}library.html"{' class="on"' if here=='library' else ''}>Library</a><a href="{up}about.html"{' class="on"' if here=='about' else ''}>About</a><a href="https://github.com/jsivark/ml-compilers-course">GitHub</a></nav></div></header>
<main class="wrap">{body}</main>
<footer class="wrap foot">An independent, free rebuild of CMU 10-411 <i>Compilers for Machine Learning</i>, based on the course's public topic list and Week 1 handout. Not affiliated with CMU. <a href="{up}about.html">How this was made</a> · <a href="https://github.com/jsivark/ml-compilers-course/issues">Report a mistake</a></footer>
</body></html>"""

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
    proj = (f'<section class="proj"><h2>Project</h2><p>{E(pr.get("note"))} '
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
    proj = (f'<section class="proj"><h2>Portfolio project: {E(pr.get("title"))}</h2>{tagh}<p>{E(pr.get("brief"))}</p>'
            + (f"<h3>Deliverables</h3><ul>{dl}</ul>" if dl else "")
            + (f'<h3>Rubric</h3><dl class="rub"><dt>Solid</dt><dd>{E(rb.get("solid"))}</dd><dt>Exceptional</dt><dd>{E(rb.get("exceptional"))}</dd></dl>' if rb else "")
            + (f'<p class="hint">References: {refs}</p>' if refs else "") + "</section>")
  prev = f'<a href="{i-1:02d}.html">← {i-1:02d} {E(mods[i-1]["title"])}</a>' if i-1 in mods else "<span></span>"
  nxt = f'<a href="{i+1:02d}.html">{i+1:02d} {E(mods[i+1]["title"])} →</a>' if i+1 in mods else "<span></span>"
  body = f"""<p class="crumb"><a href="../index.html#{p[0]}">{p[1]} · {p[2]}</a>{cw}</p>
<h1><span class="num">{i:02d}</span>{E(m["title"])}</h1>
<p class="lede">{E(m.get("why"))}</p>
{f'<p class="mmeta">{meta}</p>' if meta else ''}
{f'<h2>After this module you can</h2><ul class="check">{outcomes}</ul>' if outcomes else ''}
<h2>Steps</h2><p class="hint">Work through these in order. Each step points at one specific unit.</p>
<ol class="steps">{steps}</ol>
<h2>Build</h2><p class="build">{E(m.get("build"))}</p>
{proj}
{f'<h2>If you get stuck</h2><ul class="check">{stuck}</ul>' if stuck else ''}
{f'<h2>Ready to move on when</h2><ul class="check">{check}</ul>' if check else ''}
{f'<h2>Reference implementations</h2><p class="hint">Make a real attempt first. When you are stuck, or after you finish, compare your work with these.</p><ul class="extra">{sol}</ul>' if sol else ''}
{f'<h2>Going deeper</h2><p class="hint">Optional. The best talks, papers, code and writing on this module topic, from people who shaped the field.</p>{deeper}' if deeper else ''}
{f'<h3>More reading</h3><ul class="extra">{extra}</ul>' if extra and deeper else (f'<h2>Going deeper (optional)</h2><ul class="extra">{extra}</ul>' if extra else '')}
{f'<h2>Stretch project</h2><p class="build">{E(m.get("stretch"))}</p>' if m.get("stretch") else ''}
<nav class="pn">{prev}{nxt}</nav>"""
  return page(f'{i:02d} {m["title"]} · ML Compilers From Zero', body, 1)

def index(mods):
  parts = ""
  for pid, pn, name, rng, blurb in PARTS:
    rows = "".join(
      f'<li><a href="modules/{i:02d}.html"><span class="num">{i:02d}</span>{E(mods[i]["title"])}</a>'
      f'<span class="meta">{E(mods[i].get("effort") or str(len(mods[i]["steps"])) + " steps")}{" · " + "●"*int(mods[i]["difficulty"]) if mods[i].get("difficulty") else ""}</span></li>'
      for i in rng if i in mods)
    parts += f'<section id="{pid}"><h2>{pn} · {name}</h2><p class="sub">{E(blurb)}</p><ol class="mods">{rows}</ol></section>'
  body = f"""<h1>ML Compilers From Zero</h1>
<p class="lede">A free, self-paced path from intermediate Python and basic C to writing your own machine-learning compiler, modelled on CMU 10-411 <i>Compilers for Machine Learning</i>. Every module is a short, ordered list of specific lectures, chapters, problems and projects. Each one ends with something you build.</p>
<h2>How to use this</h2>
<ul class="how">
<li><b>Go in order.</b> Each module assumes the ones before it. If you already know a topic, do its <i>Build</i> step anyway. If it's easy, skip ahead.</li>
<li><b>No deadlines.</b> Move on when the build works and you can answer every “ready to move on when” question without notes.</li>
<li><b>Get the code.</b> The assignments, tests and this site's source are on GitHub: <a href="https://github.com/jsivark/ml-compilers-course">github.com/jsivark/ml-compilers-course</a>.</li>
<li><b>Keep one repo.</b> From Module 18 onward, you grow a single <code>./compile</code>. The <a href="assignments.html">assignments</a> come with test suites.</li>
<li><b>Build one system, plus focused projects.</b> Your main project, kiln, grows from a C tensor core in Module 1 to a compiler that trains a GPT on your GPU in Module 38. Each version works on its own. Skill projects along the way teach what kiln does not cover. See the <a href="portfolio.html">portfolio</a>.</li>
<li><b>Effort estimates are honest, not deadlines.</b> Hard modules take longer. Being stuck is normal, and every module has an “if you get stuck” section.</li>
<li><b>Write the code yourself.</b> Use AI to explain things and to debug, not to write your compiler. The real course has the same rule.</li>
</ul>
<div id="modules">{parts}</div>"""
  return page("ML Compilers From Zero", body, 0, "modules")

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
          + sec("Capstone", "One capstone in three phases. Module 39 adds a research track.", by("capstone"), ex)
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
      flush(); out.append("</pre>" if code else "<pre>"); code = not code; continue
    if code: out.append(E(line) + "\n"); continue
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
  md = md.split("\n", 1)[1]  # drop H1
  intro = ('<h1>Assignments</h1><p class="lede">The compiler you build across Part III. Get the starter repo, which has the specs, test suites and a test runner:</p>'
           '<p><b>The tests start at Module 18.</b> Modules 0–17 rely on the labs and test suites linked from each module. Test folders are numbered by the real course\'s weeks: Module 18 is <code>tests/week01</code> (<code>python3 run_tests.py 1</code>), Module 19 is <code>week02</code>, and so on through Module 24 (<code>week07</code>). Modules 25–28 are graded by measured milestones.</p>'
           '<pre>git clone https://github.com/jsivark/ml-compilers-course.git\ncd ml-compilers-course\npython3 run_tests.py 1   # runs ./compile on tests/week01</pre>')
  return page("Assignments · ML Compilers From Zero", intro + md_to_html(md), 0, "assign")

def static(name):
  return open(os.path.join(ROOT, "site", name)).read()

def main():
  mods = load()
  KILN.update({i: m["project"]["version"] for i, m in mods.items() if m.get("project", {}).get("track") == "main"})
  if os.path.exists(OUT): shutil.rmtree(OUT)
  os.makedirs(os.path.join(OUT, "modules"))
  w = lambda p, s: open(os.path.join(OUT, p), "w").write(s)
  w("style.css", static("style.css"))
  w(".nojekyll", "")
  w("index.html", index(mods))
  w("assignments.html", assignments())
  w("portfolio.html", portfolio(mods))
  for name, here, title in (("projects.html", "projects", "Final projects"), ("library.html", "library", "Library"), ("about.html", "about", "About")):
    w(name, page(f"{title} · ML Compilers From Zero", static(name), 0, here))
  for i, m in mods.items(): w(f"modules/{i:02d}.html", module_page(m, mods))
  print(f"built {len(mods)} modules into {OUT}")

if __name__ == "__main__":
  main()
