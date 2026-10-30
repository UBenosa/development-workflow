# Validation record

## Scope

This is a checked workflow document/toolkit, not a deployed development system. No existing project adopted it, and no upstream plugin, model, dependency, hook, or persistent automation was installed. The repository templates intentionally contain fields to fill from the target project.

## Primary-source checks

- Retrieved the full interview's automatic captions and checked the mapped passages. Captions are not a separately audited audio transcript.
- Resolved and pinned both upstream repository revisions in `SOURCES.md`.
- Recomputed the saved source manifests: all 38 fetched source files matched their recorded byte sizes and SHA-256 hashes.
- An independent reviewer read 14 directly attributed primary documents and the mapped interview passages, not merely the research summaries. No materially inaccurate attribution was found.

## Independent design review

The initial review inspected `README.md`, `SKILL.md`, `SOURCES.md`, `templates/AGENTS.md`, and `templates/WORK.md` against the original request and primary evidence. Verdict: **PASS with nonblocking suggestions; no blocking findings.**

The following suggestions were then incorporated:

1. Initial approach approval now consistently applies to substantive new work, not every routine correction inside an approved task.
2. Reverting one's own approved diagnostic code edits is explicitly distinguished from deleting files/data or discarding unrelated edits.
3. `README.md` now demonstrates a compact small-task ledger without introducing another required file.

The optional skill entry point also has a short trigger and explicit use, pitfall, and verification sections. `REVIEW.md` records the separate final follow-up verdict and hashes for the final snapshot. Do not substitute the older initial-review hashes for those final hashes.

## Cold-start rehearsal

A different fresh agent received only a disposable fixture's `AGENTS.md`, `WORK.md`, and actual workspace. It did not receive the parent conversation, the expected diagnosis, the research, or this kit's explanatory documents. Its authority was limited to read-only inspection and local standard-library tests.

The fixture used a real historical baseline, not fabricated test output:

- Public function: `remaining_quota(limit, used)` for nonnegative integer inputs.
- Acceptance examples: unused quota remains available; exact use returns zero; overuse returns zero.
- Baseline: `python -m unittest -v` actually passed all three tests; source, tests, and unrelated operator notes were fingerprinted.
- Controlled drift: the zero clamp was deliberately removed afterward, leaving historical passing evidence in place.

Observed pickup result:

- Detected that `quota.py` no longer matched the passing baseline.
- Confirmed that tests and unrelated operator notes still matched their baseline hashes.
- Ran the focused overuse regression: exit code 1, `AssertionError: -3 != 0`.
- Ran the full suite: two passed, one failed, exit code 1.
- Identified the concrete repair and the need for new snapshot evidence and independent review.
- Did not call the task done, assume write authority, modify fixture files, install tooling, or touch external systems.
- Before/after inventory and hash comparison reported no fixture file changes. The parent separately confirmed the source drift and preservation of the test and operator-note hashes.

This is evidence that the state protocol supports a **same-filesystem, read-only cold-start pickup** and rejects stale proof in a small controlled case. It is not an end-to-end implementation transfer, a production trial, cross-machine distribution, or certification across agent products. The intentionally broken fixture is a validation exercise, not a shipped application.

## Structural and packaging checks

The local checks cover internal Markdown links, required contract/ledger fields, generic skill frontmatter, machine-specific paths, normal hyphens, final file hashes, and archive integrity. The final follow-up review checks the actual revised documents. A package manifest permits verifying that extracted files match the packaged snapshot.

## Changes after the final review

`REVIEW.md` and its hashes describe the package as it stood before these changes. Do not read its PASS as covering them. The independent review of the additions is a separate record, `REVIEW-additions.md`, with its own hashes.

Changed or added since: `README.md`, `SKILL.md`, `SOURCES.md`, `VALIDATION.md`, `templates/AGENTS.md` (approval gate, ledger tiers and storage, script use; the rest reworded for length, with a few minor qualifiers dropped and two restored; it ends at about 15.6 KB against 11.4 KB originally, so the added sections cost more than the rewording saved), `templates/WORK.md` (tier marker, Gate line, `fp:` tokens), new `templates/WORK-lite.md`, new `scripts/work-check.py`, new `scripts/test_work_check.py`, new `scripts/mutation_check.py`. `MANIFEST.json` was regenerated for the new set. `REVIEW.md` is byte-identical to the reviewed version.

Independent reviews of the additions (`REVIEW-additions.md`). Three rounds, each by a fresh-context reviewer or its continuation, each reproducing defects before they were fixed:

1. **Round 1: FAIL, four blocking findings, all fixed.** A stale `MANIFEST.json`; a fingerprint that included HEAD and so broke on committing reviewed work or the ledger; a credential heuristic that rejected ordinary task slugs; and a done gate that accepted plain negations ("not approved", "does not pass", a REJECTED review, "none, but blocking bug remains"). Fixes: manifest regenerated after final edits; fingerprint made content-only (tracked and untracked non-ignored files, nested repositories included, ledgers excluded, independent of HEAD, staging, and commits); word-boundary credential regex with `--no-secret-scan`; negation checks. Also fixed from that round: G3 counts changes since the ledger's `Base HEAD` so committing no longer hides an oversized task; lite ledgers that record a G1, G2, G4, G5 or G6 trigger or exceed G3 are rejected; `--as-done` evaluates the done gate whatever Status says (the earlier "lint must exit 0 before done" was circular); nested-repository edits change the fingerprint; bad `--include` and `--root` paths exit 2; non-UTF-8 ledgers do not crash; `Status: **done**` is accepted; comparison operators are not placeholders; `storage --apply` escapes glob characters; the stale message names `--ledger`.
2. **Round 2: narrow FAIL, two new blocking findings, both fixed.** `lint` passed silently when the fingerprint could not be computed (now an error for `review` and `done`, `snapshot` exits 2, a missing Git binary in a repository exits 2); and the Review line accepted negations of its own positive word. Also fixed: `Base HEAD` without a hash warns, acceptance IDs other than `A#` are checked, "G3 checked" is not a trigger, "cannot pass" and "partial pass" are rejected, `SOURCES.md` no longer lists approval as unconditional.
3. **Round 3: B1 and B2 confirmed closed; one new blocking finding (a negator before "accepted" or "lgtm" passed the gate) and about 100 further phrasings, of which 39 were false accepts.** Rather than patch word by word, the verdict checks were rebuilt as one shared test applied to review, approval and acceptance lines: negator before any positive word, structured negation (`pass: no`, `0 passed`), trailing negator (`approved - no`), and hedge words (`but`, `except`, `only`, `yet`, `unverified`, `outstanding`, `flaky`, `crashed` and similar) all mark a line as unfit for `done`; findings and remaining verification must be exactly `none`, optionally with a `(nonblocking: ...)` note; zero-failure wording (`0 failed`, `no failures`) and all-pass counts (`4 of 4`) are accepted; FIFOs, sockets and devices fail closed instead of hanging. A bug in the "blocking ... remains" pattern (no word boundary tolerance for "remains") was found by a new test and fixed. All phrasings the reviewers reported (83 that must be rejected, 17 that must be accepted) now behave correctly and live in the test suite as a table. **Because those phrasings were also what the fixes were fitted to, passing them is weak evidence about unseen wording.**

**The final files were not independently reviewed.** The round-3 fixes were re-submitted for verification twice; both attempts ended on a session limit before the reviewer did any work, and further rounds were stopped. The rebuilt verdict logic, the in-kit mutation harness, and the final text of the documents are therefore verified only by the author's tests and mutation checks, which share the author's blind spots. `REVIEW-additions.md` records exactly what each reviewer saw.

Checks run (Linux, Python 3.13, Git 2.43, throwaway repositories):

- `python3 -m unittest scripts/test_work_check.py`: 83 tests, all passing.
- `python3 scripts/mutation_check.py`: 37 named deliberate breakages of the script, each run against the full suite, all caught. The list is in that file and reproducible. Earlier rounds found mutants that survived; each led to a new or corrected test, and redundant code that made a mutant equivalent was removed instead of kept.
- Both ledger templates, filled in, reach `done` under `lint --as-done`, single deliberate defects are rejected, and the unfilled templates and contract fail lint as intended. The README example ledger lints with exit 0 (one warning, because its illustrative Base HEAD is not a commit in the reader's repository).

Not checked in that Linux validation round: Windows or macOS paths, Git versions other than 2.43, fingerprint equality across two machines or under `core.autocrlf`, submodules and sparse checkout, very large binary files, permission-denied files as a non-root user (a socket and a FIFO stand in), any real repository adoption, or whether agents follow the gate and tier rules in practice. The gate triggers G1, G2, G4, G5 and G6 and most of the tier rule rely on honest recording; the script enforces G3, lite-ledger eligibility as recorded on the Gate line, self-approval consistency, and the done gate. The cold-start rehearsal above predates the lite ledger, the gate, and the script and has not been repeated with them.

Known limits of the wording checks: they are word patterns. Unusual or contradictory phrasing can still be accepted (for example a hedge that uses none of the listed words), and honest phrasing that happens to use a listed hedge is rejected until reworded (the reviewers saw `pass on retry after flaky failure` and `none (bug fixed)` rejected). A lowercase-only `sk-` token is not flagged as a credential. Independence of the reviewer ("reviewed by the author") cannot be checked. The `HEAD` text on the Snapshot line is informational and is not verified; the `fp:` is what lint checks, so checking out a different commit with identical working-tree content gives the same fingerprint. A `lint` pass means the ledger is internally consistent and current, nothing more.

## Validator hardening on Windows

This later revision fixes Git failure handling, ledger paths, and mutation baseline gating. It also corrects the lite example without changing G1 or the ledger tiers. Earlier review verdicts do not cover these changes.

Checks used Windows, Python 3.12.10, and Git 2.55.0.windows.5. All application and Git fixtures were disposable.

- Before the fixes, regression cases reproduced successful snapshots after Git index corruption, failed external ledger lookup, incorrect bracketed-filename classification, and non-Git fallback below a repository when Git was unavailable.
- A deliberately failing baseline also reproduced all 37 mutants being reported as caught. The new regression confirms that this baseline now stops mutation scoring with a nonzero exit.
- `python -B -m unittest scripts/test_work_check.py`: 90 tests, passing with 5 explicit skips. Unix-domain sockets, POSIX executable permissions, named pipes, literal trailing-space filenames, and symlink creation lacked the required platform support or privileges.
- `python -B scripts/mutation_check.py`, before the filename-test split: the unchanged baseline passed. The run caught 33 of 37 variants and exited 1. Executable-permission, symlink, special-file, and trailing-space-escape variants were not caught on this Windows environment. This is not a full mutation pass.
- CLI smoke: a valid synthetic completed ledger passed. Source drift then failed lint with exit 1. Git index corruption rejected snapshot creation with exit 2 and completion with exit 1. Missing Git from a repository subdirectory exited 2.
- External invocation smoke: relative and absolute ledgers resolved correctly under `--root`, including a repository path containing spaces. Storage excluded the intended ledger. A local `led[1].md` remained distinct from tracked `led1.md` and disappeared from Git's visible untracked-file listing.
- An actual quota caller returned `[7, 0, 0]` for unused, exact-use, and overuse cases. Completed-ledger smoke inputs used synthetic review metadata to exercise the checker, not a claim of independent application review.
- After that mutation run, the trailing-space integration case became explicitly POSIX-only. A Windows fixture requested `trail ` but created `trail`. Hash and bang filename cases remain cross-platform. CLI smoke confirmed both stayed excluded from Git's visible untracked-file listing. The full mutation run was not repeated after this test-only split.

These checks do not establish POSIX-only behavior, complete mutation coverage, cross-machine fingerprints, or real-project adoption. No independent review of this hardening revision is claimed.

## Remaining real-world work

Adopt in one chosen repository, merge rather than overwrite its existing instructions, fill and exercise its actual command recipe, then complete a small task with a second agent picking it up and a separate reviewer checking the result. Repository adoption and any external integration need their own concrete scope. No such adoption or integration is claimed here.
