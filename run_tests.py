#!/usr/bin/env python3
"""Run a week's tests against your compiler (or the oracle).

  python3 run_tests.py 1                      # uses ./compile
  python3 run_tests.py 1 --compiler "python3 my_compiler.py"
  python3 run_tests.py 1 -v                   # show every file

The expected outcome comes from the filename prefix:
  (none) MATCH · mismatch_ MISMATCH · rejected_ REJECTED · overbudget_ OVERBUDGET

Each run sets UIR_WEEK=<week> in the environment, so a compiler can apply that week's
rules (only week01/rejected_alu_on_vector.uir needs it: ALU ops on vectors become valid in week 4).
"""
import argparse, glob, os, shlex, shutil, signal, subprocess, sys

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
env = dict(os.environ, UIR_WEEK=str(a.week))
ok = 0
for f in files:
  rel = os.path.relpath(f)
  # own session, so a timeout kills the compiler and anything it started
  p = subprocess.Popen(shlex.split(a.compiler) + [rel], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
  try:
    out, _ = p.communicate(timeout=a.timeout)
    got = (out.strip().split() or ["(no output)"])[0]
  except subprocess.TimeoutExpired:
    try: os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError: pass
    p.communicate()
    got = "TIMEOUT"
  exp = expected(f); good = got == exp; ok += good
  if a.v or not good: print(f"{'ok  ' if good else 'FAIL'} {rel}: expected {exp}, got {got}")
print(f"\n{ok}/{len(files)} passed")
sys.exit(0 if ok == len(files) else 1)
