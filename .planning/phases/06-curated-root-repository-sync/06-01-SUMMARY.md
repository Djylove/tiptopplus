---
phase: 06-curated-root-repository-sync
plan: 01
subsystem: curated-boundary-docs-and-bootstrap
tags: [docs, bootstrap, workspace-boundary, planning-alignment]
provides:
  - collaborator-facing curated workspace bootstrap contract
  - aligned root and planning-side wording for the git-tracked curated repo boundary
affects: [workspace-onboarding, root-docs, planning-docs]
tech-stack:
  added: []
  patterns: [root-level navigation doc, concise boundary contract, planning-doc alignment]
key-files:
  created:
    - WORKSPACE-BOOTSTRAP.md
  modified:
    - README.md
    - WORKSPACE-SERVICES.md
    - .planning/codebase/WORKSPACE.md
    - .planning/codebase/CONCERNS.md
    - .planning/ROADMAP.md
key-decisions:
  - "Keep one dedicated bootstrap doc at the workspace root instead of duplicating runtime manuals into multiple files."
  - "Describe the root repo as curated and git-tracked while keeping sibling repos explicitly outside the upload boundary."
duration: manual-session
completed: 2026-04-21
---

# Phase 6: Curated Root Repository Sync Summary

**The curated root repository now has one explicit bootstrap contract, and the root/planning docs all describe the same multi-repo boundary story.**

## Performance
- **Duration:** manual-session
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Added `WORKSPACE-BOOTSTRAP.md` as the collaborator-facing entrypoint for required sibling repos, expected layout, first verification pass, and curated-boundary exclusions.
- Linked the new bootstrap doc from `README.md` and `WORKSPACE-SERVICES.md` without duplicating the detailed TiPToP operator manuals.
- Updated planning-side boundary docs so they describe `/home/user/tiptop` as a curated root git repo while keeping sibling repos external.
- Kept roadmap routing aligned with execution by preserving the `$gsd-execute-phase 6` next step.

## Task Commits
1. **Task 1: Create `WORKSPACE-BOOTSTRAP.md` as the collaborator-facing curated-boundary contract** - `70ae377`
2. **Task 2: Link the new bootstrap contract from `README.md` and `WORKSPACE-SERVICES.md`** - `70ae377`
3. **Task 3: Align planning-side docs and roadmap routing with the git-tracked curated root repo** - `a66391c`

## Files Created/Modified
- `WORKSPACE-BOOTSTRAP.md` - root bootstrap contract for clone/layout and first verification pass
- `README.md` - root navigation updated to point at the bootstrap contract
- `WORKSPACE-SERVICES.md` - top-level clone/layout pointer added
- `.planning/codebase/WORKSPACE.md` - curated root git repo wording added
- `.planning/codebase/CONCERNS.md` - external sibling dependency wording strengthened
- `.planning/ROADMAP.md` - planned-plan list and execute-phase routing preserved

## Verification
- `bash -lc 'test -f WORKSPACE-BOOTSTRAP.md && rg -n "## What This Repo Contains|## Required Sibling Checkouts|## Expected Workspace Layout|## First Verification Pass|## What Is Intentionally Excluded|sam3/|Fast-FoundationStereo/|M2T2/|droid-sim-evals/|FoundationStereo/" WORKSPACE-BOOTSTRAP.md'`
- `bash -lc 'rg -n "WORKSPACE-BOOTSTRAP.md|Cloning this repo alone is therefore not enough|sibling repos" README.md WORKSPACE-SERVICES.md'`
- `bash -lc 'rg -n "curated root git repo|sibling repos remain external|curated subset|\$gsd-execute-phase 6" .planning/codebase/WORKSPACE.md .planning/codebase/CONCERNS.md .planning/ROADMAP.md'`

## Decisions & Deviations
- The bootstrap doc stays intentionally boundary-focused and links outward to `tiptop/docs/*` instead of copying runtime commands into yet another root document.
- `.planning/ROADMAP.md` already contained the correct `$gsd-execute-phase 6` next step from plan-phase work, so execution preserved that routing instead of rewriting it again.
- Task 1 and Task 2 landed in the same commit because the new bootstrap contract and the two root-doc links were introduced together as one tightly coupled documentation slice.

## Next Phase Readiness
The root repo now explains what cloning `tiptopplus` does and does not provide, which clears the way for a repeatable repo-boundary verification surface in `06-02`.
