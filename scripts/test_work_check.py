#!/usr/bin/env python3
"""Tests for work-check.py. Standard library only: python3 -m unittest scripts/test_work_check.py

Each test builds a throwaway Git repository in a temp directory; nothing outside it is touched.
"""
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "work-check.py")
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")

LITE_OK = """<!-- tier: lite -->
# Work (lite): clamp remaining quota at zero

- Status: {status}
- Owner: agent-a; released
- Base HEAD: {head}
- Snapshot: {snap}
- Goal: remaining_quota(10, 13) returns 0
- Non-goals: input validation
- Gate: none triggered (checked G1-G6)
- Approval: {approval}
- Preserve: none
- Plan: inspect -> red -> fix -> verify -> review

## Acceptance

- A1: overuse regression test => {a1}

## State

- Evidence: python -m unittest in repo root, exit 0
- Review: {review}
- Open findings: {findings}
- Next action: run python -m unittest and confirm exit 0
- Stop: any unapproved external action
- Resources: none
"""


def run(args, cwd, expect=None):
    p = subprocess.run([sys.executable, "-I", SCRIPT] + args, cwd=cwd,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if expect is not None and p.returncode != expect:
        raise AssertionError("exit %s != %s\n%s" % (p.returncode, expect, p.stdout))
    return p


def sh(cwd, *cmd):
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def fp_of(cwd):
    out = run(["snapshot"], cwd, 0).stdout
    return re.search(r"fp:([0-9a-f]+)", out).group(1), re.search(r"HEAD (\w+)", out).group(1)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="work-check-test-")
        self.addCleanup(shutil.rmtree, self.d, True)
        sh(self.d, "git", "init", "-q", "-b", "task-branch")
        sh(self.d, "git", "config", "user.email", "t@example.invalid")
        sh(self.d, "git", "config", "user.name", "t")
        self.write("quota.py", "def remaining_quota(l, u):\n    return l - u\n")
        sh(self.d, "git", "add", "quota.py")
        sh(self.d, "git", "commit", "-q", "-m", "init")

    def write(self, name, text):
        path = os.path.join(self.d, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def read(self, name):
        with open(os.path.join(self.d, name)) as f:
            return f.read()

    def ledger(self, **kw):
        vals = dict(status="building", head="x", snap="none yet", approval="self-approved small task",
                    a1="not run", review="not independently reviewed", findings="none")
        vals.update(kw)
        self.write("WORK.md", LITE_OK.format(**vals))


class Snapshot(Base):
    def test_ledger_edits_do_not_change_fingerprint(self):
        self.write("quota.py", "def remaining_quota(l, u):\n    return max(0, l - u)\n")
        self.ledger()
        before, _ = fp_of(self.d)
        self.ledger(a1="pass; evidence")
        self.assertEqual(before, fp_of(self.d)[0])

    def test_tracked_and_untracked_changes_change_fingerprint(self):
        base, _ = fp_of(self.d)
        self.write("quota.py", "def remaining_quota(l, u):\n    return max(0, l - u)\n")
        edited, _ = fp_of(self.d)
        self.assertNotEqual(base, edited)
        self.write("notes/extra.txt", "x\n")
        self.assertNotEqual(edited, fp_of(self.d)[0])

    def test_deterministic(self):
        self.write("a.txt", "1\n")
        self.assertEqual(fp_of(self.d), fp_of(self.d))

    def test_include_folds_ignored_file_into_fingerprint(self):
        self.write(".gitignore", "gen.bin\n")
        self.write("gen.bin", "v1")
        plain = run(["snapshot"], self.d, 0).stdout
        a = run(["snapshot", "--include", "gen.bin"], self.d, 0).stdout
        self.write("gen.bin", "v2")
        b = run(["snapshot", "--include", "gen.bin"], self.d, 0).stdout
        self.assertNotEqual(a, b)
        self.assertEqual(plain, run(["snapshot"], self.d, 0).stdout)

    def test_non_git_directory(self):
        d = tempfile.mkdtemp(prefix="work-check-nogit-")
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "f.txt"), "w") as f:
            f.write("x")
        out = run(["snapshot", "--root", d], "/", 0).stdout
        self.assertIn("non-git", out)


class Lint(Base):
    def test_unfilled_templates_fail(self):
        for name in ("WORK-lite.md", "WORK.md"):
            shutil.copy(os.path.join(TEMPLATES, name), os.path.join(self.d, "WORK.md"))
            p = run(["lint"], self.d, 1)
            self.assertIn("Status must start with", p.stdout, name)
            self.assertIn("unfilled placeholder", p.stdout, name)

    def test_full_template_has_every_required_field(self):
        shutil.copy(os.path.join(TEMPLATES, "WORK.md"), os.path.join(self.d, "WORK.md"))
        self.assertNotIn("missing field", run(["lint"], self.d).stdout)

    def test_lite_template_has_every_required_field(self):
        shutil.copy(os.path.join(TEMPLATES, "WORK-lite.md"), os.path.join(self.d, "WORK.md"))
        self.assertNotIn("missing field", run(["lint"], self.d).stdout)

    def test_building_with_valid_ledger_passes(self):
        self.ledger()
        run(["storage", "--apply"], self.d, 0)
        p = run(["lint"], self.d, 0)
        self.assertIn("0 error(s)", p.stdout)

    def test_missing_field_is_reported(self):
        self.ledger()
        text = self.read("WORK.md").replace("- Stop: any unapproved external action\n", "")
        self.write("WORK.md", text)
        self.assertIn("missing field 'Stop:'", run(["lint"], self.d, 1).stdout)

    def test_pending_approval_blocks_building(self):
        self.ledger(approval="not yet approved")
        self.assertIn("Approval is not recorded as granted", run(["lint"], self.d, 1).stdout)

    def test_triggered_gate_cannot_be_self_approved(self):
        self.ledger()
        text = self.read("WORK.md").replace(
            "none triggered (checked G1-G6)", "triggered: G1 changes public CLI flag")
        self.write("WORK.md", text)
        self.assertIn("self-approved", run(["lint"], self.d, 1).stdout)

    def test_g3_growth_is_caught_for_self_approved_task(self):
        self.ledger()
        for i in range(4):
            self.write("mod%d.py" % i, "x = %d\n" % i)
        out = run(["lint"], self.d, 1).stdout
        self.assertIn("gate G3 now exceeded", out)
        self.assertEqual(run(["lint", "--max-files", "10"], self.d).stdout.count("G3"), 0)

    def test_secret_like_text_is_an_error(self):
        self.ledger()
        with open(os.path.join(self.d, "WORK.md"), "a") as f:
            f.write("- note: AKIAABCDEFGHIJKLMNOP\n")
        self.assertIn("credential", run(["lint"], self.d, 1).stdout)

    def test_inline_code_is_not_a_placeholder(self):
        self.ledger()
        with open(os.path.join(self.d, "WORK.md"), "a") as f:
            f.write("- note: type is `List<String>` here\n")
        self.assertNotIn("placeholder", run(["lint"], self.d).stdout)


class DoneGate(Base):
    def done_ledger(self, **kw):
        fp, head = fp_of(self.d)
        vals = dict(status="done", head=head, snap="HEAD %s fp:%s" % (head, fp), a1="pass; exit 0",
                    review="reviewer-b fresh context, fp:%s, no blockers" % fp, findings="none")
        vals.update(kw)
        self.ledger(**vals)
        return fp

    def setUp(self):
        super().setUp()
        self.write("quota.py", "def remaining_quota(l, u):\n    return max(0, l - u)\n")

    def test_done_passes_when_everything_matches(self):
        self.done_ledger()
        run(["storage", "--apply"], self.d, 0)
        p = run(["lint"], self.d)
        self.assertNotIn("ERROR", p.stdout, p.stdout)
        self.assertEqual(p.returncode, 0)

    def test_done_requires_review(self):
        self.done_ledger(review="not independently reviewed")
        self.assertIn("no independent review", run(["lint"], self.d, 1).stdout)

    def test_done_requires_passing_acceptance(self):
        self.done_ledger(a1="not run")
        self.assertIn("acceptance A1 is not recorded as pass", run(["lint"], self.d, 1).stdout)

    def test_done_rejects_open_findings(self):
        self.done_ledger(findings="blocking: missing test")
        self.assertIn("open review findings", run(["lint"], self.d, 1).stdout)

    def test_code_change_after_review_makes_evidence_stale(self):
        self.done_ledger()
        self.write("quota.py", "def remaining_quota(l, u):\n    return max(0, l - u) + 0\n")
        out = run(["lint"], self.d, 1).stdout
        self.assertIn("is stale", out)
        self.assertIn("re-review", out)

    def test_committing_does_not_make_evidence_stale(self):
        self.done_ledger()
        before = fp_of(self.d)[0]
        sh(self.d, "git", "add", "quota.py")
        sh(self.d, "git", "commit", "-q", "-m", "fix")
        self.assertEqual(before, fp_of(self.d)[0])
        self.assertEqual(run(["lint"], self.d).returncode, 0)

    def test_committing_the_ledger_for_handoff_does_not_make_evidence_stale(self):
        self.done_ledger()
        before = fp_of(self.d)[0]
        sh(self.d, "git", "add", "-f", "WORK.md", "quota.py")
        sh(self.d, "git", "commit", "-q", "-m", "handoff")
        self.assertEqual(before, fp_of(self.d)[0])
        self.assertNotIn("stale", run(["lint"], self.d).stdout)

    def test_staging_does_not_change_fingerprint(self):
        self.write("new.py", "x = 1\n")
        before = fp_of(self.d)[0]
        sh(self.d, "git", "add", "new.py")
        self.assertEqual(before, fp_of(self.d)[0])

    def test_review_must_cite_fingerprint(self):
        self.done_ledger(review="reviewer-b, no blockers")
        self.assertIn("must cite the reviewed snapshot", run(["lint"], self.d, 1).stdout)


class Storage(Base):
    def test_visible_then_excluded_and_idempotent(self):
        self.ledger()
        self.assertIn("visible to Git", run(["storage"], self.d, 0).stdout)
        self.assertIn("warn", run(["lint"], self.d).stdout.lower())
        run(["storage", "--apply"], self.d, 0)
        run(["storage", "--apply"], self.d, 0)
        self.assertIn("excluded from Git", run(["storage"], self.d, 0).stdout)
        with open(os.path.join(self.d, ".git", "info", "exclude")) as f:
            self.assertEqual(f.read().splitlines().count("/WORK.md"), 1)
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=self.d, stdout=subprocess.PIPE,
                                        text=True).stdout.strip(), "")

    def test_tracked_on_default_branch_warns(self):
        sh(self.d, "git", "checkout", "-q", "-b", "main")
        self.ledger()
        sh(self.d, "git", "add", "WORK.md")
        sh(self.d, "git", "commit", "-q", "-m", "ledger")
        self.assertIn("tracked on default branch", run(["lint"], self.d).stdout)

    def test_tracked_on_task_branch_is_allowed(self):
        self.ledger()
        sh(self.d, "git", "add", "WORK.md")
        sh(self.d, "git", "commit", "-q", "-m", "ledger")
        self.assertNotIn("default branch", run(["lint"], self.d).stdout)


class Contract(Base):
    def test_unfilled_contract_fails_and_filled_passes(self):
        shutil.copy(os.path.join(TEMPLATES, "AGENTS.md"), os.path.join(self.d, "AGENTS.md"))
        self.assertIn("unfilled placeholder", run(["lint", "AGENTS.md"], self.d, 1).stdout)
        text = self.read("AGENTS.md")
        text = re.sub(r"<[^<>\n]+>", "filled", text)
        self.write("AGENTS.md", text)
        self.assertEqual(run(["lint", "AGENTS.md"], self.d).returncode, 0)


class Negations(Base):
    """Plain negations must not satisfy the done gate (reviewer findings)."""

    def setUp(self):
        super().setUp()
        self.write("quota.py", "def remaining_quota(l, u):\n    return max(0, l - u)\n")

    def done(self, **kw):
        fp, head = fp_of(self.d)
        vals = dict(status="done", head=head, snap="HEAD %s fp:%s" % (head, fp), a1="pass; exit 0",
                    review="reviewer-b, fp:%s, no blockers" % fp, findings="none")
        vals.update(kw)
        self.ledger(**vals)
        return run(["lint"], self.d)

    def test_baseline_done_passes(self):
        self.assertEqual(self.done().returncode, 0)

    def test_negated_approvals_are_rejected(self):
        for text in ("not approved", "owner denied", "unapproved", "approval pending", "rejected by owner"):
            self.assertEqual(self.done(approval=text).returncode, 1, text)

    def test_approval_with_unrelated_pending_text_is_accepted(self):
        self.assertEqual(self.done(approval="approved by owner 2026-10-24; follow-up pending").returncode, 0)

    def test_negated_pass_is_rejected(self):
        for text in ("does not pass; python -m unittest", "never passed", "did not pass", "pass but not run in CI"):
            self.assertEqual(self.done(a1=text).returncode, 1, text)

    def test_negative_review_verdicts_are_rejected(self):
        fp = fp_of(self.d)[0]
        for text in ("reviewer-b REJECTED, changes requested, fp:%s" % fp, "reviewer-b fp:%s blockers remain" % fp):
            self.assertEqual(self.done(review=text).returncode, 1, text)

    def test_mixed_positive_and_negative_verdict_is_rejected(self):
        fp = fp_of(self.d)[0]
        for text in ("reviewer-b fp:%s approved in part but changes requested" % fp,
                     "reviewer-b fp:%s no issues in style, REJECTED on correctness" % fp):
            out = self.done(review=text)
            self.assertEqual(out.returncode, 1, text)
            self.assertIn("reads as negative", out.stdout, text)

    def test_review_without_verdict_is_rejected(self):
        fp = fp_of(self.d)[0]
        self.assertEqual(self.done(review="reviewer-b looked at it, fp:%s" % fp).returncode, 1)

    def test_findings_must_be_clean_none(self):
        self.assertEqual(self.done(findings="none, but blocking bug in parser remains").returncode, 1)
        self.assertEqual(self.done(findings="none (nonblocking: rename helper)").returncode, 0)

    def test_gate_trigger_hidden_after_none_is_still_a_trigger(self):
        self.ledger(status="building")
        text = self.read("WORK.md").replace("none triggered (checked G1-G6)",
                                            "none triggered, except G4 triggered (auth)")
        self.write("WORK.md", text)
        self.assertIn("self-approved", run(["lint"], self.d, 1).stdout)

    def test_bold_status_is_accepted(self):
        self.ledger(status="**building**")
        self.assertNotIn("Status must start with", run(["lint"], self.d).stdout)

    def test_as_done_checks_the_done_gate_while_status_is_review(self):
        self.ledger(status="review")
        self.assertIn("done:", run(["lint", "--as-done"], self.d, 1).stdout)
        self.assertNotIn("done:", run(["lint"], self.d).stdout)


class SecretScan(Base):
    def test_ordinary_slugs_ending_in_sk_are_not_secrets(self):
        for slug in ("task-implement-retry-logic-queue", "feature/risk-assessment-for-payments-flow",
                     "ask-user-about-everything-now", "disk-usage-monitoring-service-fix"):
            self.ledger()
            with open(os.path.join(self.d, "WORK.md"), "a") as f:
                f.write("- note: %s\n" % slug)
            self.assertNotIn("credential", run(["lint"], self.d).stdout, slug)

    def test_real_looking_keys_are_still_caught_and_overridable(self):
        for key in ("sk-Ab12Cd34Ef56Gh78Ij90Kl", "ghp_" + "a1" * 20, "AKIAABCDEFGHIJKLMNOP",
                    "-----BEGIN RSA PRIVATE KEY-----"):
            self.ledger()
            with open(os.path.join(self.d, "WORK.md"), "a") as f:
                f.write("- note: %s\n" % key)
            self.assertIn("credential", run(["lint"], self.d, 1).stdout, key)
        self.assertNotIn("credential", run(["lint", "--no-secret-scan"], self.d).stdout)


class DoneGateFull(Base):
    """Full-tier done gate, and checks the reviewer found untested."""

    def full_done(self, **kw):
        fp, head = fp_of(self.d)
        text = self.read_template("WORK.md")
        rep = {
            "<framing | ready | building | verifying | review | blocked | paused | done>": kw.get("status", "done"),
            "<agent or human identifier; active or released; transfer condition>": "agent-a; released",
            "<repository identity, branch/worktree, how a successor accesses it>": "local repo",
            "<actual revisions or non-Git manifest>": head,
            "<output of `work-check.py snapshot` (HEAD + fp:<hex>), or a changed-file manifest with hashes if the script is unavailable>":
                "HEAD %s fp:%s" % (head, fp),
            "<observable result>": "overuse returns 0",
            "<explicit exclusions>": "none",
            "<none triggered (checked G1-G6) | triggered: G# reason, approval required>": "none triggered (checked G1-G6)",
            "<self-approved small task | exact approved scope, approving owner, reference/date | not yet approved>":
                "self-approved small task",
            "<current task/workspace scope>": "local edits",
            "<not run / fail / pass; link>": kw.get("a1", "pass; exit 0"),
            "<outcome>": "overuse clamps", "<observable check>": "unit test",
            "<reviewer/context identity, fp:<hex> of the reviewed snapshot, findings/artifact, status; or not independently reviewed>":
                "reviewer-b, fp:%s, no blockers" % fp,
            "<blocking first, suggestions separately; or none>": "none",
            "<unrun, stale, inaccessible, flaky, or manual checks; or none>": kw.get("remaining", "none"),
            "<one exact command or concrete edit, working directory, and prerequisites>": kw.get("next", "none; done"),
            "<what success/failure reveals; next branch of action>": "n/a",
            "<actual blocker or changed authority boundary>": "none",
            "<process IDs/ports/jobs and owner; stop instructions if authorized; or none>": "none",
            "<one concrete question; or none>": "none",
            "<released/accepted by whom; artifact/workspace access; do not imply a push happened>": "released",
        }
        for k, v in rep.items():
            self.assertIn(k, text, k)
            text = text.replace(k, v)
        text = text.replace("- [ ] S1", "- [x] S1").replace("- [ ] S2", "- [x] S2")
        text = re.sub(r"<[^<>\n]+>", "filled", text)
        self.write("WORK.md", text)
        return run(["lint"], self.d)

    def read_template(self, name):
        with open(os.path.join(TEMPLATES, name)) as f:
            return f.read()

    def setUp(self):
        super().setUp()
        self.write("quota.py", "def remaining_quota(l, u):\n    return max(0, l - u)\n")

    def test_filled_full_ledger_reaches_done(self):
        p = self.full_done()
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_unchecked_slice_blocks_done(self):
        text_before = self.full_done()
        self.assertEqual(text_before.returncode, 0)
        self.write("WORK.md", self.read("WORK.md").replace("- [x] S2", "- [ ] S2"))
        self.assertIn("unchecked slices", run(["lint"], self.d, 1).stdout)

    def test_remaining_verification_must_be_none(self):
        self.assertIn("Remaining verification", self.full_done(remaining="manual smoke test not run").stdout)

    def test_empty_next_action_is_an_error_while_working(self):
        p = self.full_done(status="building", next="none")
        self.assertIn("Next action is empty", p.stdout)


class Misc(Base):
    def test_test_files_do_not_count_toward_g3_lines(self):
        self.ledger()
        self.write("tests/test_big.py", "x = 1\n" * 500)
        out = run(["snapshot"], self.d, 0).stdout
        self.assertRegex(out, r"\b0 non-test lines")

    def test_tracked_test_file_changes_do_not_count_toward_g3_lines(self):
        self.write("tests/test_q.py", "x = 1\n")
        sh(self.d, "git", "add", "tests/test_q.py")
        sh(self.d, "git", "commit", "-q", "-m", "t")
        self.write("tests/test_q.py", "x = 1\n" * 400)
        out = run(["snapshot"], self.d, 0).stdout
        self.assertRegex(out, r"1 files, 0 non-test lines")
        self.write("quota.py", "def remaining_quota(l, u):\n" + "    pass\n" * 150)
        self.assertNotIn(" 0 non-test lines", run(["snapshot"], self.d, 0).stdout)

    def test_g3_counts_committed_work_since_base(self):
        head = fp_of(self.d)[1]
        self.ledger(head=head)
        for i in range(5):
            self.write("mod%d.py" % i, "x = %d\n" % i)
        sh(self.d, "git", "add", "-A", ":!WORK.md")
        sh(self.d, "git", "commit", "-q", "-m", "work")
        self.assertIn("gate G3 now exceeded", run(["lint"], self.d, 1).stdout)

    def test_unknown_base_warns(self):
        self.ledger(head="deadbeef1234")
        self.assertIn("not found in this repository", run(["lint"], self.d).stdout)

    def test_base_that_is_an_ancestor_does_not_warn(self):
        self.ledger(head=fp_of(self.d)[1])
        sh(self.d, "git", "commit", "-q", "--allow-empty", "-m", "later")
        self.assertNotIn("Base HEAD", run(["lint"], self.d).stdout)

    def test_owner_without_active_or_released_warns(self):
        self.ledger()
        self.write("WORK.md", self.read("WORK.md").replace("agent-a; released", "agent-a"))
        self.assertIn("Owner should say", run(["lint"], self.d).stdout)

    def test_lite_ledger_with_g1_trigger_is_rejected(self):
        self.ledger(approval="approved by owner 2026-10-24")
        self.write("WORK.md", self.read("WORK.md").replace("none triggered (checked G1-G6)", "triggered: G1 public flag"))
        self.assertIn("use the full ledger", run(["lint"], self.d, 1).stdout)

    def test_lite_ledger_over_g3_with_owner_approval_is_rejected(self):
        self.ledger(approval="approved by owner 2026-10-24")
        for i in range(4):
            self.write("mod%d.py" % i, "x = %d\n" % i)
        self.assertIn("lite ledger exceeds the G3 limits", run(["lint"], self.d, 1).stdout)

    def test_custom_ledger_path_needs_ledger_flag_and_message_says_so(self):
        head = fp_of(self.d)[1]
        body = lambda fp: LITE_OK.format(status="review", head=head, snap="HEAD %s fp:%s" % (head, fp),
                                         approval="self-approved small task", a1="pass", review="x", findings="none")
        self.write("notes/led.md", body("0" * 16))
        plain = re.search(r"fp:([0-9a-f]+)", run(["snapshot"], self.d, 0).stdout).group(1)
        flagged = re.search(r"fp:([0-9a-f]+)", run(["snapshot", "--ledger", "notes/led.md"], self.d, 0).stdout).group(1)
        self.assertNotEqual(plain, flagged)
        self.write("notes/led.md", body(plain))
        out = run(["lint", "notes/led.md"], self.d, 1).stdout
        self.assertIn("is stale", out)
        self.assertIn("snapshot --ledger notes/led.md", out)
        self.write("notes/led.md", body(flagged))
        self.assertNotIn("is stale", run(["lint", "notes/led.md"], self.d).stdout)

    def test_docs_work_ledger_is_excluded_by_default(self):
        before = fp_of(self.d)[0]
        self.write("docs/work/t1.md", "- anything\n")
        self.assertEqual(before, fp_of(self.d)[0])

    def test_nested_repo_edits_change_fingerprint(self):
        self.write("nest/n.txt", "1\n")
        sh(os.path.join(self.d, "nest"), "git", "init", "-q")
        before = fp_of(self.d)[0]
        self.write("nest/n.txt", "2\n")
        self.assertNotEqual(before, fp_of(self.d)[0])

    def test_bad_inputs_exit_2(self):
        self.assertEqual(run(["snapshot", "--include", "missing"], self.d).returncode, 2)
        self.assertEqual(run(["snapshot", "--include", ".."], self.d).returncode, 2)
        self.assertEqual(run(["snapshot", "--root", "/nonexistent-dir"], self.d).returncode, 2)

    def test_non_utf8_ledger_does_not_crash(self):
        self.ledger()
        with open(os.path.join(self.d, "WORK.md"), "ab") as f:
            f.write(b"- note: \xff\xfe\n")
        self.assertNotIn("Traceback", run(["lint"], self.d).stdout)

    def test_crlf_ledger_and_paths_with_spaces(self):
        self.ledger(approval="self-approved small task")
        self.write("WORK.md", self.read("WORK.md").replace("\n", "\r\n"))
        self.write("dir with space/a b.txt", "x\n")
        self.assertEqual(run(["lint"], self.d).returncode, 0)

    def test_repo_with_no_commits(self):
        d = tempfile.mkdtemp(prefix="work-check-empty-")
        self.addCleanup(shutil.rmtree, d, True)
        sh(d, "git", "init", "-q")
        with open(os.path.join(d, "a.txt"), "w") as f:
            f.write("x\n")
        p = run(["snapshot"], d, 0)
        self.assertIn("HEAD none", p.stdout)

    def test_storage_escapes_glob_characters(self):
        self.write("led[1].md", LITE_OK.format(status="building", head="x", snap="none", approval="self-approved small task",
                                              a1="not run", review="n", findings="none"))
        run(["storage", "led[1].md", "--apply"], self.d, 0)
        self.assertIn("excluded from Git", run(["storage", "led[1].md"], self.d, 0).stdout)

    def test_comparison_operators_are_not_placeholders(self):
        self.ledger()
        with open(os.path.join(self.d, "WORK.md"), "a") as f:
            f.write("- note: retry if n < 3 and m > 2\n")
        self.assertNotIn("placeholder", run(["lint"], self.d).stdout)

    def test_ledger_with_no_changes_to_it_keeps_ledger_out_of_stats(self):
        self.ledger()
        self.assertIn("0 files", run(["snapshot"], self.d, 0).stdout)


class SecondReview(Base):
    """Regressions from the second independent review."""

    def setUp(self):
        super().setUp()
        self.write("quota.py", "def remaining_quota(l, u):\n    return max(0, l - u)\n")

    def done(self, **kw):
        fp, head = fp_of(self.d)
        vals = dict(status="done", head=head, snap="HEAD %s fp:%s" % (head, fp), a1="pass; exit 0",
                    review="reviewer-b, fp:%s, no blockers" % fp, findings="none")
        vals.update(kw)
        self.ledger(**vals)
        return run(["lint", "--as-done"], self.d)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "requires Unix-domain sockets")
    def test_unreadable_file_makes_done_fail_closed_and_snapshot_exit_2(self):
        self.done()  # valid first
        os.remove(os.path.join(self.d, "quota.py"))
        srv = socket.socket(socket.AF_UNIX)
        self.addCleanup(srv.close)
        srv.bind(os.path.join(self.d, "quota.py"))
        p = run(["lint", "--as-done"], self.d, 1)
        self.assertIn("could not compute snapshot", p.stdout)
        self.assertNotIn("Traceback", p.stdout)
        q = run(["snapshot"], self.d)
        self.assertEqual(q.returncode, 2, q.stdout)
        self.assertNotIn("Traceback", q.stdout)

    def test_review_negations_are_rejected(self):
        fp = fp_of(self.d)[0]
        for text in ("did not pass", "not passed", "pass but blocking issue remains",
                     "no blockers; 2 blocking findings open", "approved with reservations: critical bug in parser"):
            out = self.done(review="reviewer-b fp:%s %s" % (fp, text))
            self.assertEqual(out.returncode, 1, text)

    def test_negative_words_inside_positive_statements_are_accepted(self):
        fp = fp_of(self.d)[0]
        for text in ("no blockers, nothing rejected", "no blocking findings remain", "pass; no issues found"):
            out = self.done(review="reviewer-b fp:%s %s" % (fp, text))
            self.assertEqual(out.returncode, 0, text + "\n" + out.stdout)

    def test_approval_not_granted_is_rejected(self):
        for text in ("approval was not granted", "Approved? no"):
            self.assertEqual(self.done(approval=text).returncode, 1, text)

    def test_other_acceptance_id_prefixes_are_checked(self):
        self.done()
        with open(os.path.join(self.d, "WORK.md"), "a") as f:
            f.write("- AC2: second criterion => not run\n")
        self.assertIn("acceptance AC2", run(["lint", "--as-done"], self.d, 1).stdout)

    def test_other_acceptance_id_prefixes_in_table_rows_are_checked(self):
        self.done()
        with open(os.path.join(self.d, "WORK.md"), "a") as f:
            f.write("| AC3 | outcome | check | not run |\n")
        self.assertIn("acceptance AC3", run(["lint", "--as-done"], self.d, 1).stdout)

    def test_blocking_concern_phrasing_is_negative(self):
        fp = fp_of(self.d)[0]
        self.assertEqual(self.done(review="reviewer-b fp:%s pass; blocking concern still open" % fp).returncode, 1)

    def test_partial_and_cannot_pass_are_rejected(self):
        for text in ("cannot pass", "partial pass", "PASS (3 of 4 cases)"):
            self.assertEqual(self.done(a1=text).returncode, 1, text)

    def test_gate_checked_wording_is_not_a_trigger(self):
        self.ledger()
        text = self.read("WORK.md").replace("none triggered (checked G1-G6)", "none triggered; G3 checked, G1 no")
        self.write("WORK.md", text)
        self.assertNotIn("self-approved", run(["lint"], self.d).stdout)

    def test_base_without_a_hash_warns(self):
        self.ledger(head="main")
        self.assertIn("Base HEAD has no commit hash", run(["lint"], self.d).stdout)

    def test_missing_git_binary_exits_2(self):
        env = dict(os.environ, PATH="/nonexistent")
        os.makedirs(os.path.join(self.d, "src"))
        for start in (self.d, os.path.join(self.d, "src")):
            with self.subTest(start=start):
                p = subprocess.run([sys.executable, "-I", SCRIPT, "snapshot"], cwd=start, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.assertEqual(p.returncode, 2, p.stdout)
                self.assertNotIn("fp:", p.stdout)
                self.assertNotIn("Traceback", p.stdout)

    @unittest.skipUnless(os.name == "posix", "requires POSIX executable permissions")
    def test_exec_bit_changes_change_fingerprint(self):
        base = fp_of(self.d)[0]
        os.chmod(os.path.join(self.d, "quota.py"), 0o755)
        self.assertNotEqual(base, fp_of(self.d)[0])

    def test_symlink_changes_change_fingerprint(self):
        base = fp_of(self.d)[0]
        os.remove(os.path.join(self.d, "quota.py"))
        try:
            os.symlink("other.py", os.path.join(self.d, "quota.py"))
        except OSError as e:
            if getattr(e, "winerror", None) == 1314:
                self.skipTest("Windows requires permission to create symlinks")
            raise
        self.assertNotEqual(base, fp_of(self.d)[0])

    def test_storage_escapes_hash_and_bang(self):
        for name in ("#hash.md", "!bang.md"):
            self.write(name, "local ledger\n")
            run(["storage", name, "--apply"], self.d, 0)
            self.assertEqual(subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", name],
                                           cwd=self.d).returncode, 0)

    @unittest.skipUnless(os.name == "posix", "requires literal trailing-space filenames")
    def test_storage_escapes_trailing_space(self):
        self.write("trail ", "local ledger\n")
        run(["storage", "trail ", "--apply"], self.d, 0)
        self.assertEqual(subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", "trail "],
                                       cwd=self.d).returncode, 0)

    def test_digit_or_uppercase_required_for_sk_tokens(self):
        for text, flagged in (("sk-abcdefghijklmnopqrstuvwx", False), ("sk-abcdefghijklmnopqrstuv9x", True),
                              ("sk-abcdefghijklmnopqrstuvwX", True)):
            self.ledger()
            with open(os.path.join(self.d, "WORK.md"), "a") as f:
                f.write("- note: %s\n" % text)
            self.assertEqual("credential" in run(["lint"], self.d).stdout, flagged, text)

    def test_review_pending_and_findings_remaining_are_rejected(self):
        fp = fp_of(self.d)[0]
        self.assertEqual(self.done(review="pending, fp:%s, no blockers so far" % fp).returncode, 1)
        self.assertEqual(self.done(findings="none, 2 issues remain unresolved").returncode, 1)


def load_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("work_check_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class VerdictPhrasing(unittest.TestCase):
    """Table of phrasings found by reviewers. Pattern matching is a tripwire, not a proof; see VALIDATION.md."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    REVIEW_REJECT = [
        "not accepted", "not LGTM", "did not pass", "not passed", "pass but blocking issue remains",
        "no blockers; 2 blocking findings open", "approved with reservations: critical bug in parser", "pass: no",
        "passed: no", "pass: false", "pass=false", "0 passed", "approved: no", "approved: false",
        "pass, but I could not finish reviewing", "pass for module a only; module b unreviewed",
        "pass with 3 open blockers", "pass; one blocker outstanding", "no blockers yet",
        "no blockers remain except the data loss one", "lgtm, except the crash on empty input",
        "pass; regression in export", "pass. However the migration is unsafe.", "approved subject to owner sign-off",
        "would pass if the fix landed", "unable to confirm; pass unverified", "nothing is approved", "pass - NOT",
        "REJECTED, changes requested", "blockers remain", "pass; blocking concern remains",
        "pass; blocking issue unresolved",
    ]
    REVIEW_ACCEPT = [
        "no blockers, nothing rejected", "no blocking findings remain", "pass; no issues found",
        "approved, no blockers", "lgtm, no blockers found", "passed (4 of 4 cases)",
    ]
    APPROVAL_REJECT = [
        "approval was not granted", "Approved? no", "not approved", "owner denied", "approved: no", "approved: false",
        "approved=no", "approved - no", "approved by owner: no", "approved by owner? no", "approved ? no",
        "approved NOT", "approved - NOT", "approved (retracted)", "approved for planning only", "approved by nobody",
        "approved earlier, scope since changed", "not yet approved", "pending", "",
    ]
    APPROVAL_ACCEPT = [
        "approved by owner, no concerns", "approved by owner 2026-10-24; follow-up filed as issue 12",
        "approved by maintainer (ref PR 12)", "self-approved small task",
    ]
    A1_REJECT = [
        "pass: no", "pass=false", "pass? no", "pass - no", "pass(no)", "0 passed", "0/3 passed", "unable to pass",
        "pass on 2 of 3 inputs", "pass in dev only", "passes sometimes", "flaky pass", "passed with errors",
        "pass once, then crashed", "pass (stub)", "untested; expected to pass", "pass - unverified",
        "pass* (see caveat: missing coverage)", "does not pass; python", "never passed", "cannot pass",
        "partial pass", "PASS (3 of 4 cases)", "not run", "fail", "",
    ]
    A1_ACCEPT = [
        "pass; no failures observed", "pass; exit 0", "pass (4 of 4)", "passed; python -m unittest exit 0 in repo root",
        "pass; 12 tests, 0 failed", "pass; 0 errors",
    ]
    FINDINGS_REJECT = [
        "none but see the crash in notes", "none; open question about auth", "none, apart from the data loss",
        "none... for now except the memory leak", "none? no", "none: false", "none found? no", "none, 1 open",
        "blocking bug in parser", "none, but blocking bug in parser remains", "none, 2 issues remain unresolved", "",
    ]
    FINDINGS_ACCEPT = ["none", "None.", "none (nonblocking: rename helper)", "none (nits: naming)"]

    def test_review(self):
        for t in self.REVIEW_REJECT:
            self.assertFalse(self.m.verdict_ok("reviewer-b fp:0123456789abcdef " + t)[0], t)
        for t in self.REVIEW_ACCEPT:
            self.assertTrue(self.m.verdict_ok("reviewer-b fp:0123456789abcdef " + t)[0], t)

    def test_approval(self):
        for t in self.APPROVAL_REJECT:
            self.assertFalse(self.m.approval_granted(t), repr(t))
        for t in self.APPROVAL_ACCEPT:
            self.assertTrue(self.m.approval_granted(t), t)

    def test_acceptance(self):
        for t in self.A1_REJECT:
            self.assertFalse(self.m.passed(t), repr(t))
        for t in self.A1_ACCEPT:
            self.assertTrue(self.m.passed(t), t)

    def test_findings(self):
        for t in self.FINDINGS_REJECT:
            self.assertFalse(self.m.CLEAN_NONE.match(t), repr(t))
        for t in self.FINDINGS_ACCEPT:
            self.assertTrue(self.m.CLEAN_NONE.match(t), t)


class SpecialFiles(Base):
    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX named pipes")
    def test_fifo_fails_closed_without_hanging(self):
        self.write("x.txt", "x\n")
        sh(self.d, "git", "add", "x.txt")
        sh(self.d, "git", "commit", "-q", "-m", "x")
        os.remove(os.path.join(self.d, "x.txt"))
        os.mkfifo(os.path.join(self.d, "x.txt"))
        p = subprocess.run([sys.executable, "-I", SCRIPT, "snapshot"], cwd=self.d, timeout=20,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertNotIn("Traceback", p.stdout)


class Hardening(Base):
    def test_corrupt_index_refuses_snapshot_and_done(self):
        fp, head = fp_of(self.d)
        self.ledger(status="done", head=head, snap="HEAD %s fp:%s" % (head, fp),
                    a1="pass; exit 0", review="reviewer-b fp:%s; no blockers" % fp)
        run(["lint", "--as-done"], self.d, 0)
        with open(os.path.join(self.d, ".git", "index"), "wb") as f:
            f.write(b"invalid index")
        self.write("quota.py", "def remaining_quota(l, u):\n    return 999\n")
        p = run(["snapshot"], self.d, 2)
        self.assertNotIn("fp:", p.stdout)
        self.assertNotIn("Traceback", p.stdout)
        self.assertIn("could not compute snapshot", run(["lint", "--as-done"], self.d, 1).stdout)

    def test_missing_commit_object_refuses_snapshot(self):
        full_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.d,
                                   stdout=subprocess.PIPE, text=True, check=True).stdout.strip()
        obj = os.path.join(self.d, ".git", "objects", full_head[:2], full_head[2:])
        os.chmod(obj, 0o600)
        os.remove(obj)
        p = run(["snapshot"], self.d, 2)
        self.assertNotIn("fp:", p.stdout)
        self.assertNotIn("Traceback", p.stdout)

    def test_root_resolves_ledger_for_all_commands_from_outside(self):
        outside = tempfile.mkdtemp(prefix="work-check-caller-")
        self.addCleanup(shutil.rmtree, outside, True)
        ledger = "docs/work/task.md"
        self.write(ledger, LITE_OK.format(status="building", head=fp_of(self.d)[1], snap="none yet",
                                         approval="self-approved small task", a1="not run",
                                         review="not independently reviewed", findings="none"))
        before = run(["snapshot", "--ledger", ledger, "--root", self.d], outside, 0).stdout
        run(["lint", ledger, "--root", self.d], outside, 0)
        run(["storage", ledger, "--root", self.d, "--apply"], outside, 0)
        self.assertEqual(subprocess.run(["git", "check-ignore", "-q", "--", ledger],
                                       cwd=self.d).returncode, 0)
        self.assertEqual(before, run(["snapshot", "--ledger", ledger, "--root", self.d], outside, 0).stdout)

    def test_storage_does_not_match_a_different_tracked_filename(self):
        self.write("led1.md", "unrelated tracked file\n")
        sh(self.d, "git", "add", "led1.md")
        self.write("led[1].md", "local ledger\n")
        run(["storage", "led[1].md", "--apply"], self.d, 0)
        self.assertEqual(subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", "led[1].md"],
                                       cwd=self.d).returncode, 0)
        self.assertEqual(subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", "led1.md"],
                                       cwd=self.d).returncode, 1)


class MutationBaseline(unittest.TestCase):
    def test_failing_baseline_cannot_count_as_caught_mutants(self):
        with tempfile.TemporaryDirectory(prefix="work-check-baseline-") as tmp:
            scripts = os.path.join(tmp, "scripts")
            os.makedirs(scripts)
            os.makedirs(os.path.join(tmp, "templates"))
            for name in ("work-check.py", "mutation_check.py"):
                shutil.copy(os.path.join(HERE, name), os.path.join(scripts, name))
            with open(os.path.join(scripts, "test_work_check.py"), "w") as f:
                f.write("import unittest\n"
                        "class BrokenBaseline(unittest.TestCase):\n"
                        "    def test_failure(self):\n"
                        "        self.fail('deliberate baseline failure')\n")
            p = subprocess.run([sys.executable, "-B", os.path.join(scripts, "mutation_check.py")],
                               cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, timeout=120)
            self.assertNotEqual(p.returncode, 0, p.stdout)
            self.assertNotIn("CAUGHT", p.stdout)


if __name__ == "__main__":
    unittest.main()
