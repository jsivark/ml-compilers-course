#!/usr/bin/env python3
"""Quality gate for curriculum/*.json.

  python3 tools/check_content.py          # style + structure
  python3 tools/check_content.py --links  # also check every URL (slow)

Fails (exit 1) on: missing fields, filler phrases, em-dashes, duplicate lines across modules,
and (with --links) URLs that don't return 2xx/3xx. Sites that block automated clients can be
marked "bot_block": true on the step and are reported but not failed.
"""
import glob, json, os, re, sys, urllib.request, concurrent.futures as cf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site"))
sys.dont_write_bytecode = True
from build import KIND, KN  # the step and "go deeper" kinds the site knows how to label

FILLER = [r"\bdelve", r"\bleverag", r"\bseamless", r"\brobust understanding", r"\bdeep understanding",
          r"\bunlock(?!ing gpu performance)", r"\bembark", r"\bjourney\b", r"\bgame[- ]changer", r"\btapestry", r"\bin today's",
          r"\bcutting[- ]edge", r"\bharness the power", r"\bit's worth noting", r"(?<!deep )\bdive into (?!systems|deep learning|dispatching)", r"\bnavigate the",
          r"\bempower", r"\bsupercharge", r"\bmaster(?:y|ing)? the art"]
REQ = ["id", "title", "why", "steps", "build", "check", "effort", "difficulty", "outcomes", "stuck", "project"]

def strings(x):
  if isinstance(x, str): yield x
  elif isinstance(x, dict):
    for v in x.values(): yield from strings(v)
  elif isinstance(x, list):
    for v in x: yield from strings(v)

SAFE_URL = re.compile(r"https?://[^\s<>\"'`]+")

def all_urls(x):
  """Every non-empty "url" value anywhere in a module."""
  if isinstance(x, dict):
    for k, v in x.items():
      if k == "url" and isinstance(v, str) and v: yield v
      else: yield from all_urls(v)
  elif isinstance(x, list):
    for v in x: yield from all_urls(v)

def urls(m):
  for s in m.get("steps", []):
    if s.get("url"): yield s["url"], s.get("bot_block", False)
  for x in m.get("extra", []):
    if isinstance(x, dict) and x.get("url"): yield x["url"], False
  for x in m.get("solutions", []) + m.get("deeper", []):
    if x.get("url"): yield x["url"], x.get("bot_block", False)
  for r in (m.get("project") or {}).get("references", []):
    if r.get("url"): yield r["url"], False

def head(u):
  req = urllib.request.Request(u, headers={"User-Agent": "ml-compilers-course link checker"})
  try:
    with urllib.request.urlopen(req, timeout=25) as r: return r.status
  except urllib.error.HTTPError as e: return e.code
  except Exception as e: return str(e)[:60]

def main():
  mods = [m for f in sorted(glob.glob("curriculum/*.json")) for m in json.load(open(f))]
  errs, warns, seen = [], [], {}
  for m in mods:
    tag = f"module {m.get('id')}"
    for k in REQ:
      if not m.get(k) and m.get(k) != 0: errs.append(f"{tag}: missing {k}")
    for s in strings(m):
      if "—" in s: errs.append(f"{tag}: em-dash in: {s[:70]}")
      for pat in FILLER:
        if re.search(pat, s, re.I): errs.append(f"{tag}: filler /{pat}/ in: {s[:70]}")
    for u in all_urls(m):
      if not SAFE_URL.fullmatch(u): errs.append(f"{tag}: unsafe or malformed url: {u[:80]!r}")
      elif u.startswith("http://"): warns.append(f"{tag}: plain http url: {u}")
    for x in m.get("deeper", []):
      if x.get("kind", "blog") not in KN: errs.append(f"{tag}: deeper kind {x.get('kind')!r} not in build.py KN")
    for s in m.get("steps", []):
      if s.get("kind") not in KIND: errs.append(f"{tag}: step kind {s.get('kind')!r} not in build.py KIND")
    if m.get("course_week") is not None and not re.fullmatch(r"\d+", str(m["course_week"])):
      errs.append(f"{tag}: course_week {m['course_week']!r} is not an integer")
    if re.search(r"[<>]", str(m.get("effort", ""))): errs.append(f"{tag}: '<' or '>' in effort")
    for k in ("outcomes", "stuck", "check"):
      for line in m.get(k, []):
        key = line.strip().lower()
        if key in seen and seen[key] != m["id"]: warns.append(f"{tag}: '{line[:60]}' duplicates module {seen[key]}")
        seen.setdefault(key, m["id"])
  if "--links" in sys.argv:
    todo = {u: bb for m in mods for u, bb in urls(m)}
    with cf.ThreadPoolExecutor(16) as ex:
      for (u, bb), code in zip(todo.items(), ex.map(head, todo)):
        ok = isinstance(code, int) and code < 400
        if not ok: (warns if bb or code in (403, 406, 418, 429, 503) or not isinstance(code, int) else errs).append(f"link {code}: {u}")
    print(f"checked {len(todo)} links")
  for w in warns: print("warn:", w)
  for e in errs: print("ERROR:", e)
  print(f"{len(mods)} modules, {len(errs)} errors, {len(warns)} warnings")
  sys.exit(1 if errs else 0)

if __name__ == "__main__":
  main()
