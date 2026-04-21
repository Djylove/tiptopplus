---
phase: 04-planning-and-service-contract-hardening
plan: 01
subsystem: planning-contract-and-m2t2-handoff
tags: [planning, m2t2, fallback, tests]
provides:
  - explicit movable-only provided-grasp filtering at the shared planning boundary
  - focused coverage for heuristic fallback and combined failure reasons
affects: [planning-contract, m2t2-handoff, tests]
tech-stack:
  added: []
  patterns: [shared contract surface, focused branch-contract tests]
key-files:
  created:
    - tiptop/tests/test_planning_contracts.py
  modified:
    - tiptop/tiptop/planning.py
    - tiptop/tiptop/tiptop_websocket_server.py
    - tiptop/tiptop/websocket_server.py
    - droid-sim-evals/tiptop_eval.py
    - droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py
key-decisions:
  - "Keep `run_planning()` as the one shared contract for live, H5, and websocket planning."
  - "Treat missing or unusable provided grasps as an intentional degradation path, not as an implicit side effect."
duration: manual-session
completed: 2026-04-20
---

# Phase 4: Planning and Service Contract Hardening Summary

**The shared planning boundary now makes the M2T2 handoff explicit, filters provided grasps down to movable objects with usable payloads, and regression-protects the fallback path when those grasps are missing or later fail in planning.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Tightened `planning.py` so only movable objects with non-empty `grasps_obj` reach cuTAMP as provided grasps.
- Preserved and clarified the baseline fallback behavior: no usable grasps falls back directly to heuristics, while provided-grasp planning failure retries once with heuristic-only grasps.
- Added focused tests for missing-grasp fallback, provided-grasp retry, combined failure reasons, serialized plan round-trip, and websocket module alias compatibility.
- Aligned websocket startup/help text across TiPToP and `droid-sim-evals` so the canonical command and compatibility alias tell the same story.

## Task Commits
1. **Task 1: Tighten provided-grasp filtering and planning-boundary clarity** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Add focused contract tests for M2T2 grasp handoff** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tiptop/planning.py` - explicit movable-grasp filtering, fallback retry behavior, and combined failure reporting
- `tiptop/tests/test_planning_contracts.py` - focused planning contract coverage
- `tiptop/tiptop/websocket_server.py` - compatibility alias for historical websocket module imports
- `tiptop/tiptop/tiptop_websocket_server.py` - canonical startup/help guidance
- `droid-sim-evals/tiptop_eval.py` - simulator-side startup guidance aligned with the canonical websocket command
- `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` - client-side startup hint aligned with the canonical websocket command

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q`
- `rg -n "No valid M2T2 grasps|provided grasps|heuristic fallback" tiptop/tiptop/planning.py`

## Decisions & Deviations
- Chose to protect the planner contract through focused unit tests rather than widening scope into a full simulator test harness in this plan.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
The planning boundary is now explicit enough to extend into offline H5 artifact expectations and serialized-plan compatibility without changing the supported execution modes.
