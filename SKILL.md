---
name: development-workflow
description: Use when the user asks to adopt, start, pause, hand off, or resume a coding task through a repository AGENTS.md and WORK.md ledger, or when the repository already contains that ledger.
---

# Development workflow

Use for software work that must be resumable by a different agent without private chat history. This is a workflow protocol, not a dependency on a particular plugin or model.

## When to Use

- Start, continue, pause, or coordinate development work that must transfer across agents.
- Adopt a compact repository workflow when the user requests it.
- Do not replace a repository's existing process merely because a coding task was assigned.

## Procedure

1. Identify the intended repository without switching projects or modifying unrelated workspaces.
2. Read existing repository instructions and the current task ledger. Prefer the repository's adopted contract over generating a competing plan or tracker.
3. If the workflow has not been adopted and adoption is requested, merge [the operating-contract template](templates/AGENTS.md) into the existing `AGENTS.md` and create the task ledger as `WORK.md` from [the lite template](templates/WORK-lite.md) or [the full template](templates/WORK.md) per the tier rule in the contract, and copy [the check script](scripts/work-check.py) into the repository. Do not overwrite instructions or working state. Discover and exercise the actual command recipe; do not leave invented commands as defaults.
4. If only a task is requested, apply the relevant execution and verification discipline without silently installing a workflow or replacing repository conventions.

## Operate

- The operating contract defines the full loop and authority boundaries: orient, frame, choose a verifiable slice, build, independently verify, checkpoint, continue.
- Stable repository knowledge belongs in `AGENTS.md`; current task intent, plan, evidence, approvals, ownership, and the exact next action belong in `WORK.md` or an explicitly named task ledger.
- Run the contract's approval gate (G1-G6) and record it on the ledger's Gate line. No trigger: state the approach in one line and proceed. Any trigger: obtain approval first unless the owner already approved that specific approach, then continue within it. Routine corrections inside an approved task need no new gate. Investigate facts yourself. Re-ask only when a trigger newly fires, scope or risk changes materially, or an action exceeds authority.
- On pickup, reconcile actual files/revisions, stale evidence, ownership, and pending approvals before writing. Do not depend on agent memory or require the original chat.
- Default to one writer and an independent reviewer. Parallelize only across stable seams with exclusive ownership and an integration owner.
- Run `scripts/work-check.py lint` on pickup and before a handoff is called ready, and `lint --as-done` before recording `done`; use `snapshot` to record the evidence fingerprint. It checks consistency and rejects negated or hedged verdict wording, not that checks were really run; write plain verdicts such as `pass; exit 0` or `no blockers`.
- Missing checks or independent review are gaps, not success. Approval for local work is not approval to install, delete, publish, push, merge, deploy, access credentials, spend, or schedule persistent automation.

## Portability and improvement

This file can be explicitly attached/opened in any agent capable of reading Markdown. Automatic skill discovery is tool-specific and optional. Tool-specific startup files should point to the adopted repository contract rather than duplicate it.

Use the templates as the detailed reference when bootstrapping, or when the repository contract is missing a needed handoff/verification mechanism. The [source mapping](SOURCES.md) records upstream ideas and deliberate adaptations. Keep corrections in the canonical repository files. Promote repeated deterministic interventions to tested scripts, types, or checks before expanding prose.

## Pitfalls

- A historical passing check does not cover changed source or missing untracked inputs.
- A local checkpoint does not make files available on another machine. The default ledger is local and untracked; cross-machine handoff needs it committed on a task branch.
- A private todo list, transcript, or agent memory is not the canonical task state.
- Reverting your own approved diagnostic code edits is not permission to delete files/data or discard unrelated work.

## Verification

A successor must recover the goal, authority, ownership, actual snapshot, evidence gaps, and one executable next action from repository files alone. Check this with a cold-start rehearsal. A substantive deliverable still needs independent review of requirements, actual artifacts, and current-snapshot evidence; label unavailable checks or review explicitly instead of marking it done.
