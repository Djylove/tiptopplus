---
phase: 05-regression-and-verification-loop
plan: 02
subsystem: cross-service-smoke-and-contracts
tags: [contracts, smoke, m2t2, websocket, docs]
provides:
  - focused smoke coverage for service-health and downstream consumer contract assumptions
  - clearer operator guidance for distinguishing environment failures from real TiPToP regressions
affects: [cross-service-contracts, smoke-tests, troubleshooting]
tech-stack:
  added: []
  patterns: [focused contract checks, service-prerequisite docs]
key-files:
  created: []
  modified:
    - tiptop/tests/test_perception_baseline.py
    - tiptop/tests/test_planning_contracts.py
    - tiptop/docs/simulation.md
    - tiptop/docs/troubleshooting.md
key-decisions:
  - "Catch missing-service and websocket/serialized-plan drift with focused tests instead of waiting for full simulator bring-up."
  - "Document service prerequisites where operators will debug first."
duration: manual-session
completed: 2026-04-20
---

# Phase 5: Regression and Verification Loop Summary

**Cross-service failure modes now fail earlier and more clearly, with focused tests and docs aligned to the real TiPToP consumers.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added focused smoke coverage for the `check_server_health()` boundary so obvious `M2T2` failures surface before deeper debugging begins.
- Added websocket response-shape protection for the simulator-facing `success / plan / error / server_timing` contract.
- Captured service-prerequisite guidance for H5, websocket, and replay flows in simulation and troubleshooting docs.
- Made it easier to distinguish environment or downstream-consumer issues from true planner regressions.

## Task Commits
1. **Task 1: Strengthen lightweight cross-service smoke coverage** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Capture service prerequisites and consumer contract expectations in the docs** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tests/test_perception_baseline.py` - health-check and SAM3 fallback regression coverage
- `tiptop/tests/test_planning_contracts.py` - websocket response contract coverage
- `tiptop/docs/simulation.md` - service prerequisite and validation ladder guidance
- `tiptop/docs/troubleshooting.md` - downstream/environment boundary triage guidance

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py tests/test_planning_contracts.py -q`
- `rg -n "M2T2|FoundationStereo|health|server_timing|replay_json_traj|tiptop-server" tiptop/docs/simulation.md tiptop/docs/troubleshooting.md droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py droid-sim-evals/replay_json_traj.py`

## Decisions & Deviations
- The new SAM3 regression fix for `scene4` also belongs to this plan’s risk surface because it changes how a cross-service VLM + SAM3 failure degrades: warn and fall back to VLM boxes instead of aborting the whole run.
- `/home/user/tiptop` is not a git repository, so closeout records validation results but not commit hashes.

## Next Phase Readiness
The project now has explicit smoke checks and service-boundary guidance, which makes the validation ladder documentation coherent instead of aspirational.
