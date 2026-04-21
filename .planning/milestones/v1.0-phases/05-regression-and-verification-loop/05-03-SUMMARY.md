---
phase: 05-regression-and-verification-loop
plan: 03
subsystem: validation-ladder-docs
tags: [docs, validation, ladder, saved-perception, workflow]
provides:
  - one explicit local validation ladder across fast, focused, and heavy checks
  - explicit guidance for when planner-only saved-perception replay is better than rerunning noisy perception stages
affects: [developer-workflow, docs, local-validation]
tech-stack:
  added: []
  patterns: [single-source validation workflow, low-noise planner-only regression guidance]
key-files:
  created: []
  modified:
    - tiptop/docs/development-build.md
    - tiptop/docs/command-reference.md
    - tiptop/docs/simulation.md
key-decisions:
  - "Keep one clear validation ladder instead of scattering equivalent commands across docs."
  - "Treat saved-perception planner-only replays as first-class low-noise regression tools."
duration: manual-session
completed: 2026-04-20
---

# Phase 5: Regression and Verification Loop Summary

**The local verification story is now written as one concrete ladder: fast checks, focused checks, and heavy integration checks, with saved-perception planner-only workflows called out explicitly.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added a recommended local validation ladder to the main development build notes.
- Linked websocket, H5, replay, and focused D435 preflight commands back to that ladder from the command reference and simulation docs.
- Documented when to prefer `replan_from_saved_perception.py` and other planner-only flows over rerunning noisy VLM/SAM perception.
- Aligned the docs around one practical validation sequence grounded in the current workspace assets and services.

## Task Commits
1. **Task 1: Write an explicit local validation ladder** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Explain when to prefer saved-perception replans over full reruns** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/docs/development-build.md` - recommended validation ladder and planner-only regression workflow
- `tiptop/docs/command-reference.md` - command-level placement within the ladder
- `tiptop/docs/simulation.md` - simulation-facing ladder and saved-observation layering guidance

## Verification
- `rg -n "fast checks|focused checks|heavy integration|validation ladder|test_planning_contracts|test_tiptop_h5|d435-fast-fs-m2t2-demo" tiptop/docs/development-build.md tiptop/docs/command-reference.md`
- `rg -n "saved perception|replan_from_saved_perception|full rerun|noise|planner-only" tiptop/docs/development-build.md tiptop/docs/simulation.md`

## Decisions & Deviations
- The ladder stays intentionally local and workstation-oriented; this phase does not invent CI or claim a broader automation story than the workspace currently supports.
- Because the workspace root is not a git repository, summary tracking remains doc- and verification-based.

## Next Phase Readiness
The docs now describe the same regression loop the tests implement, enabling final Phase 5 closeout without hidden oral history.
