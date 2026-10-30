<!-- tier: full -->
# Work ledger: <task ID and short outcome>

Replace placeholders with inspected facts. Use `none`, `unknown`, or `not run` explicitly. This file is the current state, not a chat transcript. Keep only decision-critical context; link larger artifacts.

## Control and workspace

- Status: <framing | ready | building | verifying | review | blocked | paused | done>
- Owner/writer: <agent or human identifier; active or released; transfer condition>
- Workspace: <repository identity, branch/worktree, how a successor accesses it>
- Base / current HEAD: <actual revisions or non-Git manifest>
- Snapshot under test/review: <output of `work-check.py snapshot` (HEAD + fp:<hex>), or a changed-file manifest with hashes if the script is unavailable>
- Dirty/staged/untracked work: <paths and ownership; include required ignored/generated files>
- Other work to preserve: <unrelated edits, active workers, integration constraints>

## Goal and authority

- User outcome: <observable result>
- Non-goals: <explicit exclusions>
- Approach: <chosen seam/design; why it fits>
- Gate: <none triggered (checked G1-G6) | triggered: G# reason, approval required>
- Approval: <self-approved small task | exact approved scope, approving owner, reference/date | not yet approved>
- Allowed local actions: <current task/workspace scope>
- External/destructive/install actions: <not approved by default; exact approved targets if any>
- Constraints and risks: <privacy, compatibility, data, budget, recovery>

## Acceptance and verification

| ID | Required behavior/outcome | Check or scenario | Current result and evidence |
| --- | --- | --- | --- |
| A1 | <outcome> | <observable check> | <not run / fail / pass; link> |

## Current plan

Use only actionable slices. A checkbox means that slice's acceptance evidence exists, not merely that code was written.

- [ ] S1: <thin vertical slice; dependencies; acceptance IDs; proving command/scenario>
- [ ] S2: <next dependent or independent slice; same fields>

## Decisions, context, and rejected paths

- <domain terms or links, nonobvious design decision and evidence; preserve why>
- <failed attempt/hypothesis, observed result, why not to repeat it>
- <latest plan change and its reason, or none>

## Execution evidence

| Check | Exact command/scenario and working directory | Environment + snapshot | Observed result | Artifact/limits |
| --- | --- | --- | --- | --- |
| <focused/broader/runtime> | <command; safe fixtures> | <runtime/config; snapshot> | <exit code and observation, or not run> | <relative path; gap> |

- Independent review: <reviewer/context identity, fp:<hex> of the reviewed snapshot, findings/artifact, status; or not independently reviewed>
- Unresolved review findings: <blocking first, suggestions separately; or none>
- Remaining verification: <unrun, stale, inaccessible, flaky, or manual checks; or none>

## Pickup / next action

- Completed and checked: <current verified boundary>
- In progress: <what is partially implemented or uncertain>
- **Next action:** <one exact command or concrete edit, working directory, and prerequisites>
- Expected observation: <what success/failure reveals; next branch of action>
- Stop/escalate if: <actual blocker or changed authority boundary>
- Live resources: <process IDs/ports/jobs and owner; stop instructions if authorized; or none>
- Pending human decision/approval: <one concrete question; or none>
- Transfer: <released/accepted by whom; artifact/workspace access; do not imply a push happened>

## Unapproved incoming context / backlog

- <related reports grouped by likely cause, with source; not part of approved scope; or none>
