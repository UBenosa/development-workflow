# Development workflow

Understand the goal. Prove one small slice. Preserve enough state for the next agent.

This is an original synthesis of Matt Pocock's skills and Poteto's pstack/interview, adapted for interchangeable coding agents. It does not require either plugin, a particular model, a subscription, a tracker, or an orchestration service. See [SOURCES.md](SOURCES.md) for provenance and deliberate departures.

## The loop

**Orient -> clarify -> choose a verifiable slice -> build -> verify independently -> checkpoint -> continue.

## Two maintained files per repository

| File | Owns | Update when |
| --- | --- | --- |
| `AGENTS.md` | Stable operating contract, repository map, commands, verification recipe, boundaries | The repository or its proven operating method changes |
| `WORK.md` | Current goal, approved scope, acceptance checks, plan, actual state, evidence, next action | A slice finishes, the plan changes, a blocker appears, or control transfers |

Code and version control remain authoritative about the implementation. `WORK.md` is authoritative about task intent and recorded decisions, not whether a command would still pass. Reconcile both on pickup. Chat history is optional background, never required state.

Two ledger sizes exist. Use `templates/WORK-lite.md` for single-writer, single-seam tasks and `templates/WORK.md` when a handoff, multiple sessions, parallel workers, or a risky change is involved. The rule is in `templates/AGENTS.md`, "Ledger tiers and storage". By default the ledger is a local, untracked file excluded through `.git/info/exclude`; commit it only on a task branch for cross-machine handoff.

`scripts/work-check.py` checks the mechanical parts: unfilled placeholders, missing fields, a `done` that lacks passing acceptance or a positive review (plain negations such as "not approved" or "does not pass" are rejected), evidence that no longer matches the working tree, self-approved tasks that outgrew the approval gate, and where the ledger sits relative to Git. It checks consistency, not truth, and its wording checks are word patterns: it rejects negations and hedges ("not approved", "pass but", "unverified") in the verdict lines, and a human still has to read the ledger.

Do not create a separate PRD, plan, progress log, handoff, and status file containing the same facts. Link existing project documents instead of copying them. Add a glossary or decision record only when the vocabulary or decision actually needs one.

## Adopt in a repository

1. Read the existing repository instructions. **Merge** `templates/AGENTS.md` into them; do not overwrite existing rules or agent adapters.
2. Fill the repository map and verification recipe from inspection and real execution. Leave unavailable checks explicitly unavailable; do not invent commands.
3. Copy `scripts/work-check.py` into the repository (or run it from the kit with `--root`). Create `WORK.md` from `templates/WORK-lite.md` or `templates/WORK.md` per the tier rule, then run `python scripts/work-check.py storage --apply` to keep it out of history. Record the actual goal, gate result, approval boundaries, and next verifiable slice. Replace placeholder values and run `work-check.py lint` before calling it resumable. If the ledger lives outside `WORK.md` or `docs/work/`, pass `--ledger <path>` to `snapshot` so the fingerprint matches what lint computes.
4. Run one small task with one implementer and an independent reviewer. Only add parallel workers after the basic feedback path works.

`lint`, `storage`, and `snapshot --ledger` resolve relative ledger paths from the repository root. Use `--root` when invoking the kit elsewhere. Absolute ledger paths remain absolute. Snapshot creation fails if required Git inspection commands fail.

## Example Prompts (Verbosed, can be simplified)

### Start prompt

> Read AGENTS.md and WORK.md. Inspect the current repository before trusting recorded state. Frame the goal, first verifiable slice, verification method, and authority boundary. Run the approval gate in AGENTS.md and record it on the ledger's Gate line. If no trigger fires, state the approach in one line and proceed; if any fires, obtain approval first, then continue within it without asking after every slice. Routine corrections inside an approved task need no new approval unless a trigger newly fires. Keep WORK.md current and run `work-check.py lint` before you stop.

### Continue with a different agent

> Read AGENTS.md and WORK.md. Run `work-check.py lint` and `work-check.py snapshot`, then reconcile the recorded revision, dirty files, ownership, approvals, and evidence against the actual workspace. Do not restart discovery or re-plan completed work without contrary evidence. State the next executable action, then continue within the approved scope. If ownership is still active, coordinate before editing.

### Pause prompt

> Checkpoint WORK.md for a cold start. Preserve current edits, describe failing and unrun checks honestly, identify the exact next command and expected observation, and record live resources and pending approvals. Do not commit, stop someone else's process, or clean up data just to make the handoff look tidy.

### Review prompt

> Independently inspect the requirements, actual changed files/diff, and evidence for the recorded snapshot. Check both behavioral correctness and maintainability. Run the relevant checks if available. Return blocking findings with evidence, nonblocking suggestions separately, missing checks, and the exact snapshot reviewed as `fp:<hex>` from `work-check.py snapshot`. Do not treat the implementer's summary as proof.

## Tool and agent portability

The protocol is plain Markdown plus repository-native checks. Skill auto-discovery is optional. If a tool does not read `AGENTS.md` automatically, explicitly attach or ask it to open the file.

| Capability | Preferred implementation | If unavailable |
| --- | --- | --- |
| Read/edit/run | Agent's local file and shell tools | Human runs the recorded command and returns actual output |
| UI verification | Available browser/desktop driver with evidence | Record the manual scenario; leave it pending for a human |
| Delegation | Fresh independent agent context | Separate session or qualified human review; otherwise mark not independently reviewed |
| Work isolation | Separate existing/approved worktrees or branches | Sequential single-writer work |
| Tracking | Local untracked ledger by default; task branch for cross-machine handoff | A tracker can be canonical if accessible to every participant; otherwise retain the local state |

## Contents

- `SKILL.md`: optional portable entry point; automatic discovery depends on the agent.
- `templates/AGENTS.md`: repository operating contract and runbook.
- `templates/WORK.md`: full living task ledger.
- `templates/WORK-lite.md`: compact ledger for small single-writer tasks.
- `scripts/work-check.py`: snapshot fingerprint, ledger lint, storage check (standard library only).
- `scripts/test_work_check.py`: its tests (`python3 -m unittest scripts/test_work_check.py`).
- `scripts/mutation_check.py`: requires a passing unchanged suite, then checks 37 named breakages in scratch copies (`python3 scripts/mutation_check.py`). A failed or timed-out baseline stops the run before mutation scoring.
- `SOURCES.md`: checked source mapping, pinned revisions, and adaptations.
- `VALIDATION.md`: checks and independent review of this kit, when supplied.