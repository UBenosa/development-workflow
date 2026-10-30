# Review record: additions to the kit

This records the independent review of the changes made after `REVIEW.md` (the script, lite ledger, approval gate, and storage default). `REVIEW.md` is unchanged and does not cover them.

## Verdict

**No PASS was obtained on the final files.** Two independent review rounds returned FAIL and every blocking finding they raised was fixed. A third round, which would have checked the final rebuilt verdict logic against fresh phrasings, did not run: both attempts ended on a session limit before the reviewer began, and further rounds were stopped. The final files are verified only by the author's own tests and mutation checks.

## What each reviewer saw

| Round | Reviewed | Result | Outcome |
| --- | --- | --- | --- |
| 1 | The first version of the additions, in a fresh context | **FAIL**, 4 blocking | Stale manifest; fingerprint depended on HEAD (committing reviewed work or the ledger made `done` fail); credential regex rejected ordinary task slugs; done gate accepted plain negations ("not approved", "does not pass", a REJECTED review). All four reproduced, then fixed. |
| 2 | The round-1 fixes, in a fresh context | **FAIL (narrow)**, 2 blocking | Closed round-1 findings 2, 3 and 4. New: `lint` passed silently when the fingerprint could not be computed; the Review line accepted negations of its own positive word. Both reproduced, then fixed. |
| 3 (continuation of round 2's reviewer) | The round-2 fixes | **FAIL (narrow)**, 1 blocking | Confirmed B1 and B2 closed. New: a negator before "accepted" or "lgtm" passed the gate (`not accepted`, `not LGTM`). It also reported about 100 more phrasings, 39 of them false accepts, mostly contrived or contradictory wording. |
| 4 | The final files after the round-3 rebuild | **Not run** | Two attempts failed on a session limit before any checking. |

## What changed after the last review

After round 3 the verdict logic was rebuilt rather than patched word by word (see `VALIDATION.md`, round 3): one shared test for negators, structured negation, trailing negators and hedge words on the review, approval and acceptance lines; strict `none` for findings; non-regular files fail closed; a word-boundary bug in the "blocking ... remains" pattern, found by a new test, was fixed. Every phrasing the reviewers reported (83 that must be rejected, 17 that must be accepted) is now a unit test and behaves correctly. Those phrasings were also what the fix was fitted to, so this is weak evidence about unseen wording.

Author-run checks on the final files, not independent: 83 tests pass; `scripts/mutation_check.py` runs 37 named breakages and all are caught; both ledger templates, filled in, reach `done`; the README example ledger lints with exit 0; `REVIEW.md` is byte-identical to the originally reviewed file.

## What remains open

- No independent reviewer has seen the rebuilt verdict logic, `scripts/mutation_check.py`, or the final documents.
- The wording checks are word patterns. Unusual phrasing can still be accepted or an honest line wrongly rejected. The reviewers found examples in both directions.
- Not checked by anyone: Windows or macOS, other Git versions, cross-machine fingerprint equality, `core.autocrlf`, submodules, permission-denied files as a non-root user, real repository adoption, and whether agents follow the gate and tier rules in practice. The cold-start rehearsal in `VALIDATION.md` predates all of these additions.
- Review independence cannot be checked by the script (for example "reviewed by the author").

A reasonable next step is one more independent review of the final files, using phrasings not already in `scripts/test_work_check.py`, before relying on `lint` as a gate.
