---
phase: 01-workspace-baseline
plan: 03
subsystem: workspace-services
tags: [workspace, docs, services, onboarding]
provides:
  - repo and service responsibility matrix for the active baseline
  - high-level bring-up order from the workspace root
affects: [workspace-baseline, onboarding, runtime-visibility]
tech-stack:
  added: []
  patterns: [role matrix, high-level bring-up sequencing]
key-files:
  created:
    - WORKSPACE-SERVICES.md
  modified:
    - README.md
    - tiptop/docs/getting-started.md
key-decisions:
  - "Keep WORKSPACE-SERVICES.md high-level and route exact commands to existing TiPToP manuals."
  - "Represent responsibilities as a role matrix so active baseline coverage is easy to scan and verify."
duration: manual-session
completed: 2026-04-20
---

# Phase 1: Workspace Baseline Summary

**A new workspace service reference now explains what each active repo provides, which runtime surfaces must exist, and the high-level bring-up order before launching TiPToP entrypoints.**

## Performance
- **Duration:** manual-session
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created `WORKSPACE-SERVICES.md` with an active repo/service matrix covering `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`.
- Added a high-level bring-up order that separates required services from detailed command manuals.
- Cross-linked the new service reference from both the root `README.md` and `tiptop/docs/getting-started.md`.

## Task Commits
1. **Task 1: Create workspace service matrix** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Add high-level bring-up order** - `git unavailable (workspace is not a git repository)`
3. **Task 3: Cross-link service reference** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `WORKSPACE-SERVICES.md` - dedicated workspace repo/service and bring-up-order reference
- `README.md` - now links directly to the service matrix from the main navigation path
- `tiptop/docs/getting-started.md` - now points readers back to the workspace-level service context before detailed steps

## Decisions & Deviations
- Followed the plan and kept this document at the role/ordering layer rather than turning it into a second command manual.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
Phase 1 now satisfies the workspace-boundary, onboarding, and service-visibility prerequisites needed before Phase 2 starts on config and bring-up hardening.
