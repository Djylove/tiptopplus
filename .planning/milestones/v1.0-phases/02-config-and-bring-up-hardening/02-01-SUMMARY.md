---
phase: 02-config-and-bring-up-hardening
plan: 01
subsystem: runtime-config-resolution
tags: [config, workspace, sam3, tests]
provides:
  - centralized workspace-root and sibling-repo path resolution
  - SAM3 local path and checkpoint fallback aligned with workspace-derived defaults
affects: [config-hardening, bring-up, portability]
tech-stack:
  added: []
  patterns: [centralized resolution helper, layered override precedence]
key-files:
  created:
    - tiptop/tests/test_workspace_config.py
  modified:
    - tiptop/tiptop/config/__init__.py
    - tiptop/tiptop/perception/sam3.py
    - tiptop/tiptop/config/tiptop.yml
    - tiptop/tests/conftest.py
key-decisions:
  - "Centralize workspace-root resolution in tiptop.config and let runtime modules consume it."
  - "SAM3 checkpoint defaults should derive from project_root unless an explicit env override is provided."
duration: manual-session
completed: 2026-04-20
---

# Phase 2: Config and Bring-Up Hardening Summary

**Runtime path resolution now has a shared workspace-root model, and the active SAM3 path no longer depends on one irreducible workstation fallback.**

## Performance
- **Duration:** manual-session
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Added shared helpers in `tiptop.config` for resolving the workspace root, workspace-relative paths, and sibling repo roots.
- Routed `tiptop.perception.sam3` through the shared resolver and changed SAM3 checkpoint defaults to derive from `project_root`.
- Added focused unit coverage for workspace-root, sibling-repo, and SAM3 resolution behavior.
- Reduced unrelated test coupling by moving `gdown` import in `tests/conftest.py` to runtime use instead of top-level import.

## Task Commits
1. **Task 1: Add central workspace-root helpers** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Route SAM3 path logic through the shared resolver** - `git unavailable (workspace is not a git repository)`
3. **Task 3: Add focused resolution tests** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tiptop/config/__init__.py` - shared workspace-root and sibling-path resolution helpers
- `tiptop/tiptop/perception/sam3.py` - SAM3 root/checkpoint resolution now aligned with centralized config logic
- `tiptop/tiptop/config/tiptop.yml` - workspace root documented; SAM3 checkpoint now derives from project root by default
- `tiptop/tests/test_workspace_config.py` - focused unit coverage for override precedence and derived fallback behavior
- `tiptop/tests/conftest.py` - test fixture import path no longer blocks non-integration test collection

## Decisions & Deviations
- Used `TIPTOP_WORKSPACE_ROOT` plus config-based `workspace.root` as the new root-resolution surface.
- Kept the current workstation baseline intact by preserving `/home/user/tiptop` as the validated default in config.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
The runtime layer now has one central path model, so the next plan can safely align `tiptop-config` and the human-facing bring-up docs around the same override story.
