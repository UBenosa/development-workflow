#!/usr/bin/env python3
"""Mutation check for work-check.py: break the script on purpose and confirm the tests notice.

Usage: python3 scripts/mutation_check.py [--jobs N]

Each mutant is one named, literal replacement in a scratch COPY of scripts/ and templates/
(the originals are never modified). A mutant is CAUGHT when the test suite fails on it.
A mutant whose search text no longer matches exactly once is reported as STALE: update the
list when work-check.py is refactored. Exit 0 only if every mutant is CAUGHT.
The unchanged suite must pass first. A failed or timed-out baseline stops the run
before any mutants are evaluated.

This shows the tests detect these specific breakages. It does not show the wording
patterns cover real-world phrasing. Takes a few minutes (the suite runs once per mutant).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
SRC = open(os.path.join(HERE, "work-check.py"), encoding="utf-8").read()

MUTANTS = [
    ("fingerprint ignores file content", "    elif os.path.lexists(full):\n        st = os.lstat(full)", "    elif False:\n        st = os.lstat(full)"),
    ("fingerprint ignores exec bit", 'x = b"x" if (st.st_mode & 0o111) and not os.path.islink(full) else b"-"', 'x = b"-"'),
    ("fingerprint follows symlinks", "    if os.path.islink(path):\n        h.update(", "    if False:\n        h.update("),
    ("fingerprint includes HEAD", "h = hashlib.sha256()\n    files = set()", 'h = hashlib.sha256()\n    h.update(subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True).stdout)\n    files = set()'),
    ("nested repositories skipped", "    if os.path.isdir(full) and not os.path.islink(full):\n        for f, r in _walk(full", "    if False:\n        for f, r in _walk(full"),
    ("special files opened instead of failing", "    if not os.path.isfile(path):  # FIFO, socket, device: opening could hang or lie", "    if False:"),
    ("stale snapshot check disabled", 'elif not fp_match(rec, snap["fp"]):\n                bucket.append', 'elif False:\n                bucket.append'),
    ("review fingerprint mismatch ignored", 'elif snap and not fp_match(rm.group(1), snap["fp"]):', "elif False:"),
    ("snapshot failure fails open", '(errs if eff in ("review", "done") else warns).append(\n            "could not compute snapshot', 'warns.append(\n            "could not compute snapshot'),
    ("environment errors escape", 'except OSError as e:\n        print("cannot inspect workspace: %s" % e, file=sys.stderr)\n        return 2', 'except ZeroDivisionError:\n        return 2'),
    ("missing git binary not detected", 'if os.path.lexists(os.path.join(probe, ".git")):', "if False:"),
    ("negators ignored", "return bool(NEG_PASS.search(text) or POSTFIX_NEG.search(text)", "return bool(POSTFIX_NEG.search(text)"),
    ("structured negation ignored", "or POSTFIX_NEG.search(text) or HEDGE.search(text)", "or HEDGE.search(text)"),
    ("hedges ignored", "or HEDGE.search(text)\n                or TRAILING_NEG.search(text))", "\n                or TRAILING_NEG.search(text))"),
    ("trailing negator ignored", "\n                or TRAILING_NEG.search(text))", ")"),
    ("positive-safe phrases not stripped", 'clean = VERDICT_SAFE.sub(" ", review)', "clean = review"),
    ("blocking-remains pattern removed", '|blocking[^;.]{0,30}\\b(remain\\w*|open|found|unresolved)"', '"'),
    ("partial counts allowed", "and not hostile(cleaned) and not VETO_RESULT.search(cleaned) and not count_mismatch(cleaned)", "and not hostile(cleaned) and not VETO_RESULT.search(cleaned)"),
    ("acceptance negation ignored", "and not hostile(cleaned) and not VETO", "and not VETO"),
    ("zero-failure phrasing rejected", 'cleaned = re.sub(r"\\b(0|no|zero|without)\\s+(\\w+\\s+)?(fail\\w*|errors?)\\b", " ", result, flags=re.I)', "cleaned = result"),
    ("approval check reduced to non-blank", 'if vals.get("approval") is not None and not approval_granted(approval):', 'if vals.get("approval") is not None and blank(approval):'),
    ("positive verdict not required", "    if not VERDICT_POS.search(review):", "    if False:"),
    ("review pending accepted", 'or re.search(r"\\bnot (independently )?reviewed\\b|\\bpending\\b", rv, re.I):', 'or re.search(r"\\bnot (independently )?reviewed\\b", rv, re.I):'),
    ("findings need only start with none", "            if not CLEAN_NONE.match(v):", '            if not re.match(r"\\s*none\\b", v, re.I):'),
    ("non-A# acceptance ids ignored", "([A-Z]{1,3}\\d+)\\s*\\|(.*)\\|", "(A\\d+)\\s*\\|(.*)\\|"),
    ("unchecked slices ignored", 'if re.search(r"^\\s*[-*]\\s+\\[ \\]", nofence, re.M):', "if False:"),
    ("gate 'G3 checked' read as trigger", 'rest = re.sub(r"\\bG[1-6]\\s*(\\(?\\s*(checked|ok|clear|no|n/a)\\b\\)?|:\\s*(no|none|ok|clear)\\b)", "", rest, flags=re.I)', "pass"),
    ("lite ledger may record G1/G2/G4/G5/G6", 'if tier == "lite" and gate_hits & LITE_FORBIDDEN_GATES:', "if False:"),
    ("lite ledger may exceed G3 under owner approval", '            elif tier == "lite":\n                errs.append("lite ledger exceeds', '            elif False:\n                errs.append("lite ledger exceeds'),
    ("G3 counts against HEAD, not Base HEAD", "base_rev = resolve_commit(root, base) or head", "base_rev = head"),
    ("tracked test files counted in G3 lines", "if not TEST_PATH.search(parts[2]) and parts[0].isdigit()", "if parts[0].isdigit()"),
    ("untracked test files counted in G3 lines", "            if not TEST_PATH.search(rel):\n                lines += count_lines(full)", "            lines += count_lines(full)"),
    ("Base HEAD without a hash not warned", 'warns.append("Base HEAD has no commit hash', 'None and warns.append("Base HEAD has no commit hash'),
    ("Owner warning removed", 'warns.append("Owner should say \'active\' or \'released\'")', "pass"),
    ("empty Next action allowed", 'errs.append("Next action is empty; leave one exact executable action")', "pass"),
    ("credential lookahead removed", "(?=[A-Za-z0-9_-]*[0-9A-Z])", ""),
    ("storage trailing-space escape removed", 'if esc.endswith(" "):', "if False:"),
]


def run_one(item):
    i, (name, old, new) = item
    if SRC.count(old) != 1:
        return name, "STALE (search text matches %d times)" % SRC.count(old)
    tmp = tempfile.mkdtemp(prefix="mutant-%d-" % i)
    try:
        shutil.copytree(os.path.join(KIT, "scripts"), os.path.join(tmp, "scripts"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(KIT, "templates"), os.path.join(tmp, "templates"))
        with open(os.path.join(tmp, "scripts", "work-check.py"), "w", encoding="utf-8") as f:
            f.write(SRC.replace(old, new))
        p = subprocess.run([sys.executable, "-B", "-m", "unittest", "scripts/test_work_check.py"], cwd=tmp,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900)
        failing = [l for l in p.stderr.splitlines() if l.startswith(("FAIL:", "ERROR:"))]
        return name, ("CAUGHT (%d failing)" % len(failing)) if p.returncode else "MISSED"
    except subprocess.TimeoutExpired:
        return name, "TIMEOUT"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    print("Checking unchanged test baseline...", flush=True)
    try:
        baseline = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "scripts/test_work_check.py"], cwd=KIT,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        print("Baseline timed out; no mutants were run.")
        return 1
    print(baseline.stdout, end="")
    if baseline.returncode != 0:
        print("Baseline failed; no mutants were run.")
        return 1
    print("Baseline passed.", flush=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(run_one, enumerate(MUTANTS)))
    for name, res in results:
        print("%-52s %s" % (name, res))
    bad = [n for n, r in results if not r.startswith("CAUGHT")]
    print("\n%d mutants, %d caught, not caught: %s" % (len(results), len(results) - len(bad), bad or "none"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
