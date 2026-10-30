#!/usr/bin/env python3
"""work-check: mechanical checks for the development workflow.

Subcommands
  snapshot  Print the current snapshot line: HEAD plus a fingerprint of the working
            tree content (tracked and untracked, non-ignored files; ledgers excluded).
            The fingerprint ignores HEAD, staging, and commits, so committing reviewed
            work does not make evidence stale. Only content changes do.
  lint      Check a ledger (default WORK.md) for unfilled placeholders, missing
            fields, ownership/approval gaps, stale snapshot evidence, approval-gate
            violations, an unearned `done`, and ledger storage problems.
            `--as-done` evaluates the done gate whatever Status says.
  storage   Report where the ledger sits relative to version control. With --apply,
            append the ledger path to .git/info/exclude (the only write this tool does).

Standard library only (Python 3.8+). Exit codes: 0 ok (warnings allowed),
1 errors found, 2 usage or environment problem.

This script checks mechanics, not truth. A passing lint means the ledger is
internally consistent and current for the working tree. It does not mean the
recorded commands were run or the review was real. Verdict wording is matched
with simple patterns that catch common negations; it is not natural-language
understanding.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
DEFAULT_LEDGER_EXCLUDES = ["WORK.md", "docs/work"]
STATUSES = ["framing", "ready", "building", "verifying", "review", "blocked", "paused", "done"]
WORKING = {"building", "verifying", "review", "done"}
DEFAULT_BRANCHES = {"main", "master", "trunk", "develop"}
SNAPSHOT_FP_LEN = 16
LITE_FORBIDDEN_GATES = {"G1", "G2", "G4", "G5", "G6"}

# role -> label prefix. A line matches when it looks like "- <label...>: value".
LABELS = {
    "full": {
        "status": "Status", "owner": "Owner", "workspace": "Workspace", "head": "Base",
        "snapshot": "Snapshot", "outcome": "User outcome", "nongoals": "Non-goals",
        "gate": "Gate", "approval": "Approval", "allowed": "Allowed local actions",
        "review": "Independent review", "findings": "Unresolved review findings",
        "remaining": "Remaining verification", "next": "Next action",
        "expected": "Expected observation", "stop": "Stop", "resources": "Live resources",
        "pending": "Pending human decision", "transfer": "Transfer",
    },
    "lite": {
        "status": "Status", "owner": "Owner", "head": "Base HEAD", "snapshot": "Snapshot",
        "goal": "Goal", "nongoals": "Non-goals", "gate": "Gate", "approval": "Approval",
        "preserve": "Preserve", "plan": "Plan", "evidence": "Evidence", "review": "Review",
        "findings": "Open findings", "next": "Next action", "stop": "Stop",
        "resources": "Resources",
    },
}

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
COMMENT = re.compile(r"<!--.*?-->", re.S)
# A placeholder is <text> where text does not begin or end with whitespace, so
# comparisons such as "if n < 3 and m > 2" are not flagged. Put generics such as
# List<String> in backticks.
PLACEHOLDER = re.compile(r"<(?![/!\s])(?!https?://)[^<>\n=\"']+(?<!\s)>")
HTML_OK = {"br", "hr", "kbd", "details", "summary", "p", "b", "i", "em", "strong"}
STATUS_RE = re.compile(r"\s*[*_`]*(" + "|".join(STATUSES) + r")\b", re.I)
FP_RE = re.compile(r"\bfp:([0-9a-f]{12,64})\b")
HEX_REV = re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|specs?)/|(^|/)test_[^/]*$|[_.](test|spec)\.[A-Za-z0-9]+$")
SECRET_RE = re.compile(
    r"\bAKIA[0-9A-Z]{16}\b"
    r"|(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{30,}"
    r"|(?<![A-Za-z0-9])sk-(?=[A-Za-z0-9_-]*[0-9A-Z])[A-Za-z0-9_-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?<![A-Za-z0-9])xox[abp]-[A-Za-z0-9-]{10,}"
)

NEG_APPROVAL = re.compile(
    r"\b(not|never|un|dis)[ -]?approved\b|\b(denied|rejected|declined|refused|revoked|withheld)\b"
    r"|\bnot yet approved\b|\b(awaiting|pending)\s+(owner\s+)?approval\b"
    r"|\bapproval\s+(is\s+)?(pending|required|needed)\b", re.I)
POS_APPROVAL = re.compile(r"\b(self-approved|approved|granted)\b", re.I)
POSITIVE = r"(pass(?:ed|es)?|approved|approval|accepted|lgtm|granted|ok|okay|clean)"
NEG_PASS = re.compile(r"(\bnot\b|\bnever\b|n't\b|\bno\b|\bnothing\b|\bnobody\b|\bun(?:able)?\b|\bcannot\b)[^;,.:]{0,12}\b"
                      + POSITIVE + r"\b", re.I)
# a verdict line that ends in a negator ("approved - no", "approved by owner: no", "approved NOT")
TRAILING_NEG = re.compile(r"\b(no|not|false|nope|never|nobody|none)\W*$", re.I)
# structured negation: "pass: no", "approved? false", "0 passed", "0/3 passed"
POSTFIX_NEG = re.compile(r"\b" + POSITIVE + r"\b\s*[:=?]+\s*\(?\s*(no|false|nope|not|0|n)\b"
                         r"|\b" + POSITIVE + r"\s*\(\s*(no|false|nope|not)\s*\)"
                         r"|\b0\s*(/\s*\d+|of\s+\d+)?\s*" + POSITIVE + r"\b"
                         r"|\b" + POSITIVE + r"\s*[-\u2013]+\s*not\b", re.I)
# hedges and qualifiers: a line that carries one cannot back `done`; reword it into a plain statement
HEDGE = re.compile(
    r"\b(but|except|however|unless|although|though|only|yet|outstanding|unverified|unreviewed|untested|"
    r"unconfirmed|retracted|caveats?|reservations?|subject to|for now|expected to|supposed to|"
    r"would|should|could|might|may|partial(ly)?|incomplete|unfinished|still (open|present|failing|broken)|"
    r"sometimes|flaky|once|stubs?|stubbed|crash(ed|es)?|regressions?|with errors|since changed|"
    r"open (blockers?|issues?|findings?)|blockers? (outstanding|remain\w*))\b", re.I)
VETO_RESULT = re.compile(r"\b(fail(ed|s|ing|ure)?|not run|stale|blocked|unrun)\b", re.I)
VERDICT_POS = re.compile(
    r"\b(pass(ed)?|approved|accepted|lgtm|no (blockers?|blocking( findings?)?|issues?|findings?))\b", re.I)
VERDICT_NEG = re.compile(
    r"\b(reject(ed)?|changes requested|requests? changes|fail(ed|s)?|blocked|do not merge|not approved"
    r"|needs (changes|work)|blockers? (remain\w*|found|open)|blocking[^;.]{0,30}\b(remain\w*|open|found|unresolved)"
    r"|(critical|blocking|serious)\s+(bug|issue|defect|finding)s?)\b", re.I)
# "nothing rejected", "no blockers found", "no blocking findings remain" are positive statements
VERDICT_SAFE = re.compile(
    r"\b(no|nothing|none|zero|without)\b[^;.,]{0,20}\b(reject(ed)?|blockers?|blocking( (findings?|issues?|bugs?))?)\b"
    r"([^;.,]{0,15}\b(remain(s|ing)?|open|found|unresolved)\b)?", re.I)
CLEAN_NONE = re.compile(r"^\s*none\.?\s*(\(\s*(non-?blocking|suggestions?|nits?)\b[^()]*\)\s*\.?)?\s*$", re.I)


# ---------------------------------------------------------------- git helpers

def git(root, *args):
    try:
        p = subprocess.run(
            ["git", "-c", "core.quotepath=off", "-C", root] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return 127, b""
    return p.returncode, p.stdout


def required_git(root, *args):
    rc, out = git(root, *args)
    if rc != 0:
        raise OSError("git %s failed (exit %d)" % (" ".join(args), rc))
    return out


def find_root(arg):
    start = os.path.abspath(arg or os.getcwd())
    rc, out = git(start, "rev-parse", "--show-toplevel")
    if rc == 0 and out.strip():
        return out.decode().strip(), True
    probe = start
    while True:
        if os.path.lexists(os.path.join(probe, ".git")):
            raise OSError("cannot inspect Git repository at %s (git exit %d)" % (probe, rc))
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    return start, False


def resolve_commit(root, rev):
    if not rev:
        return None
    rc, out = git(root, "rev-parse", "--verify", "-q", rev + "^{commit}")
    return out.decode().strip() if rc == 0 and out.strip() else None


def rel_to(root, path):
    r = os.path.relpath(os.path.abspath(path), root)
    return None if r == ".." or r.startswith(".." + os.sep) else r.replace(os.sep, "/")


def is_excluded(rel, excludes):
    return any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in excludes)


def excludes_for(root, ledgers):
    ex = list(DEFAULT_LEDGER_EXCLUDES)
    for l in ledgers or []:
        r = rel_to(root, l)
        if r and r not in ex:
            ex.append(r)
    return ex


# ------------------------------------------------------------------- snapshot

def file_digest(path):
    h = hashlib.sha256()
    if os.path.islink(path):
        h.update(b"link:" + os.readlink(path).encode(errors="surrogateescape"))
        return h.hexdigest()
    if not os.path.isfile(path):  # FIFO, socket, device: opening could hang or lie
        raise OSError("not a regular file: %s" % path)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_lines(path):
    try:
        with open(path, "rb") as f:
            data = f.read(5_000_000)
    except OSError:
        return 0
    if b"\0" in data:
        return 0
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def _walk(root, skip_dirs):
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in skip_dirs)
        for name in sorted(fn):
            full = os.path.join(dp, name)
            yield full, os.path.relpath(full, root).replace(os.sep, "/")


def _enc(s):
    return s.encode(errors="surrogateescape")


def hash_entry(h, tag, rel, full):
    """Fold one path (file, symlink, or directory such as a nested repo) into hash h."""
    if os.path.isdir(full) and not os.path.islink(full):
        for f, r in _walk(full, {".git", "__pycache__"}):
            h.update(tag + b"\0" + _enc(rel + "/" + r) + b"\0-" + file_digest(f).encode() + b"\n")
    elif os.path.lexists(full):
        st = os.lstat(full)
        x = b"x" if (st.st_mode & 0o111) and not os.path.islink(full) else b"-"
        h.update(tag + b"\0" + _enc(rel) + b"\0" + x + file_digest(full).encode() + b"\n")


def snapshot(root, is_repo, excludes, includes=(), base=None):
    """Return dict(head, base, fp, files, lines, repo).

    fp covers the content of every tracked and untracked non-ignored file (excluding
    ledgers) plus any --include paths. It does not depend on HEAD, the index, or commits.
    files and lines count changes against `base` (default HEAD) for the approval-gate
    size check; they are None outside Git.
    """
    h = hashlib.sha256()
    files = set()
    lines = 0
    head = None
    base_rev = None
    if is_repo:
        rc, out = git(root, "rev-parse", "HEAD")
        head = out.decode().strip() if rc == 0 else None
        base_rev = resolve_commit(root, base) or head
        out = required_git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        paths = sorted({p for p in out.decode(errors="surrogateescape").split("\0") if p})
        for rel in paths:
            if not is_excluded(rel, excludes):
                hash_entry(h, b"F", rel, os.path.join(root, rel))
        spec = ["--", "."] + [":(exclude)" + e for e in excludes]
        num = required_git(root, "diff", "--no-renames", "--numstat", base_rev or EMPTY_TREE, *spec)
        for row in num.decode(errors="replace").splitlines():
            parts = row.split("\t")
            if len(parts) == 3:
                files.add(parts[2])
                if not TEST_PATH.search(parts[2]) and parts[0].isdigit() and parts[1].isdigit():
                    lines += int(parts[0]) + int(parts[1])
        un = required_git(root, "ls-files", "-o", "--exclude-standard", "-z")
        for rel in sorted(x for x in un.decode(errors="surrogateescape").split("\0") if x):
            full = os.path.join(root, rel)
            if is_excluded(rel, excludes) or not (os.path.isfile(full) or os.path.islink(full)):
                continue
            files.add(rel)
            if not TEST_PATH.search(rel):
                lines += count_lines(full)
    else:
        skip = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
        for full, rel in _walk(root, skip):
            if not is_excluded(rel, excludes):
                hash_entry(h, b"F", rel, full)
    for inc in includes or ():
        target = os.path.join(root, inc)
        if os.path.isdir(target):
            items = list(_walk(target, {".git", "__pycache__"}))
        elif os.path.exists(target):
            items = [(target, inc)]
        else:
            items = []
        for full, rel in sorted(items, key=lambda x: x[1]):
            h.update(b"I\0" + _enc(rel) + b"\0" + file_digest(full).encode() + b"\n")
    return {
        "head": head, "base": base_rev, "fp": h.hexdigest()[:SNAPSHOT_FP_LEN], "repo": is_repo,
        "files": len(files) if is_repo else None, "lines": lines if is_repo else None,
    }


def fmt_snapshot(s):
    if not s["repo"]:
        return "non-git fp:%s (file manifest)" % s["fp"]
    head = s["head"][:12] if s["head"] else "none"
    base = s["base"][:12] if s["base"] else "empty tree"
    return "HEAD %s fp:%s (%d files, %d non-test lines changed since %s, ledgers excluded)" % (
        head, s["fp"], s["files"], s["lines"], base)


# --------------------------------------------------------------- ledger parse

def field(text, label):
    pat = re.compile(
        r"^[ \t]*[-*][ \t]+\**[ \t]*" + re.escape(label) + r"[^:\n]*:\**[ \t]*(.*)$", re.I | re.M)
    m = pat.search(text)
    return m.group(1).strip() if m else None


def find_placeholders(text):
    out = []
    for m in PLACEHOLDER.finditer(text):
        inner = m.group(0)[1:-1].strip().lower()
        if inner in HTML_OK or not re.search(r"[a-z]", inner):
            continue
        out.append(m.group(0))
    return out


def strip_for_placeholders(text):
    return COMMENT.sub("", INLINE.sub("", FENCE.sub("", text)))


def acceptance_rows(text):
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*([A-Z]{1,3}\d+)\s*\|(.*)\|\s*$", line)
        if m:
            rows.append((m.group(1), m.group(2).split("|")[-1].strip()))
            continue
        m = re.match(r"^\s*[-*]\s+([A-Z]{1,3}\d+)\s*:(.*)$", line)
        if m:
            rest = m.group(2)
            rows.append((m.group(1), rest.split("=>", 1)[1].strip() if "=>" in rest else ""))
    return rows


def hostile(text):
    """True when a verdict-type line carries a negation, structured negation, or hedge."""
    return bool(NEG_PASS.search(text) or POSTFIX_NEG.search(text) or HEDGE.search(text)
                or TRAILING_NEG.search(text))


def count_mismatch(text):
    """'pass (3 of 4)' or '3/4 passed' is partial; '4 of 4' is not."""
    for m in re.finditer(r"\b(\d+)\s*(?:of|/)\s*(\d+)\b", text):
        if m.group(1) != m.group(2):
            return True
    return False


def passed(result):
    cleaned = re.sub(r"\b(0|no|zero|without)\s+(\w+\s+)?(fail\w*|errors?)\b", " ", result, flags=re.I)
    return bool(re.search(r"\bpass(ed|es)?\b", cleaned, re.I)) \
        and not hostile(cleaned) and not VETO_RESULT.search(cleaned) and not count_mismatch(cleaned)


def approval_granted(text):
    """True only for a recorded, unhedged grant such as 'approved by owner 2026-10-24'."""
    text = text or ""
    return bool(not blank(text) and POS_APPROVAL.search(text)
                and not NEG_APPROVAL.search(text) and not hostile(text))


def verdict_ok(review):
    """Return (ok, message). The review line must cite fp (checked elsewhere) and state a plain positive verdict."""
    clean = VERDICT_SAFE.sub(" ", review)
    if VERDICT_NEG.search(clean) or NEG_APPROVAL.search(clean) or hostile(clean) or count_mismatch(clean):
        return False, ("review verdict reads as negative or qualified; state a plain verdict such as 'no blockers' "
                       "(hedges like 'but', 'except', 'only', 'unverified' are rejected)")
    if not VERDICT_POS.search(review):
        return False, "review line must state a verdict such as 'pass' or 'no blockers'"
    return True, ""


def blank(v):
    return v is None or v.strip().lower() in {"", "none", "n/a", "na", "tbd", "unknown"}


def fp_match(recorded, current):
    n = min(len(recorded), len(current))
    return recorded[:n] == current[:n]


def gate_info(gate):
    """Return (triggered, set of G# named as triggers). 'none triggered (checked G1-G6)' is clear."""
    rest = re.sub(r"\b(none|no|not)\s+triggered\b|\bno\s+triggers?\b", "", gate or "", flags=re.I)
    rest = re.sub(r"\bG1\s*(-|–|\.\.)\s*G6\b", "", rest, flags=re.I)
    rest = re.sub(r"\bG[1-6]\s*(\(?\s*(checked|ok|clear|no|n/a)\b\)?|:\s*(no|none|ok|clear)\b)", "", rest, flags=re.I)
    hits = {m.upper() for m in re.findall(r"\bG[1-6]\b", rest, re.I)}
    return bool(hits) or bool(re.search(r"\btriggered\b", rest, re.I)), hits


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


# -------------------------------------------------------------------- storage

def storage_state(root, is_repo, ledger):
    """Return (state, branch). state: non-git | tracked | ignored | visible | outside."""
    if not is_repo:
        return "non-git", None
    rel = rel_to(root, ledger)
    if rel is None:
        return "outside", None
    rc, out = git(root, "symbolic-ref", "--short", "-q", "HEAD")
    branch = out.decode().strip() if rc == 0 else None
    if git(root, "ls-files", "--error-unmatch", "--", ":(literal)" + rel)[0] == 0:
        return "tracked", branch
    if git(root, "check-ignore", "--no-index", "-q", "--", rel)[0] == 0:
        return "ignored", branch
    return "visible", branch


def default_branches(root):
    names = set(DEFAULT_BRANCHES)
    rc, out = git(root, "symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD")
    if rc == 0 and out.strip():
        names.add(out.decode().strip().split("/", 1)[-1])
    return names


def exclude_line(rel):
    """Anchored, glob-escaped .git/info/exclude pattern for one literal path."""
    esc = re.sub(r"([\\*?\[\]])", r"\\\1", rel)  # the leading "/" already makes # and ! literal
    if esc.endswith(" "):
        esc = esc[:-1] + "\\ "
    return "/" + esc


# ------------------------------------------------------------------------ lint

def lint_contract(path, allow_ph):
    errs, warns = [], []
    text = read_text(path)
    m = re.search(r"^##\s+Repository map[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    if not m:
        errs.append("no '## Repository map...' section found (is this the operating contract?)")
    else:
        ph = find_placeholders(strip_for_placeholders(m.group(1)))
        if ph:
            (warns if allow_ph else errs).append(
                "%d unfilled placeholder(s) in the repository map, e.g. %s" % (len(ph), ", ".join(ph[:3])))
        rec = re.search(r"Command recipe last exercised:\s*(.*)", m.group(1))
        if rec and re.search(r"\b(never|not run|unknown)\b", rec.group(1), re.I):
            warns.append("command recipe is recorded as not exercised; do not call commands proven")
    for needle in ("Authority", "Verify and obtain independent review"):
        if needle not in text:
            errs.append("contract section missing: %s" % needle)
    return errs, warns


def lint_ledger(path, root, is_repo, tier, max_files, max_lines, allow_ph, includes,
                as_done=False, secret_scan=True):
    errs, warns = [], []
    try:
        raw = read_text(path)
    except OSError as e:
        return ["cannot read %s: %s" % (path, e)], [], tier
    if tier == "auto":
        m = re.search(r"<!--\s*tier:\s*(lite|full)\s*-->", raw, re.I)
        tier = m.group(1).lower() if m else "full"
    nofence = FENCE.sub("", raw)
    spec = LABELS[tier]
    vals = {role: field(nofence, label) for role, label in spec.items()}
    for role, label in spec.items():
        if vals[role] is None:
            errs.append("missing field '%s:' (%s ledger)" % (label, tier))

    status = None
    if vals["status"] is not None:
        m = STATUS_RE.match(vals["status"])
        if m:
            status = m.group(1).lower()
        else:
            errs.append("Status must start with one of: %s (found %r)" % (", ".join(STATUSES), vals["status"][:40]))
    eff = "done" if as_done else status  # status used for every gate below

    ph = find_placeholders(strip_for_placeholders(raw))
    if ph:
        msg = "%d unfilled placeholder(s), e.g. %s" % (len(ph), ", ".join(ph[:3]))
        (warns if allow_ph or eff == "framing" else errs).append(msg)

    if secret_scan and SECRET_RE.search(raw):
        errs.append("text looks like a credential or private key; ledgers must not contain secrets "
                    "(use --no-secret-scan only after confirming it is a false positive)")

    owner = vals.get("owner")
    if owner is not None and not re.search(r"\b(active|released)\b", owner, re.I):
        warns.append("Owner should say 'active' or 'released'")
    if owner and eff in ("paused", "done") and re.search(r"\bactive\b", owner, re.I) \
            and not re.search(r"\breleased\b", owner, re.I):
        warns.append("status is %s but Owner is still marked active" % eff)

    nxt = vals.get("next")
    if eff and eff != "done" and nxt is not None and blank(nxt):
        errs.append("Next action is empty; leave one exact executable action")

    # approval gate
    approval = vals.get("approval") or ""
    gate = vals.get("gate") or ""
    gate_triggered, gate_hits = gate_info(gate)
    self_approved = bool(re.search(r"self-approved", approval, re.I))
    if eff in WORKING:
        if vals.get("approval") is not None and not approval_granted(approval):
            errs.append("status is %s but Approval is not recorded as granted" % eff)
        if gate_triggered and self_approved:
            errs.append("Gate says a trigger fired but Approval is self-approved; a triggered gate needs owner approval")
        if tier == "lite" and gate_hits & LITE_FORBIDDEN_GATES:
            errs.append("lite ledger with trigger(s) %s; use the full ledger (templates/WORK.md)"
                        % ", ".join(sorted(gate_hits & LITE_FORBIDDEN_GATES)))

    # snapshot, size, evidence
    head_field = vals.get("head") or ""
    revs = HEX_REV.findall(head_field)
    base = next((r for r in (resolve_commit(root, t) for t in revs) if r), None) if is_repo else None
    if is_repo and revs and not base:
        warns.append("recorded Base HEAD %s not found in this repository; size check uses HEAD" % revs[0])
    elif is_repo and not revs and not blank(head_field) and not re.search(r"<", head_field):
        warns.append("Base HEAD has no commit hash (%r); size check uses HEAD, so committed work is not counted"
                     % head_field[:30])
    snap = None
    try:
        snap = snapshot(root, is_repo, excludes_for(root, [path]), includes, base)
    except Exception as e:  # defensive: never let lint crash on odd repos
        (errs if eff in ("review", "done") else warns).append(
            "could not compute snapshot, so evidence cannot be checked: %s" % e)
    if snap:
        if eff in WORKING and is_repo and (snap["files"] > max_files or snap["lines"] > max_lines):
            detail = "%d files / %d lines (limits %d / %d)" % (snap["files"], snap["lines"], max_files, max_lines)
            if self_approved and not gate_triggered:
                errs.append("approval gate G3 now exceeded: %s under a self-approved task; "
                            "get owner approval or split the task" % detail)
            elif tier == "lite":
                errs.append("lite ledger exceeds the G3 limits: %s; use the full ledger" % detail)
        rec_m = FP_RE.search(vals.get("snapshot") or "")
        rec = rec_m.group(1) if rec_m else None
        strict = eff in ("review", "done")
        soft = eff == "verifying"
        if strict or soft:
            bucket = errs if strict else warns
            rel = rel_to(root, path)
            flag = "" if rel is None or is_excluded(rel, DEFAULT_LEDGER_EXCLUDES) else " --ledger " + rel
            if rec is None:
                bucket.append("Snapshot has no fp:<hex>; run `work-check.py snapshot%s` and record it" % flag)
            elif not fp_match(rec, snap["fp"]):
                bucket.append("recorded snapshot fp:%s is stale (working tree is fp:%s); re-verify, then re-record "
                              "with `work-check.py snapshot%s`" % (rec[:SNAPSHOT_FP_LEN], snap["fp"], flag))

    # done gate
    if eff == "done":
        rows = acceptance_rows(nofence)
        if not rows:
            errs.append("done: no acceptance rows (A1, A2, ...) found")
        for rid, res in rows:
            if not passed(res):
                errs.append("done: acceptance %s is not recorded as pass (%r)" % (rid, res[:40]))
        rv = vals.get("review") or ""
        if blank(rv) or re.search(r"\bnot (independently )?reviewed\b|\bpending\b", rv, re.I):
            errs.append("done: no independent review recorded")
        else:
            rm = FP_RE.search(rv)
            if not rm:
                errs.append("done: review line must cite the reviewed snapshot as fp:<hex>")
            elif snap and not fp_match(rm.group(1), snap["fp"]):
                errs.append("done: review covers fp:%s but the working tree is fp:%s; re-review"
                            % (rm.group(1)[:SNAPSHOT_FP_LEN], snap["fp"]))
            ok, why = verdict_ok(rv)
            if not ok:
                errs.append("done: " + why)
        for role, name in (("findings", "open review findings"), ("remaining", "Remaining verification")):
            if role not in vals:
                continue
            v = vals.get(role) or ""
            if not CLEAN_NONE.match(v):
                errs.append("done: %s must be exactly 'none', optionally followed by a parenthetical "
                            "'(nonblocking: ...)' (found %r)" % (name, v[:50]))
        if re.search(r"^\s*[-*]\s+\[ \]", nofence, re.M):
            errs.append("done: plan still has unchecked slices")

    # storage
    if is_repo:
        state, branch = storage_state(root, is_repo, path)
        if state == "tracked" and branch in default_branches(root):
            warns.append("ledger is tracked on default branch '%s'; keep it local or on a task branch only" % branch)
        elif state == "visible":
            warns.append("ledger is untracked and not excluded; run `work-check.py storage --apply` "
                         "(local default) or commit it on the task branch (cross-machine handoff)")
    return errs, warns, tier


# ------------------------------------------------------------------------- cli

def report(label, errs, warns):
    for w in warns:
        print("WARN:  " + w)
    for e in errs:
        print("ERROR: " + e)
    print("%s: %d error(s), %d warning(s)" % (label, len(errs), len(warns)))
    return 1 if errs else 0


def bad_includes(root, includes):
    problems = []
    for inc in includes:
        rel = rel_to(root, os.path.join(root, inc))
        if rel is None or os.path.isabs(inc):
            problems.append("--include %s is outside the repository" % inc)
        elif not os.path.exists(os.path.join(root, inc)):
            problems.append("--include %s does not exist" % inc)
    return problems


def cmd_snapshot(a):
    root, repo = find_root(a.root)
    problems = bad_includes(root, a.include)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 2
    ledgers = [l if os.path.isabs(l) else os.path.join(root, l) for l in a.ledger]
    s = snapshot(root, repo, excludes_for(root, ledgers), a.include, a.base)
    print(fmt_snapshot(s))
    return 0


def cmd_lint(a):
    root, repo = find_root(a.root)
    path = os.path.abspath(os.path.join(root, a.ledger or "WORK.md"))
    if not os.path.exists(path):
        print("no such file: %s" % path, file=sys.stderr)
        return 2
    problems = bad_includes(root, a.include)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 2
    if os.path.basename(path).upper().startswith("AGENTS"):
        errs, warns = lint_contract(path, a.allow_placeholders)
        return report("contract", errs, warns)
    errs, warns, tier = lint_ledger(path, root, repo, a.tier, a.max_files, a.max_lines,
                                    a.allow_placeholders, a.include, a.as_done, not a.no_secret_scan)
    return report("%s (%s ledger)" % (os.path.relpath(path, root), tier), errs, warns)


def cmd_storage(a):
    root, repo = find_root(a.root)
    path = os.path.abspath(os.path.join(root, a.ledger or "WORK.md"))
    state, branch = storage_state(root, repo, path)
    rel = rel_to(root, path)
    msgs = {
        "non-git": "not a Git repository: the ledger is just a file in the workspace",
        "outside": "ledger is outside the repository",
        "tracked": "tracked by Git (branch %s)" % branch,
        "ignored": "untracked and excluded from Git: the local default",
        "visible": "untracked but visible to Git: could be committed by accident",
    }
    print("%s: %s" % (rel or path, msgs[state]))
    if state == "tracked" and branch in default_branches(root):
        print("WARN:  tracked on default branch; remove it before merge (git rm --cached) or move work to a task branch")
    if a.apply:
        if state != "visible":
            print("nothing to apply")
            return 0
        rc, out = git(root, "rev-parse", "--git-path", "info/exclude")
        if rc != 0:
            print("could not locate .git/info/exclude", file=sys.stderr)
            return 2
        target = out.decode().strip()
        target = target if os.path.isabs(target) else os.path.join(root, target)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        existing = read_text(target) if os.path.exists(target) else ""
        line = exclude_line(rel)
        if line not in existing.splitlines():
            with open(target, "a", encoding="utf-8") as f:
                f.write(("" if existing.endswith("\n") or not existing else "\n") + line + "\n")
        print("added %s to %s" % (line, target))
    elif state == "visible":
        print("run with --apply to exclude it locally")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="work-check", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("snapshot", help="print HEAD + working-tree fingerprint")
    s.add_argument("--root")
    s.add_argument("--ledger", action="append", default=[],
                   help="ledger path outside WORK.md and docs/work/ to exclude (repeatable)")
    s.add_argument("--include", action="append", default=[],
                   help="extra ignored/generated path the evidence depends on (repeatable)")
    s.add_argument("--base", help="revision to count size changes against (default HEAD)")
    s.set_defaults(fn=cmd_snapshot)

    l = sub.add_parser("lint", help="check a ledger (default WORK.md) or an AGENTS.md contract")
    l.add_argument("ledger", nargs="?")
    l.add_argument("--root")
    l.add_argument("--tier", choices=["auto", "lite", "full"], default="auto")
    l.add_argument("--as-done", action="store_true", help="evaluate the done gate whatever Status says")
    l.add_argument("--max-files", type=int, default=3, help="approval gate G3 file limit (default 3)")
    l.add_argument("--max-lines", type=int, default=100, help="approval gate G3 changed-line limit (default 100)")
    l.add_argument("--allow-placeholders", action="store_true", help="downgrade placeholders to warnings")
    l.add_argument("--no-secret-scan", action="store_true", help="skip the credential heuristic (false positives)")
    l.add_argument("--include", action="append", default=[], help="extra path to fold into the fingerprint")
    l.set_defaults(fn=cmd_lint)

    st = sub.add_parser("storage", help="report or fix where the ledger lives")
    st.add_argument("ledger", nargs="?")
    st.add_argument("--root")
    st.add_argument("--apply", action="store_true", help="append the ledger to .git/info/exclude")
    st.set_defaults(fn=cmd_storage)

    a = p.parse_args(argv)
    if getattr(a, "root", None) and not os.path.isdir(a.root):
        print("--root %s is not a directory" % a.root, file=sys.stderr)
        return 2
    try:
        return a.fn(a)
    except BrokenPipeError:
        return 0
    except OSError as e:
        print("cannot inspect workspace: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
