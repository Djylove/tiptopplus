---
phase: 01-workspace-baseline
plan: 01
subsystem: workspace-planning-docs
tags: [workspace, docs, planning, architecture]
provides:
  - workspace-root boundary map for the active multi-repo system
  - aligned structure and architecture planning docs
affects: [workspace-baseline, onboarding, planning]
tech-stack:
  added: []
  patterns: [workspace boundary mapping, multi-repo documentation]
key-files:
  created:
    - .planning/codebase/WORKSPACE.md
  modified:
    - .planning/codebase/STRUCTURE.md
    - .planning/codebase/ARCHITECTURE.md
key-decisions:
  - "Treat /home/user/tiptop as the real planning boundary instead of tiptop/ alone."
  - "Keep FoundationStereo/ documented as reference-only while Fast-FoundationStereo/ stays in the active baseline."
duration: manual-session
completed: 2026-04-20
---

# Phase 1: Workspace Baseline Summary

**Planning-side workspace truth now starts from `/home/user/tiptop` and explicitly names the active baseline repos, reference repo, generated artifacts, and local archives.**

## Performance
- **Duration:** manual-session
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created `.planning/codebase/WORKSPACE.md` as the source of truth for the root workspace boundary.
- Updated `.planning/codebase/STRUCTURE.md` to use the same active/reference/generated/archive classification.
- Updated `.planning/codebase/ARCHITECTURE.md` so `tiptop-run`, `tiptop-h5`, and `tiptop-server` are described from the workspace-root boundary.

## Task Commits
1. **Task 1: Create workspace boundary map** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Align structure map** - `git unavailable (workspace is not a git repository)`
3. **Task 3: Align architecture map** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `.planning/codebase/WORKSPACE.md` - canonical workspace-layer and runtime-dependency reference for planning
- `.planning/codebase/STRUCTURE.md` - root directory map aligned to active repos, reference repo, generated artifacts, and local archives
- `.planning/codebase/ARCHITECTURE.md` - runtime architecture updated to describe the active workspace boundary and TiPToP entrypoints

## Decisions & Deviations
- Followed the plan intent without scope expansion into config hardening or command-manual work.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
The planning artifacts now encode the real workspace boundary, so the next plans can safely build the human-facing root entrypoints and service-role docs on top of a shared model.
