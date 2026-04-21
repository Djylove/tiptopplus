---
phase: 02-config-and-bring-up-hardening
plan: 02
subsystem: config-entrypoint-and-bring-up-docs
tags: [config, docs, workspace, bring-up]
provides:
  - tiptop-config prompt defaults aligned with centralized workspace resolution
  - one documented override/preference model across root and repo-level docs
affects: [config-hardening, onboarding, bring-up]
tech-stack:
  added: []
  patterns: [shared override model, validated-local-baseline plus supported overrides]
key-files:
  created: []
  modified:
    - tiptop/tiptop/scripts/tiptop_config.py
    - README.md
    - WORKSPACE-SERVICES.md
    - tiptop/docs/getting-started.md
    - tiptop/docs/development-build.md
key-decisions:
  - "Keep the validated /home/user/tiptop workstation as the documented baseline, but explain overrides explicitly instead of relying on source hunting."
  - "Treat workspace.root, profile overlays, env overrides, and explicit project_root fields as one coherent operator-facing model."
duration: manual-session
completed: 2026-04-20
---

# Phase 2: Config and Bring-Up Hardening Summary

**The human-facing config entrypoint and bring-up docs now tell the same workspace-override story as the runtime code.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Updated `tiptop-config` so the Fast-FoundationStereo project-root prompt now derives from the shared workspace resolver instead of a hard-coded fallback string.
- Added a short operator-visible summary of the active workspace root and override precedence inside `tiptop-config`.
- Clarified the root README, workspace service matrix, and TiPToP bring-up docs so contributors can discover `TIPTOP_WORKSPACE_ROOT`, `TIPTOP_CONFIG_PROFILE`, SAM3 overrides, and config-file `project_root` fields without source hunting.
- Kept command-level procedures in the existing TiPToP docs instead of duplicating the entire bring-up manual at the workspace root.

## Task Commits
1. **Task 1: Align `tiptop-config` prompts with the shared resolution model** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Document where to inspect and override workspace/service roots** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tiptop/scripts/tiptop_config.py` - shared workspace-root model surfaced in the interactive config entrypoint
- `README.md` - workspace-level override entry surface documented
- `WORKSPACE-SERVICES.md` - repo/service inspection and override surfaces documented
- `tiptop/docs/getting-started.md` - bring-up guide now explains override precedence and SAM3 checkpoint derivation
- `tiptop/docs/development-build.md` - validated local build notes aligned with workspace-root and profile override model

## Decisions & Deviations
- Preserved `/home/user/tiptop` as the validated local baseline instead of pretending the workspace is fully generic.
- Documented SAM3 checkpoint derivation from `project_root` as the preferred default rather than reintroducing a fixed absolute checkpoint path.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
The remaining visible fragility is the noisy no-git metadata path in run recording. With the docs and config entrypoint aligned, the next step can focus on graceful runtime degradation and clean Phase 2 close-out.
