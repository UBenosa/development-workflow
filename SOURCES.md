# Sources and design decisions

This kit is an original synthesis, not an official combined Matt Pocock/pstack workflow and not a claim that either author endorses it. The source repositories were inspected at fixed revisions, not inferred from the attached repository statistics.

## Primary interview

[Matt Pocock and Lauren Tan (Poteto), LIVE: Poteto (creator of pstack) on shipping 1,000's of PR's a month at SpaceX](https://www.youtube.com/watch?v=MN9dGgmLyso).

The full automatic-caption transcript was fetched with an existing local helper: 1,707 segments; reported duration 1:05:37. Automatic captions are imperfect. The workflow uses paraphrases, not purported exact quotations.

| Segment | Supported idea | Adaptation in this kit |
| --- | --- | --- |
| [06:22-09:41](https://www.youtube.com/watch?v=MN9dGgmLyso&t=382s) | Precise intent, shared vocabulary, and meaningful rather than tautological tests | Frame outcomes and seams before implementation |
| [16:14-18:43](https://www.youtube.com/watch?v=MN9dGgmLyso&t=974s) | Agents need to run and observe the result to close the feedback loop | A proven runbook and real acceptance scenarios |
| [19:32-24:52](https://www.youtube.com/watch?v=MN9dGgmLyso&t=1172s) | Extract repeated deterministic operations into commands/scripts | Improve tested commands rather than regenerating glue each task |
| [25:36-32:18](https://www.youtube.com/watch?v=MN9dGgmLyso&t=1536s) | Types, lint rules, and code structure constrain recurring failures | Encode lessons in the environment first |
| [34:14-39:51](https://www.youtube.com/watch?v=MN9dGgmLyso&t=2054s) | Outside context can make the current intent snapshot stale | Reconcile new evidence and revise the living task ledger |
| [44:29-49:04](https://www.youtube.com/watch?v=MN9dGgmLyso&t=2669s) | Aggregate related reports and buffer findings before fixing every symptom | Optional unapproved backlog; group causes before scheduling |
| [49:34-54:42](https://www.youtube.com/watch?v=MN9dGgmLyso&t=2974s) | Intensive verification and environment work underpin Poteto's reported autonomy; scaling costs tokens and effort | Start small, add risk-scaled review; no promised productivity gain |
| [55:44-59:24](https://www.youtube.com/watch?v=MN9dGgmLyso&t=3344s) | Irreversible changes and difficult-to-verify domains remain hard | Separate authority and recoverability from test confidence |
| [1:00:35-1:04:42](https://www.youtube.com/watch?v=MN9dGgmLyso&t=3635s) | Combine the libraries deliberately and extract process from repeated interventions | This small custom workflow rather than installing two competing orchestrators |

The reported PR volume is the guest's account, not an audited outcome, quality metric, or target for this workflow. This kit does not reproduce the interview's internal tools or production environment.

## Matt Pocock skills

Pinned repository revision: `5beb35b040e3de97e54fa9e386d7e42d15c295c2`.

- [grill-with-docs](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/grill-with-docs/SKILL.md) composes interviewing with domain modeling. [domain-modeling](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/domain-modeling/SKILL.md) supports shared terminology and selective durable decisions. This kit uses targeted clarification and creates extra documentation only when useful.
- [to-tickets](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/to-tickets/SKILL.md) defines independently verifiable vertical slices, blockers, context-sized tickets, and an expand-migrate-contract exception for wide refactors. This kit keeps small tasks in one ledger and grows to linked task files only when needed.
- [tdd](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/tdd/SKILL.md) requires public, pre-agreed test seams, an independent expected result, and one red-to-green slice at a time. **At this pinned revision, it places refactoring in review rather than the implementation loop.** This kit deliberately allows small green refactoring and risk-based manual scenarios where a cheap automated seam is unavailable. That is an adaptation, not a quotation of Matt's rule.
- [code-review](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/code-review/SKILL.md) separates specification compliance and standards review. This kit preserves both lenses, using one independent reviewer by default and more for higher-risk work.
- [handoff](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/handoff/SKILL.md) references existing artifacts instead of duplicating them and saves its summary outside the workspace in temporary storage. This kit deliberately stores resumable task state in the repository instead.
- [writing-for-agents](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/writing-for-agents/SKILL.md) emphasizes one authoritative meaning, explicit pointers, progressive disclosure, and checkable completion. These inform the two-file default.

## Poteto's pstack

Pinned `cursor/plugins` repository revision: `9580c23696ac8d7abed0c166f2f9918800afb819`.

- [bug-fix](https://github.com/cursor/plugins/blob/9580c23696ac8d7abed0c166f2f9918800afb819/pstack/skills/poteto-mode/playbooks/bug-fix.md) requires actual-surface reproduction, runtime evidence, supported hypotheses, and verification of the original symptom. This kit keeps those gates rather than treating a patch as a fix.
- [create-verification-skill](https://github.com/cursor/plugins/blob/9580c23696ac8d7abed0c166f2f9918800afb819/pstack/skills/create-verification-skill/SKILL.md) discovers project-native launch, interaction, isolation, and evidence methods and exercises the generated recipe. This kit stores a compact runbook in `AGENTS.md`; a larger separate verification recipe is optional.
- [prove-it-works](https://github.com/cursor/plugins/blob/9580c23696ac8d7abed0c166f2f9918800afb819/pstack/skills/principle-prove-it-works/SKILL.md) demands proof on the actual artifact rather than derived state or self-report. This kit ties acceptance to the tested snapshot, including dirty and untracked work.
- [orchestrate](https://github.com/cursor/plugins/blob/9580c23696ac8d7abed0c166f2f9918800afb819/pstack/skills/poteto-mode/playbooks/orchestrate.md) supplies scoped briefs, single-writer ownership, dependency context relay, pilot-before-fan-out, bounded retries, and revision-bound verification. This kit keeps the protocol without its specific agent types, models, dashboards, or storage system.
- [session-pickup](https://github.com/cursor/plugins/blob/9580c23696ac8d7abed0c166f2f9918800afb819/pstack/skills/poteto-mode/playbooks/session-pickup.md) reconstructs current state without repeating completed investigation, yet checks inherited claims against the artifact. This kit resolves that tension by rechecking relevant acceptance evidence without redoing historical discovery.
- [pause-safely](https://github.com/cursor/plugins/blob/9580c23696ac8d7abed0c166f2f9918800afb819/pstack/skills/poteto-mode/playbooks/pause-safely.md) checkpoints intent, progress, verification, and next steps, using a WIP commit and off-context note. This kit does not automatically commit, cancel all workers, or depend on temporary files; it records actual ownership and worker lifecycle instead.
- [encode-lessons-in-structure](https://github.com/cursor/plugins/blob/9580c23696ac8d7abed0c166f2f9918800afb819/pstack/skills/principle-encode-lessons-in-structure/SKILL.md) favors executable constraints over more instructions. This informs the improvement loop.

## Deliberate policy choices

The two-file default, approach approval (gated by triggers G1-G6, below), per-action external authority, independent review before calling substantive work done, cold-start state reconciliation, and local-state-first portability are design choices for this user. They are not presented as universal prescriptions from the authors. The approval-gate triggers and thresholds (G1-G6), the lite and full ledger tiers, the local-untracked ledger default, and `scripts/work-check.py` were added after the source review and are this kit's own design, not taken from the sources.

We do not import default automatic PR creation/merge, hard-coded model choices, ten verification lanes for every task, mandatory implementation delegation, a strict ban on useful comments, or Cursor-specific automation. External integrations and persistent triggers require a separate approved plan.

The research checks documented prescriptions, not effectiveness. Real-world reliability and cross-agent compatibility must be evaluated in the target repositories. See `VALIDATION.md` for what was actually checked here.
