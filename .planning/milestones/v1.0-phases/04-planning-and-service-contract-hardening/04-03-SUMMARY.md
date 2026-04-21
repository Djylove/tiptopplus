---
phase: 04-planning-and-service-contract-hardening
plan: 03
subsystem: planning-fallback-diagnostics
tags: [planning, fallback, troubleshooting, docs]
provides:
  - explicit troubleshooting signatures for missing provided grasps and fallback retry behavior
  - preserved combined failure reasons across provided-grasp and heuristic-only planning attempts
affects: [planning-debugging, troubleshooting, tests]
tech-stack:
  added: []
  patterns: [failure-signature capture, docs tied to focused branch tests]
key-files:
  created: []
  modified:
    - tiptop/tiptop/planning.py
    - tiptop/tests/test_planning_contracts.py
    - tiptop/docs/troubleshooting.md
key-decisions:
  - "Document the fallback semantics as baseline behavior instead of leaving them implicit in logs."
  - "Use the combined final failure reason as the canonical debugging surface when both planning attempts fail."
duration: manual-session
completed: 2026-04-20
---

# Phase 4: Planning and Service Contract Hardening Summary

**Planner fallback is now treated as an intentional, documented degradation path, with troubleshooting guidance that matches the actual log signatures and failure semantics in `planning.py`.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Preserved the missing-grasp and provided-grasp-failure fallback behaviors in the shared planner contract.
- Documented the most important planning-stage signatures: missing provided grasps, provided-grasp planning failure, heuristic fallback success, and total failure with combined reasons.
- Added troubleshooting guidance for `tiptop-h5` and `tiptop-server` failures that happen before planning completes, especially the common case where `M2T2` is not reachable.

## Task Commits
1. **Task 1: Protect fallback semantics for missing and unusable provided grasps** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Capture planning-stage fallback signatures in troubleshooting guidance** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tiptop/planning.py` - clarified fallback log messages and combined failure reporting
- `tiptop/tests/test_planning_contracts.py` - regression coverage for fallback branches
- `tiptop/docs/troubleshooting.md` - planning-stage fallback triage and H5/server failure guidance

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q`
- `rg -n "heuristic fallback|No valid M2T2 grasps|provided grasps|planning.failure_reason" tiptop/docs/troubleshooting.md tiptop/tiptop/planning.py`

## Decisions & Deviations
- Captured fallback semantics in operator-facing troubleshooting docs rather than trying to encode every failure signature as another synthetic test.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
The remaining closeout work is now mainly about websocket/runtime/docs alignment and updating planning state to reflect the hardened contract surfaces.
