#!/usr/bin/env python3
"""Run a week's tests against your compiler (or the oracle).

  python3 run_tests.py 1                      # uses ./compile
  python3 run_tests.py 1 --compiler "python3 my_compiler.py"
  python3 run_tests.py 1 -v                   # show every file

The expected outcome comes from the filename prefix:
  (none) MATCH · mismatch_ MISMATCH · rejected_ REJECTED · overbudget_ OVERBUDGET
"""
import argparse, glob, os, shlex, shutil, subprocess, sys

def expected(path):
  b = os.path.basename(path)
  for pre, out in (("mismatch_", "MISMATCH"), ("rejected_", "REJECTED"), ("overbudget_", "OVERBUDGET")):
    if b.startswith(pre): return out
  return "MATCH"

ap = argparse.ArgumentParser()
ap.add_argument("week", type=int)
ap.add_argument("--compiler", default="./compile")
ap.add_argument("-v", action="store_true")
ap.add_argument("--timeout", type=float, default=10)
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(here, "tests", f"week{a.week:02d}", "*.uir")))
if not files: sys.exit(f"no tests for week {a.week}")
cmd = shlex.split(a.compiler)
if not shutil.which(cmd[0]) and not os.path.isfile(cmd[0]):
  sys.exit(f"Can't find your compiler: {cmd[0]!r}.\n"
           "Build an executable ./compile in the repo root (any language; a shell script that runs\n"
           "`python3 my_compiler.py \"$@\"` is fine), or pass --compiler \"python3 my_compiler.py\".")
ok = 0
for f in files:
  rel = os.path.relpath(f)
  try:
    r = subprocess.run(shlex.split(a.compiler) + [rel], capture_output=True, text=True, timeout=a.timeout)
    got = (r.stdout.strip().split() or ["(no output)"])[0]
  except subprocess.TimeoutExpired:
    got = "TIMEOUT"
  exp = expected(f); good = got == exp; ok += good
  if a.v or not good: print(f"{'ok  ' if good else 'FAIL'} {rel}: expected {exp}, got {got}")
print(f"\n{ok}/{len(files)} passed")
sys.exit(0 if ok == len(files) else 1)
