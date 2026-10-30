<!-- tier: lite -->
# Work (lite): <short outcome>

For single-writer, single-seam tasks (tier rule in AGENTS.md, "Ledger tiers and storage"). One line per field. Replace placeholders with inspected facts; use `none`, `unknown`, or `not run` explicitly. If a full-ledger trigger fires, copy this content into `templates/WORK.md` and continue there.

- Status: <framing | ready | building | verifying | review | blocked | paused | done>
- Owner: <agent or human; active or released>
- Base HEAD: <revision the work started from; the G3 size check counts changes since it>
- Snapshot: <output of `work-check.py snapshot`, or none yet>
- Goal: <observable outcome>
- Non-goals: <exclusions, or none>
- Gate: <none triggered (checked G1-G6) | triggered: G# reason, approval required>
- Approval: <self-approved small task | approved by whom, reference/date | not yet approved>
- Preserve: <unrelated dirty files or edits that are not yours, or none>
- Plan: <one line: inspect -> red -> fix -> verify -> review>

## Acceptance

- A1: <observable check> => <not run | fail | pass; evidence>

## State

- Evidence: <exact command, working directory, snapshot, exit code or observation; or not run>
- Review: <reviewer or context, fp:<hex> of the reviewed snapshot, verdict; or not independently reviewed>
- Open findings: <blocking first, or none>
- Next action: <one exact command or edit, working directory, expected observation>
- Stop: <blocker or authority change that should halt work>
- Resources: <live processes, ports, files to preserve, or none>
